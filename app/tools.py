# app/tools.py
import json
from pathlib import Path
from typing import Any
import chromadb
from sentence_transformers import SentenceTransformer
from tool_security import enforce_least_autonomy

# Resolve project root dynamically
PROJECT_ROOT = Path(__file__).resolve().parent
if PROJECT_ROOT.name in ["app", "tools"]:
    PROJECT_ROOT = PROJECT_ROOT.parent

DATA_FILE = PROJECT_ROOT / "data" / "loans.json"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

_client = None
_model = None
_collection = None

def get_rag_resources():
    global _client, _model, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _collection = _client.get_collection("cred_kb_sentence_based")
    return _collection, _model

def rag_policy_search(query: Any = "") -> str:
    """Searches the Cred policy knowledge base for rules, fees, KYC, EMIs, and terms."""
    if isinstance(query, dict):
        query = query.get("query", str(query))
    elif isinstance(query, str) and query.strip().startswith("{"):
        try:
            query = json.loads(query).get("query", query)
        except Exception:
            pass

    col, model = get_rag_resources()
    embedding = model.encode([str(query)]).tolist()
    results = col.query(query_embeddings=embedding, n_results=3)
    
    top_distance = results["distances"][0][0]
    top_similarity = 1.0 - top_distance
    
    if top_similarity < 0.40:
        return "I don't know based on the provided policy documents."
    
    chunks = results["documents"][0]
    return " ".join(chunks)

@enforce_least_autonomy(allowed_agent_role="LookupAgent")
def check_loan_application_status(record_id: Any = "") -> str:
    """Looks up a loan application by its record_id (e.g. CRED-LN-001) in Cred's dataset."""
    if isinstance(record_id, dict):
        record_id = record_id.get("record_id", str(record_id))
    elif isinstance(record_id, str) and record_id.strip().startswith("{"):
        try:
            record_id = json.loads(record_id).get("record_id", record_id)
        except Exception:
            pass

    if not DATA_FILE.exists():
        return json.dumps({"error": f"loans.json not found at {DATA_FILE}"})
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        loans = json.load(f)
        
    rec_id_clean = str(record_id).strip().upper()
    match = next((l for l in loans if l["record_id"].upper() == rec_id_clean), None)
    
    if not match:
        return json.dumps({"error": f"Application {record_id} not found."})
        
    fraud_weight = 1.0 if match["flagged_for_fraud_review"] else 0.0
    recency_weight = match["days_since_created"] / 30.0
    escalation_score = round((0.6 * fraud_weight) + (0.4 * recency_weight), 2)
    requires_escalation = escalation_score >= 0.70
    
    payload = {
        "record_id": match["record_id"],
        "category": match["category"],
        "status": match["status"],
        "loan_amount_inr": match["loan_amount_inr"],
        "days_since_created": match["days_since_created"],
        "flagged_for_fraud_review": match["flagged_for_fraud_review"],
        "escalation_score": escalation_score,
        "requires_escalation": requires_escalation
    }
    return json.dumps(payload)