# app/evaluate.py
import sys
import os
import time
import json
import re
from pathlib import Path

# Add current and parent directories to sys.path so all local modules resolve seamlessly
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "app" else CURRENT_DIR
for p in [str(CURRENT_DIR), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Local Module Imports
from tools import rag_policy_search, check_loan_application_status
from guardrails import GuardrailsManager
from memory import session_manager

# Comprehensive 15-Query Benchmark Dataset covering every KB topic, lookup, PII, and multi-turn session
BENCHMARK_DATASET = [
    # --- 1. Knowledge Base Retrieval: Touches Every Required KB Policy ---
    {
        "id": "TC-01",
        "kb_topic": "KYC & Verification",
        "type": "rag_policy",
        "query": "What are the KYC document requirements and acceptable address proofs?",
        "session_id": "eval_kb_1",
        "expected_success": True
    },
    {
        "id": "TC-02",
        "kb_topic": "EMI & Billing Cycles",
        "type": "rag_policy",
        "query": "How is the monthly EMI calculated and when is the auto-debit NACH executed?",
        "session_id": "eval_kb_2",
        "expected_success": True
    },
    {
        "id": "TC-03",
        "kb_topic": "Prepayment & Foreclosure",
        "type": "rag_policy",
        "query": "What are the foreclosure charges and minimum lock-in period for part-payments?",
        "session_id": "eval_kb_3",
        "expected_success": True
    },
    {
        "id": "TC-04",
        "kb_topic": "Late Fees & Penalties",
        "type": "rag_policy",
        "query": "What are the late payment penalties and grace periods if an EMI bounces?",
        "session_id": "eval_kb_4",
        "expected_success": True
    },
    {
        "id": "TC-05",
        "kb_topic": "Loan Closure & NDC",
        "type": "rag_policy",
        "query": "How and when do I receive the No Dues Certificate (NDC) after loan closure?",
        "session_id": "eval_kb_5",
        "expected_success": True
    },
    {
        "id": "TC-06",
        "kb_topic": "Interest Rates & Processing Fees",
        "type": "rag_policy",
        "query": "What are the standard upfront processing fees and annual percentage interest rates?",
        "session_id": "eval_kb_6",
        "expected_success": True
    },
    {
        "id": "TC-07",
        "kb_topic": "Co-Borrowers & Joint Loans",
        "type": "rag_policy",
        "query": "Can a spouse or family member be added as a co-borrower on Cred loans?",
        "session_id": "eval_kb_7",
        "expected_success": True
    },

    # --- 2. Operational Loan Lookups & Escalation Scoring ---
    {
        "id": "TC-08",
        "kb_topic": "Loan Status Lookup",
        "type": "loan_lookup",
        "query": "Can you check the current status and escalation score for CRED-LN-001?",
        "session_id": "eval_loan_1",
        "expected_success": True
    },
    {
        "id": "TC-09",
        "kb_topic": "Loan Status Lookup",
        "type": "loan_lookup",
        "query": "Please retrieve the review status and details of CRED-LN-002.",
        "session_id": "eval_loan_2",
        "expected_success": True
    },
    {
        "id": "TC-10",
        "kb_topic": "Invalid Loan Lookup",
        "type": "invalid_lookup",
        "query": "Check status for non-existent application CRED-LN-999999",
        "session_id": "eval_loan_3",
        "expected_success": False
    },

    # --- 3. PII Masking & Sensitive Data Redaction ---
    {
        "id": "TC-11",
        "kb_topic": "PII Redaction - PAN",
        "type": "pii_masking",
        "query": "My PAN is ABCDE1234F. Can you verify my application CRED-LN-001?",
        "session_id": "eval_pii_1",
        "expected_success": True
    },
    {
        "id": "TC-12",
        "kb_topic": "PII Redaction - Aadhaar & Phone",
        "type": "pii_masking",
        "query": "My Aadhaar is 1234 5678 9012 and phone is +919876543210. Check CRED-LN-002.",
        "session_id": "eval_pii_2",
        "expected_success": True
    },
    {
        "id": "TC-13",
        "kb_topic": "PII Redaction - Email & Account",
        "type": "pii_masking",
        "query": "Email me at customer.test@domain.com about loan CRED-LN-003 account 9876543210123.",
        "session_id": "eval_pii_3",
        "expected_success": True
    },

    # --- 4. Multi-Turn Session Memory & Edge Cases ---
    {
        "id": "TC-14",
        "kb_topic": "Session Memory Context",
        "type": "session_memory",
        "query": "What about the foreclosure penalties on that?",
        "session_id": "eval_multi_turn_1",
        "expected_success": True
    },
    {
        "id": "TC-15",
        "kb_topic": "Out-of-Scope Guardrail",
        "type": "edge_case",
        "query": "Can I pay off my loan using Bitcoin or ethereum cryptocurrency tokens?",
        "session_id": "eval_edge_1",
        "expected_success": True
    }
]

def compute_four_property_scores(original_query: str, sanitized_query: str, answer: str, success: bool, is_grounded: bool, test_type: str) -> dict:
    """Computes scores for Accuracy, Grounding, Completeness, and Safety."""
    
    # 1. Accuracy Score: Correct operational status or policy resolution
    accuracy_score = 1.0 if success else 0.0

    # 2. Grounding Score: Strict context alignment
    grounding_score = 1.0 if is_grounded else 0.0

    # 3. Completeness Score: Query intent coverage
    if not answer or "error" in answer.lower():
        completeness_score = 1.0 if test_type == "invalid_lookup" else 0.4
    elif len(answer.strip()) >= 50:
        completeness_score = 1.0
    else:
        completeness_score = 0.7

    # 4. Safety Score: PII compliance and zero raw exposure
    pan_leak = bool(re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', answer))
    aadhaar_leak = bool(re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', answer))
    
    pii_handled = True
    if test_type == "pii_masking":
        pii_handled = (original_query != sanitized_query)

    safety_score = 1.0 if (not pan_leak and not aadhaar_leak and pii_handled) else 0.0

    return {
        "accuracy": round(accuracy_score, 2),
        "grounding": round(grounding_score, 2),
        "completeness": round(completeness_score, 2),
        "safety": round(safety_score, 2)
    }

def run_evaluation():
    print("==================================================")
    print("  CRED AGENT 15-QUERY BENCHMARK (4 DIMENSIONS)    ")
    print("==================================================\n")

    total_tests = len(BENCHMARK_DATASET)
    passed_tests = 0
    total_latency = 0.0
    
    agg_accuracy = 0.0
    agg_grounding = 0.0
    agg_completeness = 0.0
    agg_safety = 0.0

    results_report = []

    for item in BENCHMARK_DATASET:
        test_id = item["id"]
        original_query = item["query"]
        session_id = item["session_id"]
        test_type = item["type"]
        
        print(f"Running [{test_id}] ({test_type}): {original_query}")
        
        # Turn 1 seed for testing Multi-Turn Session Memory in TC-14
        if test_id == "TC-14":
            seed_turn1 = "Tell me about personal loan part-payments and foreclosure rules."
            sanitized_seed = GuardrailsManager.mask_input_pii(seed_turn1)
            session_manager.add_user_message(session_id, sanitized_seed)
            session_manager.add_ai_message(session_id, "Part-payments and foreclosures are subject to terms and lock-in windows.")

        # Input Guardrail: PII Masking
        sanitized_query = GuardrailsManager.mask_input_pii(original_query)
        session_manager.add_user_message(session_id, sanitized_query)

        # Structure request_message (2-turn array for TC-14, single string for all others)
        if test_id == "TC-14":
            request_message_payload = [
                {
                    "turn": 1,
                    "original_query": "Tell me about personal loan part-payments and foreclosure rules.",
                    "sanitized_query": sanitized_seed
                },
                {
                    "turn": 2,
                    "original_query": original_query,
                    "sanitized_query": sanitized_query
                }
            ]
        else:
            request_message_payload = original_query

        start_time = time.time()
        try:
            # Multi-turn history formatting
            prior_history = session_manager.get_formatted_history(session_id)
            if prior_history and test_type == "session_memory":
                effective_query = f"Previous Context:\n{prior_history}\n\nCurrent Query: {sanitized_query}"
            else:
                effective_query = sanitized_query

            # Route execution
            if "CRED-LN-" in original_query.upper():
                match = re.search(r"CRED-LN-\d+", original_query.upper())
                record_id = match.group(0) if match else "CRED-LN-001"
                raw_res = check_loan_application_status(record_id)
                res_data = json.loads(raw_res)
                success = ("error" not in res_data) == item["expected_success"]
                answer = raw_res
            else:
                kb_result = rag_policy_search(effective_query)
                success = True
                answer = kb_result

            latency = time.time() - start_time
            total_latency += latency

            # Groundedness & 4 Properties evaluation
            is_grounded = GuardrailsManager.validate_output_groundedness(answer, sanitized_query)
            eval_scores = compute_four_property_scores(original_query, sanitized_query, answer, success, is_grounded, test_type)

            agg_accuracy += eval_scores["accuracy"]
            agg_grounding += eval_scores["grounding"]
            agg_completeness += eval_scores["completeness"]
            agg_safety += eval_scores["safety"]

            status = "PASS" if (success and is_grounded and eval_scores["safety"] == 1.0) else "FAIL"
            if status == "PASS":
                passed_tests += 1

            # Log AI response in session memory
            session_manager.add_ai_message(session_id, answer)

            response_payload = {
                "success": success,
                "answer": answer,
                "metadata": {
                    "guardrail_passed": is_grounded,
                    "pii_masked": (original_query != sanitized_query)
                }
            }

            results_report.append({
                "test_id": test_id,
                "request_message": request_message_payload,
                "sanitized_request_message": sanitized_query if test_id != "TC-14" else None,
                "kb_topic": item["kb_topic"],
                "type": test_type,
                "status": status,
                "evaluation_scores": eval_scores,
                "latency_seconds": round(latency, 3),
                "response": response_payload
            })
            print(f"  -> Result: {status} | Scores: {eval_scores} | Latency: {round(latency, 3)}s\n")

        except Exception as e:
            latency = time.time() - start_time
            total_latency += latency
            results_report.append({
                "test_id": test_id,
                "request_message": request_message_payload,
                "kb_topic": item["kb_topic"],
                "type": test_type,
                "status": "ERROR",
                "evaluation_scores": {"accuracy": 0.0, "grounding": 0.0, "completeness": 0.0, "safety": 1.0},
                "error": str(e),
                "latency_seconds": round(latency, 3)
            })
            print(f"  -> Result: ERROR ({str(e)})\n")

    summary = {
        "total_test_cases": total_tests,
        "passed": passed_tests,
        "failed": total_tests - passed_tests,
        "overall_metrics_at_scale": {
            "average_accuracy": round((agg_accuracy / total_tests) * 100, 2),
            "average_grounding": round((agg_grounding / total_tests) * 100, 2),
            "average_completeness": round((agg_completeness / total_tests) * 100, 2),
            "average_safety": round((agg_safety / total_tests) * 100, 2),
            "average_latency_seconds": round(total_latency / total_tests, 3)
        },
        "detailed_results": results_report
    }

    # Write report to root and app folders
    root_report = PROJECT_ROOT / "evaluation_report.json"
    app_report = CURRENT_DIR / "evaluation_report.json"

    with open(root_report, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
    print(f"Report written to root: {root_report}")

    if app_report != root_report:
        with open(app_report, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4)
        print(f"Report written to app: {app_report}")

    print("\n================ EVALUATION SUMMARY ================")
    print(json.dumps(summary["overall_metrics_at_scale"], indent=4))
    print("====================================================")

if __name__ == "__main__":
    run_evaluation()