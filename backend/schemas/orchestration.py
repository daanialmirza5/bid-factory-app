from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.requirements import ExtractedRequirement
from backend.schemas.compliance import ComplianceResult
from backend.schemas.response_generation import RequirementResponse


class PipelineSourceMetadata(BaseModel):
    source_page: int | None = None
    source_section: str | None = None
    source_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BidAnalysisResult(BaseModel):
    bid_id: UUID
    processing_status: str
    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    compliance_results: list[ComplianceResult] = Field(default_factory=list)
    proposed_responses: list[RequirementResponse] = Field(default_factory=list)
    review_ids: list[str] = Field(default_factory=list)
    source_metadata: list[PipelineSourceMetadata] = Field(default_factory=list)
    extraction_mode: str | None = None
    errors: list[str] = Field(default_factory=list)