from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    id: UUID
    document_hash: str
    document_name: str
    document_type: str
    source_path: str
    text: str
    page_number: int | None = None
    section: str | None = None
    chunk_index: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    document_name: str
    source_path: str
    page_number: int | None = None
    section: str | None = None
    retrieved_text: str
    similarity_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeBaseDocument(BaseModel):
    document_name: str
    document_type: str
    source_path: str
    document_hash: str
    chunk_count: int = Field(ge=0)
    ingested_at: datetime


class KnowledgeBaseSearchResponse(BaseModel):
    query: str
    results: list[RetrievalResult] = Field(default_factory=list)
    message: str