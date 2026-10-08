from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.compliance import ComplianceResult
from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement


class RequirementResponse(BaseModel):
    requirement_id: str
    requirement_text: str
    proposed_response: str
    compliance_status: str
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[RetrievalResult] = Field(default_factory=list)
    needs_human_review: bool


class ProposedBidResponse(BaseModel):
    responses: list[RequirementResponse] = Field(default_factory=list)
    message: str
    review_ids: list[str] = Field(default_factory=list)


class ProposedResponseRequest(BaseModel):
    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    compliance_results: list[ComplianceResult] = Field(default_factory=list)