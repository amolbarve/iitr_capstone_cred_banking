# evaluate_chunking.py
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

# 1. Setup client and model
PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name == "app":
    PROJECT_ROOT = PROJECT_ROOT.parent

chroma_client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "chroma_db"))
model = SentenceTransformer("all-MiniLM-L6-v2")

fixed_col = chroma_client.get_collection("cred_kb_fixed_size")
sent_col = chroma_client.get_collection("cred_kb_sentence_based")

# 2. Define 5 test queries and their known ground-truth parent document IDs
TEST_QUERIES = [
    {
        "query": "What are the KYC documents required for credit approval?",
        "relevant_docs": ["kb_04"]
    },
    {
        "query": "Can I close my loan early without prepayment penalty?",
        "relevant_docs": ["kb_08"]
    },
    {
        "query": "What factors impact my credit score calculation?",
        "relevant_docs": ["kb_10"]
    },
    {
        "query": "How are EMIs calculated on loans?",
        "relevant_docs": ["kb_02"]
    },
    {
        "query": "What are the rules for joint accounts?",
        "relevant_docs": ["kb_11"]
    }
]

def evaluate_collection(collection, strategy_name, top_k=3):
    print(f"\n================ EVALUATING STRATEGY: {strategy_name.upper()} ================")
    total_precision = 0.0
    total_recall = 0.0
    
    for idx, item in enumerate(TEST_QUERIES, 1):
        query = item["query"]
        ground_truth = set(item["relevant_docs"])
        
        # Retrieve chunks
        embedding = model.encode([query]).tolist()
        results = collection.query(query_embeddings=embedding, n_results=top_k)
        
        # Map back to parent documents and deduplicate
        metadatas = results["metadatas"][0]
        retrieved_docs = set(m["doc_id"] for m in metadatas)
        
        # Calculate Precision and Recall
        # Precision = |Retrieved ∩ Relevant| / |Retrieved|
        # Recall = |Retrieved ∩ Relevant| / |Relevant|
        intersection = retrieved_docs.intersection(ground_truth)
        
        precision = len(intersection) / len(retrieved_docs) if retrieved_docs else 0.0
        recall = len(intersection) / len(ground_truth) if ground_truth else 0.0
        
        total_precision += precision
        total_recall += recall
        
        print(f"Query {idx}: \"{query}\"")
        print(f"  • Retrieved Parent Docs: {list(retrieved_docs)}")
        print(f"  • Ground Truth Docs:     {list(ground_truth)}")
        print(f"  • Arithmetic:            Intersection={len(intersection)}, Retrieved={len(retrieved_docs)}, Relevant={len(ground_truth)}")
        print(f"  • Precision:             {precision:.2f} | Recall: {recall:.2f}\n")
        
    avg_precision = total_precision / len(TEST_QUERIES)
    avg_recall = total_recall / len(TEST_QUERIES)
    print(f"[{strategy_name.upper()} SUMMARY] Average Precision: {avg_precision:.2f} | Average Recall: {avg_recall:.2f}")
    return avg_precision, avg_recall

if __name__ == "__main__":
    fixed_p, fixed_r = evaluate_collection(fixed_col, "Fixed-Size with Overlap", top_k=3)
    sent_p, sent_r = evaluate_collection(sent_col, "Sentence-Based", top_k=3)
    
    print("\n================ FINAL RECOMMENDATION ================")
    print(f"Fixed-Size Strategy -> Precision: {fixed_p:.2f}, Recall: {fixed_r:.2f}")
    print(f"Sentence-Based Strategy -> Precision: {sent_p:.2f}, Recall: {sent_r:.2f}")