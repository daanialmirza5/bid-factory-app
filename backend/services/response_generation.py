import logging
import re
from collections import Counter
from collections.abc import Iterable

from backend.schemas.compliance import ComplianceResult, ComplianceStatus
from backend.schemas.compliance import ConflictSeverity
from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement
from backend.schemas.response_generation import ProposedBidResponse, RequirementResponse


logger = logging.getLogger(__name__)

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)

# Counts LLM drafts and how many the figure check rejected; read by eval/run_eval.py.
draft_stats: Counter[str] = Counter()


def unsupported_numbers(draft: str, *sources: str) -> list[str]:
    """Return figures in a draft that appear in none of the sources. List numbering is ignored."""
    available = {number for source in sources for number in _NUMBER.findall(source)}
    return [number for number in _NUMBER.findall(_LIST_MARKER.sub("", draft)) if number not in available]


class ResponseGenerationService:
    """Build proposal-ready drafts from requirements and verified evidence only."""

    def generate(
        self,
        requirements: Iterable[ExtractedRequirement],
        compliance_results: Iterable[ComplianceResult],
    ) -> ProposedBidResponse:
        compliance_by_id = {
            result.requirement.requirement_id: result
            for result in compliance_results
        }
        responses: list[RequirementResponse] = []
        for requirement in requirements:
            compliance = compliance_by_id.get(requirement.requirement_id)
            if compliance is None:
                responses.append(self._without_analysis(requirement))
                continue
            responses.append(self._generate_response(compliance))
        return ProposedBidResponse(
            responses=responses,
            message="proposed responses generated" if responses else "no requirements available for response generation",
        )

    @staticmethod
    def _without_analysis(requirement: ExtractedRequirement) -> RequirementResponse:
        return RequirementResponse(
            requirement_id=str(requirement.requirement_id),
            requirement_text=requirement.requirement_text,
            proposed_response="Company evidence is unavailable for this requirement. A human review is required before responding.",
            compliance_status="NOT_FOUND",
            confidence=0.0,
            needs_human_review=True,
        )

    def _generate_response(self, compliance: ComplianceResult) -> RequirementResponse:
        status = compliance.status.value
        evidence = compliance.supporting_evidence
        has_conflict = bool(
            compliance.conflict_analysis
            and compliance.conflict_analysis.severity is not ConflictSeverity.no_conflict
        )
        if compliance.status is ComplianceStatus.covered and evidence:
            proposed_response = self._covered_response(evidence, compliance.requirement.requirement_text)
            needs_human_review = has_conflict
        elif compliance.status is ComplianceStatus.partially_covered and evidence:
            proposed_response = self._partial_response(evidence, compliance.requirement.requirement_text)
            needs_human_review = True
        elif compliance.status is ComplianceStatus.not_found or not evidence:
            status = ComplianceStatus.not_found.value
            proposed_response = "Company evidence is unavailable for this requirement. A human review is required before responding."
            needs_human_review = True
        else:
            refs = ", ".join(self._reference(item) for item in evidence)
            statements = " ".join(item.retrieved_text for item in evidence)
            proposed_response = self._draft_with_llm(
                statements,
                "The evidence is ambiguous. Draft the best response you can, but note that it requires human review.",
                f"Based on available evidence in {refs}: {statements}. However, ambiguity in the match requires human review.",
                compliance.requirement.requirement_text,
            )
            needs_human_review = True
        return RequirementResponse(
            requirement_id=str(compliance.requirement.requirement_id),
            requirement_text=compliance.requirement.requirement_text,
            proposed_response=proposed_response,
            compliance_status=status,
            confidence=compliance.confidence,
            supporting_evidence=evidence,
            needs_human_review=needs_human_review,
        )

    @classmethod
    def _covered_response(cls, evidence: list[RetrievalResult], requirement: str = "") -> str:
        refs = ", ".join(cls._reference(item) for item in evidence)
        statements = " ".join(item.retrieved_text for item in evidence)
        return cls._draft_with_llm(
            statements,
            "This requirement is fully covered based on our documentation.",
            f"The company satisfies this requirement based on verified evidence in {refs}: {statements}",
            requirement,
        )

    @classmethod
    def _partial_response(cls, evidence: list[RetrievalResult], requirement: str = "") -> str:
        refs = ", ".join(cls._reference(item) for item in evidence)
        statements = " ".join(item.retrieved_text for item in evidence)
        return cls._draft_with_llm(
            statements,
            "This requirement is only partially covered based on our documentation. Emphasize what we DO have.",
            f"The company partially satisfies this requirement based on {refs}: {statements}. However, remaining requirement details require further verification.",
            requirement,
        )
        
    @staticmethod
    def _draft_with_llm(evidence_text: str, context: str, fallback_text: str, requirement: str = "") -> str:
        import os
        import groq
        api_key = os.getenv("ROCKETRIDE_GROQ_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            return fallback_text
        try:
            g_client = groq.Groq(api_key=api_key)
            completion = g_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional B2B RFP proposal writer. You will be provided with internal company evidence. Write a professional response to the requirement based strictly on the provided evidence. Do not make up information, and use only figures that appear in the evidence. If the evidence does not fully answer the requirement, say which part is not confirmed. Write two or three plain sentences with no tables, headings or lists. {context}"
                    },
                    {
                        "role": "user",
                        "content": f"Requirement:\n{requirement}\n\nCompany evidence:\n{evidence_text[:10000]}"
                    }
                ],
                temperature=0.2,
                max_tokens=500,
            )
            draft = completion.choices[0].message.content
            if not draft or not draft.strip():
                return fallback_text
            draft_stats["drafted"] += 1
            invented = unsupported_numbers(draft, evidence_text, requirement)
            if invented:
                draft_stats["rejected"] += 1
                logger.warning("Rejected a draft with figures not in the evidence: %s", invented)
                return fallback_text
            return draft
        except Exception as e:
            print("Groq API error in generation:", e)
            return fallback_text

    @staticmethod
    def _reference(evidence: RetrievalResult) -> str:
        document_name = evidence.document_name
        source_path = evidence.source_path
        page_number = evidence.page_number
        section = evidence.section
        location = ", ".join(
            value for value in [
                f"page {page_number}" if page_number is not None else None,
                f"section {section}" if section else None,
            ] if value
        )
        return f"{document_name} ({source_path}{', ' + location if location else ''})"


response_generation_service = ResponseGenerationService()