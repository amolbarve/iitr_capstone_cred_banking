# test_task6.py
import json
from pathlib import Path

# Import your status tool function (adjust import path based on your file structure)
from status_tool import check_loan_application_status, load_loans

def run_tests():
    print("=================== TESTING TASK 6 ===================")
    
    # 1. Load dataset to get valid IDs for testing
    loans = load_loans()
    print(f"Total records available in dataset: {len(loans)}")
    
    # Pick a regular application and a flagged application if available
    sample_normal = next((l for l in loans if not l["flagged_for_fraud_review"]), loans[0])
    sample_flagged = next((l for l in loans if l["flagged_for_fraud_review"]), loans[1])
    
    test_ids = [
        sample_normal["record_id"],
        sample_flagged["record_id"],
        "CRED-LN-999"  # Invalid ID test case
    ]
    
    for record_id in test_ids:
        print(f"\n--- Testing Lookup for ID: {record_id} ---")
        result = check_loan_application_status.invoke({"record_id": record_id})
        print(json.dumps(result, indent=4))
        
        if "error" not in result:
            # Assert expected keys exist as required by the capstone brief
            assert "status" in result
            assert "loan_amount_inr" in result
            assert "escalation_score" in result
            assert "requires_escalation" in result
            print(f"✅ Success: Escalation Score = {result['escalation_score']} | Requires Escalation = {result['requires_escalation']}")
        else:
            print(f"✅ Handled invalid ID correctly: {result['error']}")

    print("\n=======================================================")
    print("Task 6 testing completed successfully!")

if __name__ == "__main__":
    run_tests()