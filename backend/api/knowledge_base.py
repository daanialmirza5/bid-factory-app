from fastapi import APIRouter, Query

from backend.schemas.rag import KnowledgeBaseSearchResponse
from backend.services.knowledge_base import knowledge_base_service


router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])
@router.get("/search", response_model=KnowledgeBaseSearchResponse)
def search_knowledge_base(query: str = Query(min_length=1, max_length=5000)) -> KnowledgeBaseSearchResponse:
    return KnowledgeBaseSearchResponse(query=query, **knowledge_base_service.search(query))