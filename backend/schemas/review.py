from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.schemas.rag import RetrievalResult


class ReviewStatus(str, Enum):
    pending = "PENDING"
    approved = "APPROVED"
    rejected = "REJECTED"
    needs_revision = "NEEDS_REVISION"


class ReviewItem(BaseModel):
    review_id: UUID = Field(default_factory=uuid4)
    bid_id: UUID
    requirement_id: UUID
    proposed_response: str
    compliance_status: str
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[RetrievalResult] = Field(default_factory=list)
    conflict_analysis: dict | None = None
    review_status: ReviewStatus = ReviewStatus.pending
    reviewer_comment: str | None = None
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    audit_log: list["ReviewAuditEntry"] = Field(default_factory=list)


class ReviewAuditEntry(BaseModel):
    previous_status: ReviewStatus
    new_status: ReviewStatus
    reviewer: str | None = None
    reviewer_comment: str | None = None
    reviewed_at: datetime


class ReviewCommentRequest(BaseModel):
    reviewer_comment: str = Field(default="No comment provided", max_length=5000)
    reviewer: str | None = Field(default=None, max_length=255)


class ReviewStatusResponse(BaseModel):
    bid_id: UUID
    status: str
    total_items: int
    pending_items: int
    approved_items: int
    rejected_items: int
    needs_revision_items: int
    items: list[ReviewItem] = Field(default_factory=list)


class ReviewCollectionResponse(BaseModel):
    bid_id: UUID | None = None
    items: list[ReviewItem] = Field(default_factory=list)
    total_pending: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_needs_revision: int = 0


class ReviewGenerationItem(BaseModel):
    requirement_id: UUID
    proposed_response: str
    compliance_status: str
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[RetrievalResult] = Field(default_factory=list)