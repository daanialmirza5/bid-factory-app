import re
from collections.abc import Iterable
from dataclasses import dataclass

from backend.schemas.compliance import (
    ComplianceAnalysisResult,
    ComplianceResult,
    ComplianceStatus,
    ConflictAnalysis,
    ConflictSeverity,
    EvidenceRetriever,
)
from backend.schemas.requirements import ExtractedRequirement
from backend.schemas.rag import RetrievalResult


class ComplianceAnalysisService:
    """Compare extracted requirements only against retrieved company evidence."""

    _STOP_WORDS = {
        "a", "an", "and", "are", "be", "by", "for", "from", "in", "is", "it", "of", "on",
        "or", "shall", "should", "that", "the", "their", "this", "to", "with",
    }

    def __init__(self, retriever: EvidenceRetriever) -> None:
        self._retriever = retriever

    def analyze(self, requirements: Iterable[ExtractedRequirement]) -> ComplianceAnalysisResult:
        results = [self._analyze_requirement(requirement) for requirement in requirements]
        return ComplianceAnalysisResult(
            results=results,
            message="compliance analysis completed" if results else "no requirements available for analysis",
        )

    def _analyze_requirement(self, requirement: ExtractedRequirement) -> ComplianceResult:
        response = self._retriever.search(requirement.requirement_text)
        evidence = self._retrieved_results(response)
        conflict = ConflictDetectionService().detect(requirement, evidence)
        if not evidence:
            return ComplianceResult(
                requirement=requirement,
                status=ComplianceStatus.not_found,
                confidence=0.0,
                evidence_missing=True,
                explanation="No relevant company evidence was retrieved.",
                            conflict_analysis=conflict,
            )

        strongest = max(evidence, key=lambda item: item.similarity_score)
        requirement_terms = self._terms(requirement.requirement_text)
        evidence_terms = self._terms(" ".join(item.retrieved_text for item in evidence))
        overlap = len(requirement_terms & evidence_terms) / len(requirement_terms) if requirement_terms else 0.0
        score = max(0.0, min(1.0, strongest.similarity_score))

        if score >= 0.70 and overlap >= 0.5:
            status = ComplianceStatus.covered
            confidence = min(1.0, score + 0.3)
            explanation = "Retrieved evidence strongly supports the requirement."
        elif score >= 0.60 and overlap > 0:
            status = ComplianceStatus.partially_covered
            confidence = min(1.0, score + 0.1)
            explanation = "Retrieved evidence supports only part of the requirement."
        else:
            status = ComplianceStatus.needs_human_review
            confidence = min(1.0, 0.5 * score + 0.5 * overlap)
            explanation = "Evidence was retrieved, but its relationship to the requirement is ambiguous."

        return ComplianceResult(
            requirement=requirement,
            status=status,
            confidence=confidence,
            supporting_evidence=evidence,
            evidence_missing=False,
            explanation=explanation,
            conflict_analysis=conflict,
        )

    @staticmethod
    def _retrieved_results(response: dict[str, object]) -> list[RetrievalResult]:
        raw_results = response.get("results", [])
        return [result for result in raw_results if isinstance(result, RetrievalResult)]

    @classmethod
    def _terms(cls, text: str) -> set[str]:
        return {
            term for term in re.findall(r"[a-z0-9]+", text.lower())
            if len(term) > 2 and term not in cls._STOP_WORDS
        }


@dataclass(frozen=True)
class _EvidenceSignals:
    topic: str
    positive: bool
    negative: bool
    qualified: bool
    value: float | None = None


