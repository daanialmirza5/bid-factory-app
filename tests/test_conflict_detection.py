import pytest
from uuid import uuid4
from backend.schemas.compliance import ConflictSeverity
from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement
from backend.services.compliance_analysis import ConflictDetectionService

def requirement(text: str) -> ExtractedRequirement:
    return ExtractedRequirement(requirement_id=uuid4(), requirement_text=text)

def evidence(text: str) -> RetrievalResult:
    return RetrievalResult(
        document_name="test.pdf",
        source_path="data/test.pdf",
        page_number=1,
        section="test",
        retrieved_text=text,
        similarity_score=1.0,
        metadata={}
    )

def test_no_contradiction():
    req = requirement("Must be encrypted")
    ev = [evidence("We use AES encrypted storage")]
    res = ConflictDetectionService().detect(req, ev)
    assert res.conflict_detected is False
    assert res.severity == ConflictSeverity.no_conflict

def test_direct_contradiction():
    req = requirement("Must be available 24/7")
    ev = [evidence("Available Monday-Friday during business hours")]
    res = ConflictDetectionService().detect(req, ev)
    assert res.conflict_detected is True
    assert res.severity == ConflictSeverity.medium
    assert res.conflicting_evidence == ev

def test_evidence_contradiction():
    req = requirement("General requirement")
    ev1 = evidence("The system is certified.")
    ev2 = evidence("The system is not certified.")
    res = ConflictDetectionService().detect(req, [ev1, ev2])
    assert res.conflict_detected is True
    assert res.severity == ConflictSeverity.high
    assert res.conflicting_evidence == [ev1, ev2]

def test_availability_percentage_contradiction():
    req = requirement("System must have 99.9% availability")
    ev = [evidence("We offer 99.5% availability")]
    res = ConflictDetectionService().detect(req, ev)
    assert res.conflict_detected is True

def test_availability_percentage_no_contradiction():
    req = requirement("System must have 99.9% availability")
    ev = [evidence("We guarantee 99.99% availability for all users")]
    res = ConflictDetectionService().detect(req, ev)
    assert res.conflict_detected is False
