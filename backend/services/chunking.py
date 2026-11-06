from uuid import uuid4

from backend.schemas.rag import DocumentChunk
from backend.services.document_ingestion import ExtractedDocument


class ChunkingService:
    """Split documents along paragraph boundaries into section-sized chunks.

    Chunks stay small so a one-sentence requirement is compared with the passage
    that answers it, not with a whole document, which would dilute the similarity score.
    """

    def __init__(self, chunk_size: int = 240, overlap: int = 40) -> None:
        if overlap >= chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size.")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def create_chunks(self, document: ExtractedDocument) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in document.pages:
            for text in self._split(page["text"]):
                chunks.append(DocumentChunk(
                    id=uuid4(),
                    document_hash=document.document_hash,
                    document_name=document.document_name,
                    document_type=document.document_type,
                    source_path=document.source_path,
                    text=text,
                    page_number=page.get("page_number"),
                    section=page.get("section"),
                    chunk_index=len(chunks),
                    metadata={"page_number": page.get("page_number"), "section": page.get("section")},
                ))
        return chunks

    def _split(self, text: str) -> list[str]:
        pieces: list[str] = []
        current = ""
        for paragraph in (line.strip() for line in text.splitlines()):
            if not paragraph:
                continue
            candidate = f"{current}\n{paragraph}" if current else paragraph
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                pieces.append(current)
                current = ""
            if len(paragraph) <= self.chunk_size:
                current = paragraph
            else:
                pieces.extend(self._window(paragraph))
        if current:
            pieces.append(current)
        return pieces

    def _window(self, text: str) -> list[str]:
        windows: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                windows.append(piece)
            if end == len(text):
                break
            start = end - self.overlap
        return windows


chunking_service = ChunkingService()
