import sys
import os
from pathlib import Path
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.document_ingestion import document_ingestion_service
from backend.services.chunking import chunking_service
from backend.services.knowledge_base import knowledge_base_service, get_settings

def print_separator():
    print("=" * 80)

def main():
    kb_dir = Path("data/knowledge_base").resolve()
    
    print("--- CHUNKING INSPECTION ---")
    for path in sorted(kb_dir.rglob("*.docx")):
        doc = document_ingestion_service.extract(path)
        chunks = chunking_service.create_chunks(doc)
        
        doc_len = sum(len(page["text"]) for page in doc.pages)
        print(f"File: {path.name}")
        print(f"  Length: {doc_len} chars")
        # Assuming size=1200, overlap=200
        expected = 1
        if doc_len > 1200:
            expected = 1 + (doc_len - 1200) // (1200 - 200)
            if (doc_len - 1200) % 1000 != 0:
                expected += 1
        print(f"  Expected chunks (approx): {expected}")
        print(f"  Produced chunks: {len(chunks)}")
        
        sections = [c.section for c in chunks]
        print(f"  Section metadata preserved: {sections}")
        print_separator()

    print("--- RETRIEVAL TEST ---")
    settings = get_settings()
    vs_dir = Path("data/vector_store").resolve()
    # using service directly so we can query
    test_queries = [
        "99.9% availability",
        "support hours",
        "AWS Azure GCP",
        "ISO 27001",
        "SOC 2",
        "AI/ML capabilities",
        "previous projects",
        "data protection",
        "irrelevant random generic query about nothing"
    ]
    
    for q in test_queries:
        print(f"QUERY: {q}")
        res = knowledge_base_service.search(q).get("results", [])
        if not res:
            print("  No results.")
            
        for r in res:
            semantic = r.metadata.get("hybrid_scores", {}).get("semantic", 0)
            lexical = r.metadata.get("hybrid_scores", {}).get("lexical", 0)
            print(f"  -> Doc: {r.document_name} | Section: {r.section}")
            print(f"     Semantic: {semantic:.4f} | Lexical: {lexical:.4f} | Combined: {r.similarity_score:.4f}")
            print(f"     Evidence preview: {r.retrieved_text[:100].strip()}...")
        print_separator()
        
if __name__ == "__main__":
    main()
