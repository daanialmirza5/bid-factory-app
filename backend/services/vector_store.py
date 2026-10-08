import json
import sqlite3
from pathlib import Path
from typing import Any
import numpy as np

from backend.schemas.rag import DocumentChunk, RetrievalResult


class VectorStoreError(RuntimeError):
    """Raised when the local vector store cannot read or write data."""


class SQLiteVectorStore:
    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)
        self._database_path = self._directory / "knowledge_base.sqlite3"
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("CREATE TABLE IF NOT EXISTS documents (document_hash TEXT PRIMARY KEY, document_name TEXT NOT NULL, document_type TEXT NOT NULL, source_path TEXT NOT NULL, ingested_at TEXT NOT NULL, chunk_count INTEGER NOT NULL)")
                connection.execute("CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, document_hash TEXT NOT NULL, document_name TEXT NOT NULL, document_type TEXT NOT NULL, source_path TEXT NOT NULL, text TEXT NOT NULL, page_number INTEGER, section TEXT, chunk_index INTEGER NOT NULL, metadata TEXT NOT NULL, embedding BLOB NOT NULL, FOREIGN KEY(document_hash) REFERENCES documents(document_hash))")
        except Exception as exc:
            raise VectorStoreError("Unable to initialize the knowledge-base vector store.") from exc

    def has_document(self, document_hash: str) -> bool:
        with self._connect() as connection:
            return connection.execute("SELECT 1 FROM documents WHERE document_hash = ?", (document_hash,)).fetchone() is not None

    def add_document(self, document: DocumentChunk, chunks: list[DocumentChunk], embeddings: list[list[float]], ingested_at: str) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunk and embedding counts do not match.")
        try:
            with self._connect() as connection:
                if self.has_document(document.document_hash):
                    return
                connection.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)", (document.document_hash, document.document_name, document.document_type, document.source_path, ingested_at, len(chunks)))
                connection.executemany(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(
                        str(chunk.id), chunk.document_hash, chunk.document_name, chunk.document_type,
                        chunk.source_path, chunk.text, chunk.page_number, chunk.section,
                        chunk.chunk_index, json.dumps(chunk.metadata), np.asarray(embedding, dtype=np.float32).tobytes(),
                    ) for chunk, embedding in zip(chunks, embeddings)],
                )
        except sqlite3.IntegrityError as exc:
            raise VectorStoreError("Unable to add document because the vector store rejected it.") from exc
        except Exception as exc:
            raise VectorStoreError("Unable to add document to the vector store.") from exc

    def search(self, query: str, query_embedding: list[float], top_k: int, min_score: float) -> list[RetrievalResult]:
        import re
        try:
            q_lower = query.lower()
            q_words_all = set(re.findall(r'\b\w+\b', q_lower))
            stop_words = {"the","a","an","and","or","is","are","of","to","in","for","with","must","provide","have","what","does",
                          "company","system","service","support","data","project","solution", "what's", "do", "we", "can", "how"}
            q_words = {w for w in q_words_all if w not in stop_words}
            
            embedding_np = np.asarray(query_embedding, dtype=np.float32)
            query_norm = np.linalg.norm(embedding_np)
            
            scored: list[tuple[float, RetrievalResult]] = []
            with self._connect() as connection:
                rows = connection.execute("SELECT document_name, document_type, source_path, text, page_number, section, metadata, embedding FROM chunks").fetchall()
            for row in rows:
                vector = np.frombuffer(row["embedding"], dtype=np.float32)
                semantic_score = 0.0
                if query_norm > 0:
                    denominator = query_norm * np.linalg.norm(vector)
                    semantic_score = float(np.dot(embedding_np, vector) / denominator) if denominator else 0.0
                
                lexical_score = 0.0
                if q_words_all:
                    t_lower = row["text"].lower()
                    # 1. Exact phrase match
                    if len(q_words_all) > 1 and q_lower in t_lower:
                        lexical_score += 0.5
                    
                    # 2. Term match (ignore stop words for scoring individual overlaps)
                    t_words = set(re.findall(r'\b\w+\b', t_lower))
                    if q_words:
                        matches = sum(1 for word in q_words if word in t_words)
                        lexical_score += 0.5 * (matches / len(q_words))
                    
                combined_score = (0.7 * semantic_score) + (0.3 * lexical_score)
                
                if combined_score >= min_score:
                    metadata: dict[str, Any] = json.loads(row["metadata"])
                    metadata.update({"document_type": row["document_type"]})
                    metadata["hybrid_scores"] = {
                        "semantic": round(semantic_score, 4),
                        "lexical": round(lexical_score, 4)
                    }
                    scored.append((combined_score, RetrievalResult(
                        document_name=row["document_name"], source_path=row["source_path"],
                        page_number=row["page_number"], section=row["section"],
                        retrieved_text=row["text"], similarity_score=combined_score, metadata=metadata,
                    )))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [result for _, result in scored[:top_k]]
        except Exception as exc:
            raise VectorStoreError("Unable to search the knowledge-base vector store.") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection