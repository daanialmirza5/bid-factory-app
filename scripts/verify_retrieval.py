import sys
import os
import sqlite3
from pathlib import Path
import json

# Add root directory to python path for imports to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.knowledge_base import KnowledgeBaseService
from backend.utils.config import get_settings

def print_separator():
    print("=" * 80)

def main():
    db_path = Path("data/vector_store/knowledge_base.sqlite3").resolve()
    print(f"Verifying SQLite DB at {db_path}...")
    
    if not db_path.exists():
        print("Database file does not exist!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    
    print(f"Documents in DB: {doc_count}")
    print(f"Chunks in DB: {chunk_count}")
    print_separator()

    settings = get_settings()
    kb_dir = Path("data/knowledge_base").resolve()
    vs_dir = Path("data/vector_store").resolve()
    
    service = KnowledgeBaseService(
        knowledge_base_dir=kb_dir,
        vector_store_dir=vs_dir,
        embedding_model=settings.embedding_model,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
    )

    test_queries = [
        "What availability does the company guarantee?",
        "Does the company provide 24/7 support?",
        "What cloud platforms does the company support?",
        "What AI and machine learning capabilities does the company have?",
        "What security certifications does the company have?",
        "What previous projects has the company completed?",
    ]

    for q in test_queries:
        print(f"QUERY: {q}")
        response = service.search(q)
        results = response.get("results", [])
        if not results:
            print("No results found.")
        
        for i, res in enumerate(results):
            print(f"  Result {i+1}:")
            print(f"    Document: {res.document_name}")
            print(f"    Section: {res.section}")
            print(f"    Page: {res.page_number}")
            print(f"    Score: {res.similarity_score:.4f}")
            print(f"    Metadata: {json.dumps(res.metadata)}")
            print(f"    Evidence: {res.retrieved_text.strip()}")
        print_separator()

if __name__ == "__main__":
    main()
