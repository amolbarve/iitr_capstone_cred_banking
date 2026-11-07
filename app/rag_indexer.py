# rag_indexer.py
import json
import re
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

# 1. Resolve paths dynamically relative to project root
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "app" else CURRENT_DIR

DATA_PATH = PROJECT_ROOT / "data" / "knowledge_base.json"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

def load_knowledge_base():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Knowledge base file not found at {DATA_PATH}. Please ensure knowledge_base.json is created.")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def chunk_fixed_size(text: str, chunk_size: int = 180, overlap: int = 40):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

def chunk_sentence_based(text: str):
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in raw_sentences if s.strip()]

def build_indices():
    print(f"Initializing persistent Chroma client at: {CHROMA_DIR}")
    # Explicit persistent client configuration
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Load free local embedding model
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Create or get collections
    fixed_col = chroma_client.get_or_create_collection(
        name="cred_kb_fixed_size",
        metadata={"hnsw:space": "cosine"}
    )
    sent_col = chroma_client.get_or_create_collection(
        name="cred_kb_sentence_based",
        metadata={"hnsw:space": "cosine"}
    )
    
    docs = load_knowledge_base()
    print(f"Loaded {len(docs)} documents from {DATA_PATH}")
    
    for doc in docs:
        doc_id = doc["doc_id"]
        content = doc["content"]
        topic = doc["topic"]
        
        # --- Strategy A: Fixed-Size Chunks ---
        fixed_chunks = chunk_fixed_size(content, chunk_size=180, overlap=40)
        if fixed_chunks:
            fixed_embeddings = model.encode(fixed_chunks).tolist()
            fixed_ids = [f"{doc_id}_fix_{i}" for i in range(len(fixed_chunks))]
            fixed_metas = [{"doc_id": doc_id, "topic": topic, "strategy": "fixed"} for _ in fixed_chunks]
            fixed_col.upsert(
                ids=fixed_ids,
                documents=fixed_chunks,
                embeddings=fixed_embeddings,
                metadatas=fixed_metas
            )
            
        # --- Strategy B: Sentence-Based Chunks ---
        sent_chunks = chunk_sentence_based(content)
        if sent_chunks:
            sent_embeddings = model.encode(sent_chunks).tolist()
            sent_ids = [f"{doc_id}_sent_{i}" for i in range(len(sent_chunks))]
            sent_metas = [{"doc_id": doc_id, "topic": topic, "strategy": "sentence"} for _ in sent_chunks]
            sent_col.upsert(
                ids=sent_ids,
                documents=sent_chunks,
                embeddings=sent_embeddings,
                metadatas=sent_metas
            )

    print("\n--- INDEXING COMPLETE ---")
    print(f"• Fixed-size collection count: {fixed_col.count()} chunks")
    print(f"• Sentence-based collection count: {sent_col.count()} chunks")
    print(f"Database successfully persisted to directory: {CHROMA_DIR}")

if __name__ == "__main__":
    build_indices()