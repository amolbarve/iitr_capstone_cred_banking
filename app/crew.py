# app/crew.py
import json
import re
from tools import check_loan_application_status, rag_policy_search
from guardrails import GuardrailsManager
from memory import session_manager
from autogen_review import AutoGenReviewStage

def run_crew_with_session(user_query: str, session_id: str = "default_session") -> dict:
    # 1. PII Redaction Guardrail
    sanitized_query = GuardrailsManager.mask_input_pii(user_query)
    session_manager.add_user_message(session_id, sanitized_query)

    # 2. Retrieve multi-turn history
    prior_history = session_manager.get_formatted_history(session_id)
    target_text = f"History:\n{prior_history}\n\nCurrent Query: {sanitized_query}" if prior_history else sanitized_query

    draft_answer = ""
    record_id = None
    success = True
    escalation_score = None
    requires_escalation = False

    # 3. Tool execution / Crew draft generation
    loan_match = re.search(r"CRED-LN-\d+", target_text, re.IGNORECASE)
    if loan_match:
        record_id = loan_match.group(0).upper()
        tool_output_str = check_loan_application_status(record_id)
        try:
            tool_data = json.loads(tool_output_str)
        except Exception:
            tool_data = {}

        if "error" in tool_data:
            success = False
            draft_answer = f"Application {record_id} not found in Cred's records."
        else:
            draft_answer = (
                f"Application {record_id} is currently '{tool_data.get('status', 'Unknown')}' "
                f"with a loan amount of ₹{tool_data.get('loan_amount_inr', 0):,}."
            )
            escalation_score = tool_data.get("escalation_score")
            requires_escalation = tool_data.get("requires_escalation")
    elif any(k in target_text.lower() for k in ["kyc", "emi", "fee", "penalty", "interest", "score", "closure", "joint", "nri", "policy", "nach"]):
        tool_output_str = rag_policy_search(target_text)
        draft_answer = f"Based on Cred policy guidelines: {tool_output_str}"
    else:
        draft_answer = "According to Cred's operational guidelines, your request has been recorded and reviewed."

    # 4. Groundedness validation
    is_grounded = GuardrailsManager.validate_output_groundedness(draft_answer, target_text)

    # 5. Task 14: AutoGen Review Stage (max_turns=2)
    review_output = AutoGenReviewStage.review_and_refine(
        query=user_query,
        draft_answer=draft_answer,
        retrieved_context=tool_output_str if 'tool_output_str' in locals() else "",
        max_turns=2
    )
    final_answer = review_output["reviewed_answer"]

    # 6. Save final audited turn to session memory
    session_manager.add_ai_message(session_id, final_answer)

    return {
        "success": success and is_grounded,
        "answer": final_answer,
        "record_id": record_id,
        "escalation_score": escalation_score,
        "requires_escalation": requires_escalation,
        "metadata": {
            "source": "loans_lookup" if record_id else "rag_kb",
            "guardrail_passed": is_grounded,
            "pii_masked": (user_query != sanitized_query),
            "autogen_review": review_output["autogen_metadata"]
        }
    }