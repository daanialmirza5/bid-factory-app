from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from backend.schemas.rag import RetrievalResult
from backend.schemas.requirements import ExtractedRequirement


class ComplianceStatus(str, Enum):
    covered = "COVERED"
    partially_covered = "PARTIALLY_COVERED"
    not_found = "NOT_FOUND"
    needs_human_review = "NEEDS_HUMAN_REVIEW"


class ConflictSeverity(str, Enum):
    no_conflict = "NO_CONFLICT"
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


class ConflictAnalysis(BaseModel):
    conflict_detected: bool
    severity: ConflictSeverity
    reason: str
    conflicting_evidence: list[RetrievalResult] = Field(default_factory=list)


class ComplianceResult(BaseModel):
    requirement: ExtractedRequirement
    status: ComplianceStatus
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[RetrievalResult] = Field(default_factory=list)
    evidence_missing: bool
    explanation: str
    conflict_analysis: ConflictAnalysis | None = None


class ComplianceAnalysisResult(BaseModel):
    results: list[ComplianceResult] = Field(default_factory=list)
    message: str


class EvidenceRetriever(Protocol):
    def search(self, query: str) -> dict[str, Any]: ...