import sys
import os
from pathlib import Path

# Add root directory to python path for imports to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.knowledge_base import knowledge_base_service, KnowledgeBaseService

def main():
    print("Ingesting knowledge base documents...")
    # Because of a bug in ingest_file with relative iterators, we need to ensure knowledge_base_dir is absolute
    kb_dir = Path("data/knowledge_base").resolve()
    vs_dir = Path("data/vector_store").resolve()
    
    # Let's bypass the default initialized service and create our own with absolute paths
    from backend.utils.config import get_settings
    
    settings = get_settings()
    service = KnowledgeBaseService(
        knowledge_base_dir=kb_dir,
        vector_store_dir=vs_dir,
        embedding_model=settings.embedding_model,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )
    
    docs = service.ingest_directory()
    print(f"Ingested {len(docs)} documents.")
    total_chunks = sum(doc.chunk_count for doc in docs)
    print(f"Total chunks inserted: {total_chunks}")

if __name__ == "__main__":
    main()
