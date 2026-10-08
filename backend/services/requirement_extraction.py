import re
import json
from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from backend.schemas.requirements import (
    ExtractedRequirement,
    RFPTextSegment,
    RequirementExtractionResult,
)


class RequirementExtractor(Protocol):
    def extract(self, text: str | Iterable[RFPTextSegment]) -> RequirementExtractionResult: ...


class AIRequirementExtractor(Protocol):
    def extract_ai(self, pipeline_response: dict[str, object]) -> RequirementExtractionResult: ...


class AIExtractionError(ValueError):
    """Raised when a RocketRide AI response is not valid structured output."""


class StructuredAIRequirementExtractor:
    """Validate structured requirements returned by an AI-capable pipeline."""

    EXTRACTION_INSTRUCTION = (
        "Extract only explicit requirements from the RFP. Split compound requirements into atomic requirements. "
        "Preserve the original wording and source page/section when available. Return structured JSON matching "
        "the requirement schema. Use null for unavailable optional fields. Never invent requirements, deadlines, "
        "priorities, certifications, capabilities, or other missing information."
    )

    def extract_ai(self, pipeline_response: dict[str, object]) -> RequirementExtractionResult:
        payload = pipeline_response.get("data", pipeline_response)
        candidates = self._find_requirements(payload)
        if candidates is None:
            raise AIExtractionError("RocketRide AI output did not contain structured requirements.")
        if not isinstance(candidates, list):
            raise AIExtractionError("RocketRide AI requirements must be a JSON array.")
        error_candidate = next((c for c in candidates if isinstance(c, str) and c.lstrip().startswith("**LLM error**")), None)
        if error_candidate:
            print(f"DEBUG LLM CANDIDATE: {candidates}")
            raise AIExtractionError(f"RocketRide LLM returned an error instead of requirements: {error_candidate}")
        try:
            requirements = [ExtractedRequirement.model_validate(self._normalise_candidate(candidate)) for candidate in candidates]
        except Exception as exc:
            raise AIExtractionError("RocketRide AI requirements failed schema validation.") from exc
        return RequirementExtractionResult(
            requirements=requirements,
            message="AI requirements found" if requirements else "no explicit requirements found",
        )

    @staticmethod
    def _normalise_candidate(candidate: object) -> object:
        if not isinstance(candidate, dict) or "requirement_id" not in candidate:
            return candidate
        requirement_id = candidate["requirement_id"]
        try:
            UUID(str(requirement_id))
        except (ValueError, TypeError, AttributeError):
            normalised = dict(candidate)
            normalised.pop("requirement_id", None)
            return normalised
        return candidate

    @classmethod
    def _find_requirements(cls, payload: object) -> list[object] | None:
        if isinstance(payload, list):
            return cls._parse_answer_list(payload)
        if isinstance(payload, dict):
            for key in ("requirements", "ai_requirements", "structured_requirements"):
                if key in payload:
                    value = payload[key]
                    if isinstance(value, list):
                        return cls._parse_answer_list(value)
                    return cls._find_requirements(value)
            result_types = payload.get("result_types")
            if isinstance(result_types, dict):
                for key, lane_type in result_types.items():
                    if lane_type == "answers" and key in payload:
                        return cls._find_requirements(payload[key])
            for key in ("text", "content", "value"):
                value = payload.get(key)
                parsed = cls._parse_json(value)
                if parsed is not None:
                    return cls._find_requirements(parsed)
            return None
        parsed = cls._parse_json(payload)
        if isinstance(parsed, list):
            return cls._parse_answer_list(parsed)
        if isinstance(parsed, dict):
            return cls._find_requirements(parsed)
        return None

    @classmethod
    def _parse_answer_list(cls, values: list[object]) -> list[object] | None:
        parsed_values: list[object] = []
        for value in values:
            if isinstance(value, dict) and "answer" in value:
                nested = cls._find_requirements(value["answer"])
                if nested is not None:
                    parsed_values.extend(nested)
                    continue
            if isinstance(value, str):
                parsed = cls._parse_json(value)
                if parsed is not None:
                    if isinstance(parsed, dict) and "requirement_text" in parsed:
                        parsed_values.append(parsed)
                        continue
                    nested = cls._find_requirements(parsed)
                    if nested is not None:
                        parsed_values.extend(nested)
                        continue
            parsed_values.append(value)
        if parsed_values and any(isinstance(value, dict) for value in parsed_values):
            parsed_values = [value for value in parsed_values if isinstance(value, dict)]
            return parsed_values
        if parsed_values and len(parsed_values) != len(values):
            return parsed_values
        return values

    @staticmethod
    def _parse_json(value: object) -> object | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        if value.startswith("```"):
            value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            for opening, closing in (("[", "]"), ("{", "}")):
                start = value.find(opening)
                end = value.rfind(closing)
                if start >= 0 and end > start:
                    try:
                        return json.loads(value[start:end + 1])
                    except json.JSONDecodeError:
                        continue
            return None


