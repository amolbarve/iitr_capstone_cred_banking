# app/test_master_capstone.py
import json
import time
from guardrails import GuardrailsManager
from tools import check_loan_application_status
from tool_security import UnauthorizedToolAccessError
from budget_guard import RuntimeBudgetGuard, BudgetExceededError
from memory import session_manager
from autogen_review import AutoGenReviewStage, FinalEditorVerdict
from cache_manager import ResponseCacheManager
from governance import AIGovernanceManager

def run_master_capstone_test_suite():
    print("==================================================================")
    print("       CRED DOMAIN SUPPORT AGENT: MASTER CAPSTONE TEST SUITE       ")
    print("==================================================================")

    results = {}

    # --- REQUIREMENT 1: Input PII Masking (Layer 1) ---
    print("\n[Test 1/7] Testing Input PII Redaction...")
    raw_input_query = "My PAN is ABCDE1234F and phone is +919876543210. Check my loan."
    masked_query = GuardrailsManager.mask_input_pii(raw_input_query)
    pii_masked_success = ("ABCDE1234F" not in masked_query) and ("XXXX" in masked_query or "*" in masked_query)
    results["pii_masking"] = pii_masked_success
    print(f"  -> Raw: {raw_input_query}")
    print(f"  -> Masked: {masked_query}")
    print(f"  -> Status: {'PASS' if pii_masked_success else 'FAIL'}")


    # --- REQUIREMENT 2: Principle of Least Autonomy (Tool Gating) ---
    print("\n[Test 2/7] Testing Least Autonomy Tool Restrictions...")
    try:
        # LookupAgent allowed
        check_loan_application_status("CRED-LN-001", agent_role="LookupAgent")
        # Unauthorized Agent should raise exception
        check_loan_application_status("CRED-LN-001", agent_role="PolicyRAGAgent")
        least_autonomy_passed = False
    except UnauthorizedToolAccessError:
        least_autonomy_passed = True
    except Exception:
        least_autonomy_passed = False
    results["least_autonomy"] = least_autonomy_passed
    print(f"  -> Status: {'PASS (Unauthorized access correctly blocked)' if least_autonomy_passed else 'FAIL'}")


    # --- REQUIREMENT 3: Runtime Layer Token & Cost Budget Cap (HTTP 429) ---
    print("\n[Test 3/7] Testing Runtime Budget Cap (800 tokens / $0.000200)...")
    normal_q = "What are the foreclosure charges?"
    oversized_q = "Explain policy. " + ("lorem ipsum " * 400)
    
    budget_passed = False
    try:
        RuntimeBudgetGuard.enforce_budget(normal_q) # Should pass
        RuntimeBudgetGuard.enforce_budget(oversized_q) # Should raise 429
    except BudgetExceededError:
        budget_passed = True # Correctly intercepted
    results["runtime_budget"] = budget_passed
    print(f"  -> Status: {'PASS (Oversized query intercepted with HTTP 429)' if budget_passed else 'FAIL'}")


    # --- REQUIREMENT 4: Multi-Turn Session Memory ---
    print("\n[Test 4/7] Testing Multi-Turn Session Memory...")
    session_id = "master_eval_session_01"
    session_manager.add_user_message(session_id, "User asked about CRED-LN-003")
    session_manager.add_ai_message(session_id, "Loan CRED-LN-003 is currently Under Review.")
    history = session_manager.get_formatted_history(session_id)
    memory_passed = "CRED-LN-003" in history
    results["session_memory"] = memory_passed
    print(f"  -> Retrieved History Length: {len(history)} chars")
    print(f"  -> Status: {'PASS' if memory_passed else 'FAIL'}")


    # --- REQUIREMENT 5: AutoGen Multi-Agent Review Stage (max_turns=2 & Pydantic) ---
    print("\n[Test 5/7] Testing AutoGen Review Stage (max_turns=2 & FinalEditorVerdict)...")
    test_draft = "Application CRED-LN-001 is In Review with an amount of ₹500,000."
    test_context = "Application CRED-LN-001 is In Review with an amount of ₹500,000."
    
    review_res = AutoGenReviewStage.review_and_refine(
        query="Check status of CRED-LN-001",
        draft_answer=test_draft,
        retrieved_context=test_context,
        max_turns=2
    )
    verdict = review_res["autogen_metadata"]["structured_verdict"]
    autogen_passed = (review_res["autogen_metadata"]["team_config"]["max_turns"] == 2) and isinstance(verdict, dict) and "approved" in verdict
    results["autogen_review"] = autogen_passed
    print(f"  -> Review Verdict Approved: {verdict.get('approved')}")
    print(f"  -> Status: {'PASS' if autogen_passed else 'FAIL'}")


    # --- REQUIREMENT 6: Four-Layer AI Governance Model & Audit Log ---
    print("\n[Test 6/7] Testing 4-Layer AI Governance Audit Pipeline...")
    def mock_executor(q, s):
        return {"success": True, "answer": "Verified Cred policy response.", "context": "Verified Cred policy response.", "record_id": None}

    governance_result = AIGovernanceManager.process_governed_request(
        user_query="What are the KYC address proof requirements?",
        session_id="gov_test_01",
        execution_callback=mock_executor
    )
    audit_logs = governance_result["metadata"]["governance_audit"]
    layers_ok = all([
        audit_logs["layers_passed"]["layer_1_input_guardrail"]["passed"],
        audit_logs["layers_passed"]["layer_2_runtime_budget_guardrail"]["passed"],
        audit_logs["layers_passed"]["layer_3_multi_agent_review"]["passed"],
        audit_logs["layers_passed"]["layer_4_telemetry_audit"]["passed"]
    ])
    results["governance_layers"] = layers_ok
    print(f"  -> All 4 Governance Layers Passed: {layers_ok}")
    print(f"  -> Status: {'PASS' if layers_ok else 'FAIL'}")


    # --- REQUIREMENT 7: Response Caching (Before/After Evidence) ---
    print("\n[Test 7/7] Testing Response Caching (Before/After Evidence)...")
    cache_query = "What is the late payment penalty fee?"
    cache_payload = {"success": True, "answer": "Late fee is 2% of overdue EMI amount."}
    
    # Before (Miss)
    assert ResponseCacheManager.get(cache_query) is None
    ResponseCacheManager.set(cache_query, cache_payload)
    
    # After (Hit)
    hit_res = ResponseCacheManager.get(cache_query)
    cache_passed = (hit_res is not None) and (hit_res["hit"] == True)
    results["response_caching"] = cache_passed
    print(f"  -> Cache Hit Verified: {cache_passed}")
    print(f"  -> Status: {'PASS' if cache_passed else 'FAIL'}")


    # --- FINAL SUMMARY REPORT ---
    print("\n==================================================================")
    print("                 MASTER CAPSTONE TEST SUMMARY                     ")
    print("==================================================================")
    all_passed = True
    for req, passed in results.items():
        status_label = "✅ PASS" if passed else "❌ FAIL"
        print(f"  * {req.replace('_', ' ').title():<30} : {status_label}")
        if not passed:
            all_passed = False
    print("==================================================================")
    if all_passed:
        print("  🎉 ALL CAPSTONE REQUIREMENTS SUCCESSFULLY VERIFIED & PASSED!    ")
    else:
        print("  ⚠️ SOME REQUIREMENTS FAILED. PLEASE CHECK LOGS ABOVE.            ")
    print("==================================================================")

if __name__ == "__main__":
    run_master_capstone_test_suite()