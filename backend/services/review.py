from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from backend.schemas.review import (
    ReviewAuditEntry,
    ReviewCommentRequest,
    ReviewItem,
    ReviewStatus,
    ReviewStatusResponse,
)


class ReviewStore:
    def save_review_item(self, item: ReviewItem) -> ReviewItem: ...

    def get_review_item(self, review_id: UUID) -> ReviewItem | None: ...

    def list_review_items(self, bid_id: UUID) -> list[ReviewItem]: ...


class ReviewService:
    def __init__(self, store: ReviewStore | None = None) -> None:
        self._store = store
        self._items: dict[UUID, ReviewItem] = {}

    def create_pending(
        self,
        *,
        bid_id: UUID,
        requirement_id: UUID,
        proposed_response: str,
        compliance_status: str,
        confidence: float,
        supporting_evidence: list,
        conflict_analysis: dict | None = None
    ) -> ReviewItem:
        item = ReviewItem(
            bid_id=bid_id,
            requirement_id=requirement_id,
            proposed_response=proposed_response,
            compliance_status=compliance_status,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            conflict_analysis=conflict_analysis,
        )
        if self._store is None:
            self._items[item.review_id] = item
        else:
            self._store.save_review_item(item)
        return item

    def get_item(self, review_id: UUID) -> ReviewItem:
        item = self._store.get_review_item(review_id) if self._store else self._items.get(review_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Review item {review_id} was not found.")
        return item

    def list_for_bid(self, bid_id: UUID) -> list[ReviewItem]:
        if self._store:
            return self._store.list_review_items(bid_id)
        return [item for item in self._items.values() if item.bid_id == bid_id]

    def transition(
        self,
        review_id: UUID,
        new_status: ReviewStatus,
        reviewer_comment: str | None = None,
        reviewer: str | None = None,
    ) -> ReviewItem:
        item = self.get_item(review_id)
        if new_status in {ReviewStatus.rejected, ReviewStatus.needs_revision} and not reviewer_comment:
            raise HTTPException(status_code=422, detail="A reviewer comment is required for this decision.")
        previous_status = item.review_status
        reviewed_at = datetime.now(timezone.utc)
        item.review_status = new_status
        item.reviewer_comment = reviewer_comment
        item.reviewer = reviewer
        item.reviewed_at = reviewed_at
        item.audit_log.append(ReviewAuditEntry(
            previous_status=previous_status,
            new_status=new_status,
            reviewer=reviewer,
            reviewer_comment=reviewer_comment,
            reviewed_at=reviewed_at,
        ))
        return item

    def update_comment(self, review_id: UUID, request: ReviewCommentRequest) -> ReviewItem:
        item = self.get_item(review_id)
        item.reviewer_comment = request.reviewer_comment
        item.reviewer = request.reviewer
        return item

    def get_status(self, bid_id: UUID) -> ReviewStatusResponse:
        items = self.list_for_bid(bid_id)
        counts = {review_status: sum(item.review_status is review_status for item in items) for review_status in ReviewStatus}
        ready = bool(items) and counts[ReviewStatus.pending] == 0 and counts[ReviewStatus.needs_revision] == 0 and counts[ReviewStatus.rejected] == 0
        return ReviewStatusResponse(
            bid_id=bid_id,
            status="READY_FOR_SUBMISSION" if ready else "IN_REVIEW",
            total_items=len(items),
            pending_items=counts[ReviewStatus.pending],
            approved_items=counts[ReviewStatus.approved],
            rejected_items=counts[ReviewStatus.rejected],
            needs_revision_items=counts[ReviewStatus.needs_revision],
            items=items,
        )


review_service = ReviewService()