class ConflictDetectionService:
    """Detect explicit, explainable conflicts without changing compliance scoring."""

    _TOPIC_PATTERNS = {
        "availability": (r"\b24\s*/?\s*7\b|around the clock|always available", r"monday\s*-?\s*friday|mon\s*-?\s*fri|business hours|\b\d{1,2}\s*(?:am|pm)\b"),
        "encryption": (r"encrypted|encryption|encrypts", r"not encrypted|unencrypted|no encryption|does not encrypt"),
        "support": (r"support (?:is )?(?:available|provided)|provides? .*support|offers? .*support", r"unsupported|support .*unavailable|no support|does not provide .*support"),
        "certification": (r"certified|certification|holds? .*certificate", r"not certified|no certification|does not hold .*certificate|without certification"),
        "feature": (r"available|provides?|offers?|supports?", r"unavailable|not available|does not provide|unsupported|not supported"),
    }

    def detect(self, requirement: ExtractedRequirement, evidence: list[RetrievalResult]) -> ConflictAnalysis:
        if not evidence:
            return ConflictAnalysis(conflict_detected=False, severity=ConflictSeverity.no_conflict, reason="No evidence was retrieved, so no contradiction was assessed.")

        requirement_signals = self._signals(requirement.requirement_text)
        evidence_signals = [(item, self._signals(item.retrieved_text)) for item in evidence]
        for topic in requirement_signals:
            if topic == "availability_percentage":
                req_val = requirement_signals[topic][0].value
                if req_val is not None:
                    opposing = [item for item, signals in evidence_signals if "availability_percentage" in signals and signals["availability_percentage"][0].value is not None and signals["availability_percentage"][0].value < req_val]
                    if opposing:
                        return ConflictAnalysis(conflict_detected=True, severity=ConflictSeverity.medium, reason=f"Evidence offers lower availability than the required {req_val}%.", conflicting_evidence=opposing)
            else:
                opposing = [item for item, signals in evidence_signals if any(signal.negative for signal in signals.get(topic, [])) and any(signal.positive for signal in requirement_signals[topic])]
                if opposing:
                    return ConflictAnalysis(conflict_detected=True, severity=ConflictSeverity.medium, reason=f"Evidence explicitly conflicts with the requirement for {topic}.", conflicting_evidence=opposing)

        for index, (item, signals) in enumerate(evidence_signals):
            for other_item, other_signals in evidence_signals[index + 1:]:
                for topic in self._shared_topics(signals, other_signals):
                    if self._opposes(signals, other_signals, topic):
                        return ConflictAnalysis(conflict_detected=True, severity=ConflictSeverity.high, reason=f"Evidence sources explicitly contradict each other for {topic}.", conflicting_evidence=[item, other_item])

        for topic in requirement_signals:
            limited = [item for item, signals in evidence_signals if any(signal.topic == topic and signal.qualified and signal.negative for signal in signals.get(topic, []))]
            if limited:
                return ConflictAnalysis(conflict_detected=True, severity=ConflictSeverity.low, reason=f"Evidence contains a qualified or limited statement about {topic} that requires review.", conflicting_evidence=limited)

        return ConflictAnalysis(conflict_detected=False, severity=ConflictSeverity.no_conflict, reason="Retrieved evidence contains no reliable opposing signals.")

    @classmethod
    def _signals(cls, text: str) -> dict[str, list[_EvidenceSignals]]:
        lowered = text.lower()
        result: dict[str, list[_EvidenceSignals]] = {}
        for topic, (positive_pattern, negative_pattern) in cls._TOPIC_PATTERNS.items():
            positive = bool(re.search(positive_pattern, lowered))
            negative = bool(re.search(negative_pattern, lowered))
            if positive or negative:
                result[topic] = [_EvidenceSignals(topic, positive, negative, negative and any(word in lowered for word in ("limited", "subject to", "partial")))]
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", lowered)
        if match:
            result["availability_percentage"] = [_EvidenceSignals("availability_percentage", True, False, False, value=float(match.group(1)))]
        return result

    @staticmethod
    def _shared_topics(left: dict[str, list[_EvidenceSignals]], right: dict[str, list[_EvidenceSignals]]) -> set[str]:
        return set(left) & set(right)

    @staticmethod
    def _opposes(left: dict[str, list[_EvidenceSignals]], right: dict[str, list[_EvidenceSignals]], topic: str) -> bool:
        left_signal = left[topic][0]
        right_signal = right[topic][0]
        return (left_signal.positive and right_signal.negative) or (left_signal.negative and right_signal.positive)


def create_compliance_analysis_service(retriever: EvidenceRetriever) -> ComplianceAnalysisService:
    return ComplianceAnalysisService(retriever)