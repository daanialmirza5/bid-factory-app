from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BidStatus(str, Enum):
    uploaded = "uploaded"
    analyzing = "analyzing"
    review = "review"
    complete = "complete"


class ProcessingStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RequirementStatus(str, Enum):
    pending = "pending"
    compliant = "compliant"
    gap = "gap"
    needs_review = "needs_review"


class RFP(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str
    title: str
    content_type: str | None = None
    file_type: str
    file_size: int = Field(ge=0)
    uploaded_at: datetime = Field(default_factory=utc_now)


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    source: str
    excerpt: str
    relevance_score: float | None = Field(default=None, ge=0, le=1)


class Review(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    decision: str
    comment: str | None = None
    reviewer: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Requirement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID | None = None
    bid_id: UUID
    reference: str
    text: str
    requirement_text: str | None = None
    category: str | None = None
    priority: str | None = None
    deadline: str | None = None
    compliance_type: str | None = None
    source_section: str | None = None
    source_page: int | None = Field(default=None, ge=1)
    status: RequirementStatus = RequirementStatus.pending
    evidence: list[Evidence] = Field(default_factory=list)
    reviews: list[Review] = Field(default_factory=list)


class Bid(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    bid_id: UUID
    rfp: RFP
    status: BidStatus = BidStatus.uploaded
    processing_status: ProcessingStatus = ProcessingStatus.uploaded
    requirements: list[Requirement] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)