from backend.schemas.rag import DocumentChunk
from backend.services.document_ingestion import ExtractedDocument
from uuid import uuid4


class ChunkingService:
    def __init__(self, chunk_size: int = 1200, overlap: int = 200) -> None:
        if overlap >= chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size.")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def create_chunks(self, document: ExtractedDocument) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_index = 0
        for page in document.pages:
            text = page["text"].strip()
            if not text:
                continue
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(DocumentChunk(
                        id=uuid4(),
                        document_hash=document.document_hash,
                        document_name=document.document_name,
                        document_type=document.document_type,
                        source_path=document.source_path,
                        text=chunk_text,
                        page_number=page.get("page_number"),
                        section=page.get("section"),
                        chunk_index=chunk_index,
                        metadata={"page_number": page.get("page_number"), "section": page.get("section")},
                    ))
                    chunk_index += 1
                if end == len(text):
                    break
                start = end - self.overlap
        return chunks


chunking_service = ChunkingService()