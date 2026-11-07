# tools/status_tool.py
import json
from pathlib import Path
from langchain.tools import tool

# Resolve path to dataset in project root/data/loans.json
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name in ["app", "tools"] else CURRENT_DIR
DATA_FILE = PROJECT_ROOT / "data" / "loans.json"

def load_loans():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found at {DATA_FILE}. Run dataset.py first.")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@tool("check_loan_application_status")
def check_loan_application_status(record_id: str) -> dict:
    """
    Looks up a loan application by its record_id from the Cred dataset.
    Returns status, loan amount in INR, and a designed escalation score.
    """
    loans = load_loans()
    record_id_clean = record_id.strip().upper()
    
    # Find matching record
    record = next((l for l in loans if l["record_id"].upper() == record_id_clean), None)
    
    if not record:
        return {
            "error": f"Loan application ID '{record_id}' not found in the database."
        }
    
    # Compute Escalation Score
    # Formula: 0.6 * fraud_flag + 0.4 * (days_since_created / 30)
    fraud_weight = 1.0 if record["flagged_for_fraud_review"] else 0.0
    recency_weight = record["days_since_created"] / 30.0
    
    escalation_score = round((0.6 * fraud_weight) + (0.4 * recency_weight), 2)
    escalation_threshold = 0.70
    requires_escalation = escalation_score >= escalation_threshold
    
    return {
        "record_id": record["record_id"],
        "category": record["category"],
        "status": record["status"],
        "loan_amount_inr": record["loan_amount_inr"],
        "days_since_created": record["days_since_created"],
        "flagged_for_fraud_review": record["flagged_for_fraud_review"],
        "escalation_score": escalation_score,
        "requires_escalation": requires_escalation,
        "escalation_justification": f"Score {escalation_score} evaluated against threshold {escalation_threshold} (Formula: 0.6*fraud + 0.4*(days/30))."
    }

if __name__ == "__main__":
    # Quick local test of the tool
    loans = load_loans()
    sample_id = loans[0]["record_id"]
    print(f"Testing status lookup for: {sample_id}")
    print(json.dumps(check_loan_application_status(sample_id), indent=4))