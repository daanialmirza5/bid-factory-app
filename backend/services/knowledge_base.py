from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.schemas.rag import KnowledgeBaseDocument
from backend.services.chunking import ChunkingService
from backend.services.document_ingestion import DocumentIngestionService
from backend.services.embeddings import EmbeddingProvider, SentenceTransformerEmbeddingService
from backend.services.retrieval import RetrievalService
from backend.services.vector_store import SQLiteVectorStore
from backend.utils.config import get_settings


class KnowledgeBaseService:
    def __init__(
        self,
        knowledge_base_dir: str | Path,
        vector_store_dir: str | Path,
        embedding_model: str,
        top_k: int,
        min_score: float,
        ingestion: DocumentIngestionService | None = None,
        chunking: ChunkingService | None = None,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        self._ingestion = ingestion or DocumentIngestionService()
        self._chunking = chunking or ChunkingService()
        self._vector_store = SQLiteVectorStore(vector_store_dir)
        self._embeddings = embeddings or SentenceTransformerEmbeddingService(embedding_model)
        self._retrieval = RetrievalService(self._embeddings, self._vector_store, top_k, min_score)

    def ingest_file(self, path: str | Path) -> KnowledgeBaseDocument:
        document_path = Path(path)
        if not document_path.is_absolute():
            # Only prepend knowledge_base_dir if the path isn't already inside it
            try:
                document_path.relative_to(self.knowledge_base_dir)
            except ValueError:
                document_path = self.knowledge_base_dir / document_path
        document = self._ingestion.extract(document_path)
        chunks = self._chunking.create_chunks(document)
        if self._vector_store.has_document(document.document_hash):
            return KnowledgeBaseDocument(
                document_name=document.document_name, document_type=document.document_type,
                source_path=document.source_path, document_hash=document.document_hash,
                chunk_count=0, ingested_at=datetime.now(timezone.utc),
            )
        embeddings = self._embeddings.embed([chunk.text for chunk in chunks])
        if not chunks:
            raise ValueError("Knowledge-base document produced no text chunks.")
        ingested_at = datetime.now(timezone.utc)
        self._vector_store.add_document(chunks[0], chunks, embeddings, ingested_at.isoformat())
        return KnowledgeBaseDocument(
            document_name=document.document_name, document_type=document.document_type,
            source_path=document.source_path, document_hash=document.document_hash,
            chunk_count=len(chunks), ingested_at=ingested_at,
        )

    def ingest_directory(self) -> list[KnowledgeBaseDocument]:
        documents: list[KnowledgeBaseDocument] = []
        for path in sorted(self.knowledge_base_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".pdf", ".docx"}:
                documents.append(self.ingest_file(path))
        return documents

    def search(self, query: str) -> dict[str, Any]:
        return self._retrieval.search(query)


_settings = get_settings()
knowledge_base_service = KnowledgeBaseService(
    knowledge_base_dir=_settings.knowledge_base_dir,
    vector_store_dir=_settings.vector_store_dir,
    embedding_model=_settings.embedding_model,
    top_k=_settings.retrieval_top_k,
    min_score=_settings.retrieval_min_score,
)