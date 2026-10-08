from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RFPTextSegment(BaseModel):
    text: str
    source_section: str | None = None
    source_page: int | None = Field(default=None, ge=1)


class ExtractedRequirement(BaseModel):
    requirement_id: UUID = Field(default_factory=uuid4)
    requirement_text: str
    category: str | None = None
    priority: str | None = None
    deadline: str | None = None
    compliance_type: str | None = None
    source_section: str | None = None
    source_page: int | None = Field(default=None, ge=1)


class RequirementExtractionResult(BaseModel):
    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    message: str