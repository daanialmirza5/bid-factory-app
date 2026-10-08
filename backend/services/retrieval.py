from typing import Any

from backend.schemas.rag import RetrievalResult
from backend.services.embeddings import EmbeddingProvider
from backend.services.vector_store import SQLiteVectorStore


class RetrievalService:
    def __init__(self, embeddings: EmbeddingProvider, vector_store: SQLiteVectorStore, top_k: int, min_score: float) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._top_k = top_k
        self._min_score = min_score

    def search(self, query: str) -> dict[str, Any]:
        if not query.strip():
            return {"results": [], "message": "no relevant evidence found"}
        results: list[RetrievalResult] = self._vector_store.search(query, self._embeddings.embed([query])[0], self._top_k, self._min_score)
        return {"results": results, "message": "evidence found" if results else "no relevant evidence found"}