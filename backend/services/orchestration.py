from collections.abc import Iterable
from typing import Any

from backend.models.entities import Bid, ProcessingStatus
from backend.schemas.orchestration import BidAnalysisResult, PipelineSourceMetadata
from backend.schemas.requirements import RFPTextSegment, RequirementExtractionResult
from backend.services.requirement_extraction import AIExtractionError, AIRequirementExtractor, RequirementExtractor, ai_requirement_extraction_service, requirement_extraction_service
from backend.services.rocketride_service import PipelineService, RocketRideServiceError, rocketride_service
from backend.schemas.compliance import ComplianceResult
from backend.schemas.response_generation import ProposedBidResponse, RequirementResponse
from backend.services.compliance_analysis import ComplianceAnalysisService, EvidenceRetriever
from backend.services.knowledge_base import knowledge_base_service
from backend.services.response_generation import ResponseGenerationService, response_generation_service
from backend.services.repository import repository
from backend.services.review import ReviewService


class PipelineOutputError(RuntimeError):
    """Raised when the pipeline response cannot be converted to extracted text."""


class BidAnalysisOrchestrator:
    def __init__(
        self,
        pipeline: PipelineService,
        extractor: RequirementExtractor = requirement_extraction_service,
        ai_extractor: AIRequirementExtractor | None = ai_requirement_extraction_service,
        compliance: ComplianceAnalysisService | None = None,
        response_generation: ResponseGenerationService | None = None,
        review: ReviewService | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._extractor = extractor
        self._ai_extractor = ai_extractor
        self._compliance = compliance or ComplianceAnalysisService(knowledge_base_service)
        self._response_generation = response_generation or response_generation_service
        self._review = review or ReviewService(repository)

    async def analyze(self, bid: Bid, document: bytes) -> BidAnalysisResult:
        bid.processing_status = ProcessingStatus.processing
        try:
            pipeline_response = await self._pipeline.analyze(bid, document)
            segments = self._normalise_pipeline_output(pipeline_response)
            extraction, extraction_mode = self._extract_requirements(pipeline_response, segments)
            compliance_results: list[ComplianceResult] = []
            proposed_responses: list[RequirementResponse] = []
            review_ids: list[str] = []
            if self._compliance is not None and extraction.requirements:
                compliance_results = self._compliance.analyze(extraction.requirements).results
                proposed = self._response_generation.generate(extraction.requirements, compliance_results)
                proposed_responses = proposed.responses
                if self._review is not None:
                    review_ids = []
                    for response in proposed_responses:
                        # Find matching compliance result to pull conflict_analysis securely
                        matching_cr = next((cr for cr in compliance_results if cr.requirement.requirement_id == response.requirement_id), None)
                        conflict = None
                        if matching_cr and hasattr(matching_cr, 'conflict_analysis') and matching_cr.conflict_analysis:
                            conflict = matching_cr.conflict_analysis.model_dump()
                        
                        review_ids.append(str(self._review.create_pending(
                            bid_id=bid.bid_id,
                            requirement_id=response.requirement_id,
                            proposed_response=response.proposed_response,
                            compliance_status=response.compliance_status,
                            confidence=response.confidence,
                            supporting_evidence=response.supporting_evidence,
                            conflict_analysis=conflict
                        ).review_id))
            bid.processing_status = ProcessingStatus.completed
            return BidAnalysisResult(
                bid_id=bid.bid_id,
                processing_status=bid.processing_status.value,
                requirements=extraction.requirements,
                compliance_results=compliance_results,
                proposed_responses=proposed_responses,
                review_ids=review_ids,
                source_metadata=segments,
                extraction_mode=extraction_mode,
            )
        except RocketRideServiceError as exc:
            return self._failed(bid, exc.public_message or "RocketRide pipeline execution failed.")
        except (PipelineOutputError, ValueError, TypeError) as exc:
            return self._failed(bid, str(exc))
        except Exception:
            return self._failed(bid, "Bid analysis failed.")

    @staticmethod
    def _failed(bid: Bid, error: str) -> BidAnalysisResult:
        bid.processing_status = ProcessingStatus.failed
        return BidAnalysisResult(
            bid_id=bid.bid_id,
            processing_status=bid.processing_status.value,
            errors=[error],
        )

    def _extract_requirements(
        self,
        pipeline_response: dict[str, Any],
        segments: list[PipelineSourceMetadata],
    ) -> tuple[RequirementExtractionResult, str]:
        if self._ai_extractor is not None:
            try:
                return self._ai_extractor.extract_ai(pipeline_response), "rocketride_ai"
            except AIExtractionError:
                if self._has_structured_ai_output(pipeline_response):
                    raise
        extraction = self._extractor.extract([
            RFPTextSegment(text=segment.source_text, source_section=segment.source_section, source_page=segment.source_page)
            for segment in segments
        ])
        return extraction, "deterministic_fallback"

    @staticmethod
    def _has_structured_ai_output(response: dict[str, Any]) -> bool:
        payload = response.get("data", response)
        if isinstance(payload, dict) and "requirements" in payload:
            return True
        if isinstance(payload, dict):
            return any(key in payload for key in ("ai_requirements", "structured_requirements"))
        return False

    @classmethod
    def _normalise_pipeline_output(cls, response: dict[str, Any]) -> list[PipelineSourceMetadata]:
        if not isinstance(response, dict):
            raise PipelineOutputError("RocketRide returned a malformed pipeline response.")
        payload = response.get("data", response)
        if not isinstance(payload, dict):
            raise PipelineOutputError("RocketRide pipeline output did not contain a data object.")
        segments: list[PipelineSourceMetadata] = []
        for lane_name in ("text", "table"):
            if lane_name in payload:
                segments.extend(cls._extract_lane(payload[lane_name], lane_name))
        if not segments:
            if any(key in payload for key in ("requirements", "ai_requirements", "structured_requirements")):
                return []
            result_types = payload.get("result_types")
            if isinstance(result_types, dict) and any(lane == "answers" for lane in result_types.values()):
                return []
            raise PipelineOutputError("RocketRide pipeline output contained no text or table data.")
        return segments

    @classmethod
    def _extract_lane(cls, value: Any, lane_name: str) -> list[PipelineSourceMetadata]:
        if isinstance(value, str):
            if not value.strip():
                return []
            return [PipelineSourceMetadata(source_text=value, metadata={"lane": lane_name})]
        if isinstance(value, dict):
            text = cls._text_from_record(value)
            if text:
                return [cls._metadata_from_record(value, text, lane_name)]
            records = value.get("items") or value.get("rows") or value.get("data")
            if records is not None:
                return cls._extract_lane(records, lane_name)
            raise PipelineOutputError(f"RocketRide {lane_name} output did not contain text.")
        if isinstance(value, list):
            segments: list[PipelineSourceMetadata] = []
            for record in value:
                segments.extend(cls._extract_lane(record, lane_name))
            return segments
        raise PipelineOutputError(f"RocketRide {lane_name} output has an unsupported format.")

    @staticmethod
    def _text_from_record(record: dict[str, Any]) -> str | None:
        for key in ("text", "source_text", "content", "value"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    @staticmethod
    def _metadata_from_record(record: dict[str, Any], text: str, lane_name: str) -> PipelineSourceMetadata:
        page = record.get("page")
        if page is None:
            page = record.get("page_number")
        if page is not None and not isinstance(page, int):
            page = None
        section = record.get("section")
        if section is None:
            section = record.get("source_section")
        if section is not None and not isinstance(section, str):
            section = None
        metadata = dict(record.get("metadata", {})) if isinstance(record.get("metadata", {}), dict) else {}
        metadata["lane"] = lane_name
        return PipelineSourceMetadata(source_text=text, source_page=page, source_section=section, metadata=metadata)


bid_analysis_orchestrator = BidAnalysisOrchestrator(rocketride_service)