class RequirementExtractionService:
    """Extract explicitly stated requirements without adding unsupported facts."""

    _EXPLICIT_MARKERS = re.compile(
        r"\b(?:must|shall|required to|required that|mandatory|obligated to|will be required to)\b",
        re.IGNORECASE,
    )
    _DEADLINE = re.compile(
        r"\b(?:by|before| no later than|within)\s+([^.;,]+)",
        re.IGNORECASE,
    )
    _COMPLIANCE = re.compile(
        r"\b(?:comply with|compliance with|conform to|certified to|certification(?: in| for)?)\s+(.+?)(?=\s+\b(?:by|before|within|no later than)\b|[.;,]|$)",
        re.IGNORECASE,
    )
    _CATEGORY_HINTS = (
        ("security", ("security", "cybersecurity", "encryption", "encrypt", "penetration")),
        ("technical", ("technical", "api", "integration", "availability", "uptime")),
        ("commercial", ("price", "pricing", "cost", "invoice", "payment")),
        ("delivery", ("deliver", "implementation", "deployment", "schedule")),
        ("support", ("support", "maintenance", "service desk")),
    )

    def extract(self, text: str | Iterable[RFPTextSegment]) -> RequirementExtractionResult:
        segments = self._normalise_segments(text)
        extracted: list[ExtractedRequirement] = []
        for segment in segments:
            for statement in self._atomic_statements(segment.text):
                if not self._EXPLICIT_MARKERS.search(statement):
                    continue
                requirement_text = self._clean_statement(statement)
                if not requirement_text:
                    continue
                extracted.append(self._build_requirement(requirement_text, segment))
        message = "requirements found" if extracted else "no explicit requirements found"
        return RequirementExtractionResult(requirements=extracted, message=message)

    @staticmethod
    def _normalise_segments(text: str | Iterable[RFPTextSegment]) -> list[RFPTextSegment]:
        if isinstance(text, str):
            return [RFPTextSegment(text=text)] if text.strip() else []
        return [segment for segment in text if segment.text.strip()]

    @staticmethod
    def _atomic_statements(text: str) -> list[str]:
        statements: list[str] = []
        for line in re.split(r"[\r\n]+", text):
            line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if not line:
                continue
            sentences = re.split(r"(?<=[.!?])\s+|\s*;\s*", line)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                clauses = re.split(
                    r"\s+(?=and\s+(?:must|shall|required to|is required to)\b)",
                    sentence,
                    flags=re.IGNORECASE,
                )
                statements.extend(clause.strip() for clause in clauses if clause.strip())
        return statements

    def _build_requirement(self, requirement_text: str, segment: RFPTextSegment) -> ExtractedRequirement:
        deadline_match = self._DEADLINE.search(requirement_text)
        compliance_match = self._COMPLIANCE.search(requirement_text)
        lowered = requirement_text.lower()
        category = next(
            (name for name, hints in self._CATEGORY_HINTS if any(hint in lowered for hint in hints)),
            None,
        )
        priority_match = re.search(
            r"\b(?:priority|severity)\s*[:=-]?\s*(high|medium|low|critical)\b",
            segment.text.lower(),
        )
        return ExtractedRequirement(
            requirement_text=requirement_text,
            category=category,
            priority=priority_match.group(1) if priority_match else None,
            deadline=deadline_match.group(1).strip() if deadline_match else None,
            compliance_type=compliance_match.group(1).strip() if compliance_match else None,
            source_section=segment.source_section,
            source_page=segment.source_page,
        )

    @staticmethod
    def _clean_statement(statement: str) -> str:
        return re.sub(r"\s+", " ", statement).strip(" -\t")


requirement_extraction_service = RequirementExtractionService()
ai_requirement_extraction_service = StructuredAIRequirementExtractor()