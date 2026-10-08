from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api import routes
from backend.main import app
from backend.models.entities import Bid, RFP
from backend.schemas.orchestration import BidAnalysisResult
from backend.schemas.requirements import ExtractedRequirement, RequirementExtractionResult
from backend.schemas.compliance import ComplianceResult, ComplianceStatus
from backend.schemas.rag import RetrievalResult
from backend.schemas.response_generation import ProposedBidResponse, RequirementResponse
from backend.schemas.review import ReviewItem, ReviewStatus
from backend.services.compliance_analysis import ComplianceAnalysisService
from backend.services.requirement_extraction import AIExtractionError, StructuredAIRequirementExtractor
from backend.services.response_generation import ResponseGenerationService
from backend.services.review import ReviewService
from backend.services.orchestration import BidAnalysisOrchestrator


def make_bid() -> Bid:
    bid_id = uuid4()
    return Bid(
        id=bid_id,
        bid_id=bid_id,
        rfp=RFP(filename="rfp.pdf", title="RFP", file_type="pdf", file_size=10),
    )


class FakePipeline:
    def __init__(self, response: dict, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.received: bytes | None = None

    async def analyze(self, bid: Bid, document: bytes) -> dict:
        self.received = document
        if self.error:
            raise self.error
        return self.response

    async def generate(self, bid: Bid, document: bytes) -> dict:
        raise AssertionError("generation must not be called")


class RecordingExtractor:
    def __init__(self) -> None:
        self.received = []

    def extract(self, text):
        self.received = list(text)
        return RequirementExtractionResult(requirements=[], message="recorded")


def test_pipeline_output_is_converted_and_sent_to_extractor() -> None:
    import asyncio

    pipeline = FakePipeline({"status": "completed", "data": {"text": [{"text": "The supplier must provide support.", "page": 3, "section": "Support"}]}})
    extractor = RecordingExtractor()
    bid = make_bid()

    result = asyncio.run(BidAnalysisOrchestrator(pipeline, extractor).analyze(bid, b"rfp-bytes"))

    assert result.processing_status == "completed"
    assert result.source_metadata[0].source_page == 3
    assert result.source_metadata[0].source_section == "Support"
    assert extractor.received[0].text == "The supplier must provide support."
    assert pipeline.received == b"rfp-bytes"


def test_table_and_text_lanes_are_supported() -> None:
    import asyncio
    pipeline = FakePipeline({"data": {"text": "The supplier shall encrypt data.", "table": [{"content": "The supplier must provide 24/7 support."}]}})
    result = asyncio.run(BidAnalysisOrchestrator(pipeline, RecordingExtractor()).analyze(make_bid(), b"document"))

    assert result.processing_status == "completed"
    assert len(result.source_metadata) == 2


def test_malformed_pipeline_output_is_reported_without_leaking_details() -> None:
    import asyncio

    result = asyncio.run(BidAnalysisOrchestrator(FakePipeline({"data": {"unknown": []}}), RecordingExtractor()).analyze(make_bid(), b"document"))

    assert result.processing_status == "failed"
    assert result.requirements == []
    assert result.errors == ["RocketRide pipeline output contained no text or table data."]


def test_connection_failure_is_sanitized() -> None:
    import asyncio

    result = asyncio.run(BidAnalysisOrchestrator(FakePipeline({}, ConnectionError("secret-api-key")), RecordingExtractor()).analyze(make_bid(), b"document"))

    assert result.processing_status == "failed"
    assert result.errors == ["Bid analysis failed."]
    assert "secret-api-key" not in str(result)


def test_pipeline_execution_failure_is_sanitized() -> None:
    import asyncio
    from backend.services.rocketride_service import RocketRideServiceError

    result = asyncio.run(BidAnalysisOrchestrator(FakePipeline({}, RocketRideServiceError("credential-value")), RecordingExtractor()).analyze(make_bid(), b"document"))

    assert result.processing_status == "failed"
    assert result.errors == ["RocketRide pipeline execution failed."]
    assert "credential-value" not in str(result)


def test_analysis_endpoint_uses_orchestrator_result() -> None:
    class FakeOrchestrator:
        async def analyze(self, bid: Bid, document: bytes) -> BidAnalysisResult:
            return BidAnalysisResult(
                bid_id=bid.bid_id,
                processing_status="completed",
                requirements=[ExtractedRequirement(requirement_text="The supplier must provide support.")],
            )

    original = routes.bid_analysis_orchestrator
    routes.bid_analysis_orchestrator = FakeOrchestrator()
    try:
        client = TestClient(app)
        upload = client.post("/api/bids/upload", files={"file": ("rfp.pdf", b"%PDF-1.7 test", "application/pdf")})
        assert upload.status_code == 201, upload.text
        response = client.post(f"/api/bids/{upload.json()['bid_id']}/analyze")
        assert response.status_code == 200, response.text
        assert response.json()["processing_status"] == "completed"
        assert response.json()["requirements"][0]["requirement_text"].startswith("The supplier")
    finally:
        routes.bid_analysis_orchestrator = original


def test_ai_output_is_validated_against_requirement_schema() -> None:
    result = StructuredAIRequirementExtractor().extract_ai({
        "data": {
            "requirements": [{
                "requirement_id": str(uuid4()),
                "requirement_text": "The supplier must provide support.",
                "category": None,
                "priority": None,
                "deadline": None,
                "compliance_type": None,
                "source_section": "Support",
                "source_page": 2,
            }]
        }
    })

    assert len(result.requirements) == 1
    assert result.requirements[0].source_page == 2


def test_malformed_ai_output_fails_without_fabrication() -> None:
    with pytest.raises(AIExtractionError):
        StructuredAIRequirementExtractor().extract_ai({"data": {"requirements": [{"text": "unsupported shape"}]}})


def test_llm_error_answer_is_not_treated_as_requirement_data() -> None:
    with pytest.raises(AIExtractionError, match="LLM returned an error"):
        StructuredAIRequirementExtractor().extract_ai({"requirements": ["**LLM error** - Rate limit exceeded"]})


def test_ai_extraction_instruction_is_explicit_and_safe() -> None:
    instruction = StructuredAIRequirementExtractor.EXTRACTION_INSTRUCTION

    assert "only explicit requirements" in instruction
    assert "atomic requirements" in instruction
    assert "Never invent" in instruction
    assert "null" in instruction


def test_structured_ai_pipeline_output_is_used_by_orchestrator() -> None:
    import asyncio

    class StructuredPipeline:
        async def analyze(self, bid: Bid, document: bytes) -> dict:
            return {"data": {"requirements": [{
                "requirement_id": str(uuid4()),
                "requirement_text": "The supplier must provide support.",
                "category": "support",
                "priority": None,
                "deadline": None,
                "compliance_type": None,
                "source_section": "Support",
                "source_page": 2,
            }]}}

        async def generate(self, bid: Bid, document: bytes) -> dict:
            raise AssertionError("generate was not expected")

    result = asyncio.run(BidAnalysisOrchestrator(
        StructuredPipeline(),
        ai_extractor=StructuredAIRequirementExtractor(),
        compliance=type("NoopCompliance", (), {"analyze": lambda self, requirements: type("Output", (), {"results": []})()})(),
    ).analyze(make_bid(), b"document"))

    assert result.extraction_mode == "rocketride_ai"
    assert result.requirements[0].source_page == 2


def test_answer_lane_json_is_validated_as_requirements() -> None:
    requirement_id = str(uuid4())
    answer = '[{"requirement_id": "' + requirement_id + '", "requirement_text": "The supplier must provide support.", "category": null, "priority": null, "deadline": null, "compliance_type": null, "source_section": "Support", "source_page": 2}]'

    result = StructuredAIRequirementExtractor().extract_ai({
        "requirements": [answer],
        "result_types": {"requirements": "answers"},
    })

    assert str(result.requirements[0].requirement_id) == requirement_id
    assert result.requirements[0].source_section == "Support"


def test_answer_lane_accepts_markdown_json_and_multiple_answer_strings() -> None:
    first = '{"requirement_text": "The supplier must provide support.", "category": "support"}'
    second = '{"requirement_text": "The supplier shall encrypt data.", "category": "security"}'

    result = StructuredAIRequirementExtractor().extract_ai({
        "requirements": [f"```json\n[{first}]\n```", second],
    })

    assert len(result.requirements) == 2
    assert result.requirements[0].category == "support"
    assert result.requirements[1].category == "security"


def test_answer_lane_normalises_provider_requirement_ids() -> None:
    result = StructuredAIRequirementExtractor().extract_ai({
        "requirements": [
            '[{"requirement_id": "REQ-001", "requirement_text": "The supplier must provide support."}]',
        ],
    })

    assert len(result.requirements) == 1
    assert result.requirements[0].requirement_id
    assert result.requirements[0].requirement_text == "The supplier must provide support."


def test_answer_lane_ignores_non_structured_commentary_when_json_is_present() -> None:
    result = StructuredAIRequirementExtractor().extract_ai({
        "requirements": [
            "These are the extracted requirements:",
            "```json\n[{\"requirement_text\": \"The supplier must provide support.\"}]\n```",
        ],
    })

    assert len(result.requirements) == 1
    assert result.requirements[0].requirement_text == "The supplier must provide support."


def test_answer_lane_recovers_json_embedded_in_prose() -> None:
    result = StructuredAIRequirementExtractor().extract_ai({
        "requirements": [
            "The extracted data is below: [{\"requirement_text\": \"The supplier must provide support.\"}]",
        ],
    })

    assert len(result.requirements) == 1


def test_full_analysis_handoffs_end_with_pending_review() -> None:
    import asyncio

    bid = make_bid()
    requirement = ExtractedRequirement(requirement_id=uuid4(), requirement_text="The supplier must provide encrypted storage.")
    retrieved = RetrievalResult(
        document_name="security.pdf", source_path="security.pdf", page_number=1,
        section="Encryption", retrieved_text="The company provides encrypted storage.",
        similarity_score=0.9, metadata={"document_type": "pdf"},
    )

    class FakeAIExtractor:
        def extract_ai(self, response: dict) -> RequirementExtractionResult:
            return RequirementExtractionResult(requirements=[requirement], message="AI requirements found")

    class FakeCompliance:
        def __init__(self) -> None:
            self.received = []

        def analyze(self, requirements):
            self.received = list(requirements)
            return type("ComplianceOutput", (), {"results": [ComplianceResult(
                requirement=requirement, status=ComplianceStatus.covered, confidence=0.9,
                supporting_evidence=[retrieved], evidence_missing=False, explanation="supported",
            )]})()

    class FakeResponses:
        def __init__(self) -> None:
            self.received = []

        def generate(self, requirements, compliance_results) -> ProposedBidResponse:
            self.received = list(compliance_results)
            return ProposedBidResponse(responses=[RequirementResponse(
                requirement_id=str(requirement.requirement_id),
                requirement_text=requirement.requirement_text,
                proposed_response="Grounded response.", compliance_status="COVERED",
                confidence=0.9, supporting_evidence=[retrieved], needs_human_review=False,
            )], message="proposed responses generated")

    class FakePipeline:
        async def analyze(self, bid: Bid, document: bytes) -> dict:
            return {"data": {"text": "Parser output is retained as source context."}}

        async def generate(self, bid: Bid, document: bytes) -> dict:
            raise AssertionError("generate was not expected")

    compliance = FakeCompliance()
    responses = FakeResponses()
    reviews = ReviewService()
    result = asyncio.run(BidAnalysisOrchestrator(
        FakePipeline(),
        ai_extractor=FakeAIExtractor(),
        compliance=compliance,
        response_generation=responses,
        review=reviews,
    ).analyze(bid, b"rfp"))

    assert result.extraction_mode == "rocketride_ai"
    assert result.requirements == [requirement]
    assert compliance.received == [requirement]
    assert responses.received[0].supporting_evidence == [retrieved]
    assert len(result.review_ids) == 1
    assert reviews.get_item(UUID(result.review_ids[0])).review_status == ReviewStatus.pending