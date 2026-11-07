# rag_core.py
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="./chroma_db")
model = SentenceTransformer("all-MiniLM-L6-v2")
collection = client.get_collection(name="cred_kb_sentence_based")

FALLBACK_RESPONSE = "I don't know based on the provided policy documents."
EMPIRICAL_THRESHOLD = 0.45  # Replace with your actual measured midpoint

def generate_grounded_answer(query_text: str, top_k: int = 3):
    embedding = model.encode([query_text]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=top_k)
    
    top_distance = results["distances"][0][0]
    top_similarity = 1.0 - top_distance
    
    # Check if retrieval confidence falls below the calibrated threshold
    if top_similarity < EMPIRICAL_THRESHOLD:
        return {
            "query": query_text,
            "answer": FALLBACK_RESPONSE,
            "top_similarity": top_similarity,
            "grounded": False,
            "sources": []
        }
    
    # Grounded response using ONLY retrieved context chunks
    retrieved_chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    
    context_text = " ".join(retrieved_chunks)
    source_docs = list(set(m["doc_id"] for m in metadatas))
    
    answer = f"According to Cred policy: {context_text}"
    
    return {
        "query": query_text,
        "answer": answer,
        "top_similarity": top_similarity,
        "grounded": True,
        "sources": source_docs
    }

if __name__ == "__main__":
    # Demonstrate on 5 in-scope queries + 1 out-of-scope fallback query
    test_queries = [
        "What are the KYC document requirements?",
        "How are EMIs calculated?",
        "What are the credit-card fee structures?",
        "How does the fraud-dispute resolution process work?",
        "What are the rules for joint accounts?",
        "Can you give me a recipe for chocolate chip cookies?"  # Out-of-scope
    ]
    
    for q in test_queries:
        res = generate_grounded_answer(q)
        print(f"Query: {res['query']}")
        print(f"Similarity: {res['top_similarity']:.4f} | Grounded: {res['grounded']}")
        print(f"Answer: {res['answer']}\n" + "-"*50)