from backend.schemas.compliance import ComplianceResult, ComplianceStatus, ConflictAnalysis, ConflictSeverity
from uuid import uuid4

from backend.schemas.compliance import ComplianceResult, ComplianceStatus
from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement
from backend.services.response_generation import ResponseGenerationService


def make_requirement(text: str = "The supplier must provide encrypted storage") -> ExtractedRequirement:
    return ExtractedRequirement(requirement_id=uuid4(), requirement_text=text)


def make_evidence(text: str) -> RetrievalResult:
    return RetrievalResult(
        document_name="security-policy.pdf",
        source_path="data/knowledge_base/security_policies/security-policy.pdf",
        page_number=4,
        section="Encryption",
        retrieved_text=text,
        similarity_score=0.92,
        metadata={"document_type": "pdf"},
    )


def make_compliance(requirement: ExtractedRequirement, status: ComplianceStatus, evidence: list[RetrievalResult]) -> ComplianceResult:
    return ComplianceResult(
        requirement=requirement,
        status=status,
        confidence=0.9 if evidence else 0.0,
        supporting_evidence=evidence,
        evidence_missing=not evidence,
        explanation="test result",
    )


def test_strong_evidence_generates_grounded_response() -> None:
    requirement = make_requirement()
    evidence = [make_evidence("The company provides encrypted storage for customer data.")]

    response = ResponseGenerationService().generate(
        [requirement], [make_compliance(requirement, ComplianceStatus.covered, evidence)]
    ).responses[0]

    assert response.requirement_id == str(requirement.requirement_id)
    assert response.requirement_text == requirement.requirement_text
    assert response.compliance_status == "COVERED"
    assert response.needs_human_review is False
    assert "encrypted storage" in response.proposed_response
    assert "security-policy.pdf" in response.proposed_response
    assert response.supporting_evidence == evidence


def test_partial_evidence_is_limited_and_requires_review() -> None:
    requirement = make_requirement()
    evidence = [make_evidence("The company encrypts customer data in transit.")]

    response = ResponseGenerationService().generate(
        [requirement], [make_compliance(requirement, ComplianceStatus.partially_covered, evidence)]
    ).responses[0]

    assert response.compliance_status == "PARTIALLY_COVERED"
    assert response.needs_human_review is True
    assert "remaining requirement details" in response.proposed_response
    assert "security-policy.pdf" in response.proposed_response


def test_missing_evidence_never_invents_a_response() -> None:
    requirement = make_requirement()

    response = ResponseGenerationService().generate(
        [requirement], [make_compliance(requirement, ComplianceStatus.not_found, [])]
    ).responses[0]

    assert response.compliance_status == "NOT_FOUND"
    assert response.needs_human_review is True
    assert response.supporting_evidence == []
    assert "unavailable" in response.proposed_response
    assert "encrypted storage" not in response.proposed_response


def test_ambiguous_evidence_requires_human_review() -> None:
    requirement = make_requirement()
    evidence = [make_evidence("The company offers storage services.")]

    response = ResponseGenerationService().generate(
        [requirement], [make_compliance(requirement, ComplianceStatus.needs_human_review, evidence)]
    ).responses[0]

    assert response.compliance_status == "NEEDS_HUMAN_REVIEW"
    assert response.needs_human_review is True
    assert response.supporting_evidence == evidence


def test_missing_compliance_result_is_safe() -> None:
    requirement = make_requirement()

    response = ResponseGenerationService().generate([requirement], []).responses[0]

    assert response.compliance_status == "NOT_FOUND"
    assert response.needs_human_review is True
    assert response.confidence == 0


def test_conflict_forces_review_without_changing_compliance_status() -> None:
    requirement = make_requirement()
    evidence = [make_evidence("The company provides encrypted storage.")]
    compliance = make_compliance(requirement, ComplianceStatus.covered, evidence)
    compliance.conflict_analysis = ConflictAnalysis(
        conflict_detected=True,
        severity=ConflictSeverity.medium,
        reason="Evidence conflicts with the requirement.",
        conflicting_evidence=evidence,
    )

    response = ResponseGenerationService().generate([requirement], [compliance]).responses[0]

    assert response.compliance_status == "COVERED"
    assert response.needs_human_review is True
