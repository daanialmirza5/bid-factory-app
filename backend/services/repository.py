from uuid import UUID
from uuid import uuid4

from fastapi import HTTPException, status

from backend.models.entities import Bid, Requirement, Review, RFP
from backend.schemas.requests import ReviewRequest
from backend.schemas.review import ReviewItem


class InMemoryRepository:
    def __init__(self) -> None:
        self._bids: dict[UUID, Bid] = {}
        self._requirements: dict[UUID, Requirement] = {}
        self._documents: dict[UUID, bytes] = {}
        self._review_items: dict[UUID, ReviewItem] = {}

    def create_bid(
        self,
        *,
        filename: str,
        title: str,
        content_type: str | None,
        file_type: str,
        file_size: int,
        document: bytes,
    ) -> Bid:
        bid_id = uuid4()
        bid = Bid(
            id=bid_id,
            bid_id=bid_id,
            rfp=RFP(
                filename=filename,
                title=title,
                content_type=content_type,
                file_type=file_type,
                file_size=file_size,
            )
        )
        self._bids[bid.id] = bid
        self._documents[bid.id] = document
        return bid

    def get_bid(self, bid_id: UUID) -> Bid:
        bid = self._bids.get(bid_id)
        if bid is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bid {bid_id} was not found.",
            )
        return bid

    def get_requirements(self, bid_id: UUID) -> list[Requirement]:
        return [requirement for requirement in self._requirements.values() if requirement.bid_id == bid_id]

    def get_document(self, bid_id: UUID) -> bytes:
        self.get_bid(bid_id)
        return self._documents[bid_id]

    def add_review(self, requirement_id: UUID, request: ReviewRequest) -> Review:
        requirement = self._requirements.get(requirement_id)
        if requirement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requirement {requirement_id} was not found.",
            )
        review = Review(requirement_id=requirement_id, **request.model_dump())
        requirement.reviews.append(review)
        return review

    def save_review_item(self, item: ReviewItem) -> ReviewItem:
        self._review_items[item.review_id] = item
        return item

    def get_review_item(self, review_id: UUID) -> ReviewItem | None:
        return self._review_items.get(review_id)

    def list_review_items(self, bid_id: UUID) -> list[ReviewItem]:
        return [item for item in self._review_items.values() if item.bid_id == bid_id]


repository = InMemoryRepository()