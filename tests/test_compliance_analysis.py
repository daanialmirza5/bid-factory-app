from uuid import uuid4

from backend.schemas.compliance import ComplianceStatus
from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement
from backend.services.compliance_analysis import ComplianceAnalysisService


class StubRetriever:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.queries: list[str] = []

    def search(self, query: str) -> dict[str, object]:
        self.queries.append(query)
        return {"results": self.results, "message": "evidence found" if self.results else "no relevant evidence found"}


def requirement(text: str = "The supplier must provide encrypted storage") -> ExtractedRequirement:
    return ExtractedRequirement(requirement_id=uuid4(), requirement_text=text)


def evidence(text: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        document_name="security-policy.pdf",
        source_path="data/knowledge_base/security_policies/security-policy.pdf",
        page_number=4,
        section="Encryption",
        retrieved_text=text,
        similarity_score=score,
        metadata={"document_type": "pdf"},
    )


def test_strong_support_is_covered_and_returns_evidence() -> None:
    retriever = StubRetriever([evidence("The supplier provides encrypted storage for all customer data.", 0.92)])

    result = ComplianceAnalysisService(retriever).analyze([requirement()]).results[0]

    assert result.status == ComplianceStatus.covered
    assert 0 <= result.confidence <= 1
    assert result.evidence_missing is False
    assert result.supporting_evidence[0].document_name == "security-policy.pdf"
    assert result.supporting_evidence[0].page_number == 4


def test_partial_support_is_not_marked_covered() -> None:
    retriever = StubRetriever([evidence("The supplier encrypts customer data in transit.", 0.65)])

    result = ComplianceAnalysisService(retriever).analyze([requirement()]).results[0]

    assert result.status == ComplianceStatus.partially_covered
    assert result.status != ComplianceStatus.covered


def test_missing_evidence_is_not_found() -> None:
    result = ComplianceAnalysisService(StubRetriever([])).analyze([requirement()]).results[0]

    assert result.status == ComplianceStatus.not_found
    assert result.confidence == 0
    assert result.evidence_missing is True
    assert result.supporting_evidence == []


def test_ambiguous_evidence_requires_human_review() -> None:
    retriever = StubRetriever([evidence("The company offers storage services and customer support.", 0.52)])

    result = ComplianceAnalysisService(retriever).analyze([requirement()]).results[0]

    assert result.status == ComplianceStatus.needs_human_review
    assert result.evidence_missing is False


def test_unrelated_evidence_never_becomes_covered() -> None:
    retriever = StubRetriever([evidence("The company has offices in three countries.", 0.99)])

    result = ComplianceAnalysisService(retriever).analyze([requirement()]).results[0]

    assert result.status != ComplianceStatus.covered
    assert result.status == ComplianceStatus.needs_human_review


def test_empty_requirements_are_handled() -> None:
    result = ComplianceAnalysisService(StubRetriever([])).analyze([])

    assert result.results == []
    assert result.message == "no requirements available for analysis"