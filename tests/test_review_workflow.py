from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.schemas.compliance import ComplianceStatus
from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement
from backend.schemas.response_generation import RequirementResponse
from backend.schemas.review import ReviewCommentRequest, ReviewStatus
from backend.services.review import ReviewService


def make_item(service: ReviewService, status: str = "COVERED", evidence: list[RetrievalResult] | None = None):
    return service.create_pending(
        bid_id=uuid4(),
        requirement_id=uuid4(),
        proposed_response="Evidence-grounded draft.",
        compliance_status=status,
        confidence=0.8,
        supporting_evidence=evidence or [],
    )


def test_new_response_starts_pending() -> None:
    service = ReviewService()
    item = make_item(service)

    assert item.review_status == ReviewStatus.pending
    assert item.reviewed_at is None
    assert item.audit_log == []


def test_approval_requires_explicit_transition_and_records_audit() -> None:
    service = ReviewService()
    item = make_item(service)

    approved = service.transition(item.review_id, ReviewStatus.approved, reviewer="reviewer@example.com")

    assert approved.review_status == ReviewStatus.approved
    assert approved.reviewer == "reviewer@example.com"
    assert approved.audit_log[0].previous_status == ReviewStatus.pending
    assert approved.audit_log[0].new_status == ReviewStatus.approved
    assert approved.audit_log[0].reviewer == "reviewer@example.com"
    assert approved.reviewed_at is not None


def test_rejection_requires_comment_and_preserves_comment() -> None:
    service = ReviewService()
    item = make_item(service)

    with pytest.raises(HTTPException):
        service.transition(item.review_id, ReviewStatus.rejected)
    rejected = service.transition(item.review_id, ReviewStatus.rejected, "Unsupported claim", "reviewer")

    assert rejected.review_status == ReviewStatus.rejected
    assert rejected.reviewer_comment == "Unsupported claim"
    assert rejected.audit_log[0].reviewer_comment == "Unsupported claim"


def test_needs_revision_requires_reason() -> None:
    service = ReviewService()
    item = make_item(service)

    with pytest.raises(HTTPException):
        service.transition(item.review_id, ReviewStatus.needs_revision)
    revised = service.transition(item.review_id, ReviewStatus.needs_revision, "Add the delivery timeline", "reviewer")

    assert revised.review_status == ReviewStatus.needs_revision
    assert revised.reviewer_comment == "Add the delivery timeline"


def test_bid_is_not_ready_while_items_are_pending() -> None:
    service = ReviewService()
    item = make_item(service)
    status = service.get_status(item.bid_id)

    assert status.status == "IN_REVIEW"
    assert status.pending_items == 1


def test_bid_is_ready_only_when_all_items_are_approved() -> None:
    service = ReviewService()
    first = make_item(service)
    second = service.create_pending(
        bid_id=first.bid_id,
        requirement_id=uuid4(),
        proposed_response="Second draft.",
        compliance_status="NOT_FOUND",
        confidence=0,
        supporting_evidence=[],
    )

    service.transition(first.review_id, ReviewStatus.approved, "Reviewed", "reviewer")
    assert service.get_status(first.bid_id).status == "IN_REVIEW"
    service.transition(second.review_id, ReviewStatus.approved, "Reviewed despite missing evidence", "reviewer")

    ready = service.get_status(first.bid_id)
    assert ready.status == "READY_FOR_SUBMISSION"
    assert ready.approved_items == 2


def test_rejected_or_revision_items_block_readiness() -> None:
    service = ReviewService()
    item = make_item(service)
    service.transition(item.review_id, ReviewStatus.rejected, "Does not meet scope", "reviewer")
    assert service.get_status(item.bid_id).status == "IN_REVIEW"

    service.transition(item.review_id, ReviewStatus.needs_revision, "Revise scope", "reviewer")
    assert service.get_status(item.bid_id).status == "IN_REVIEW"


def test_missing_evidence_remains_visible_and_comments_can_be_updated() -> None:
    service = ReviewService()
    item = make_item(service, status="NOT_FOUND")

    updated = service.update_comment(item.review_id, ReviewCommentRequest(reviewer_comment="Supply evidence before approval."))

    assert updated.compliance_status == "NOT_FOUND"
    assert updated.supporting_evidence == []
    assert updated.review_status == ReviewStatus.pending
    assert updated.reviewer_comment == "Supply evidence before approval."
