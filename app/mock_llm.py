# app/mock_llm.py
import re
import json
from crewai.llms.base_llm import BaseLLM
from tools import check_loan_application_status, rag_policy_search

class MockCrewLLM(BaseLLM):
    """
    Deterministic Mock LLM for local CrewAI testing under MOCK_LLM.
    Requires zero API keys and zero internet access.
    """
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        super().__init__(model=model_name)

    def call(self, messages, tools=None, **kwargs) -> str:
        prompt_text = ""
        for m in messages:
            if isinstance(m, dict):
                prompt_text += f" {m.get('content', '')}"
            else:
                prompt_text += f" {getattr(m, 'content', str(m))}"

        # 1. Isolate the current query so historical session turns don't hijack the lookup ID
        target_text = prompt_text
        if "Current User Query:" in prompt_text:
            target_text = prompt_text.split("Current User Query:")[-1]

        record_id = None
        loan_match = re.search(r"CRED-LN-\d+", target_text, re.IGNORECASE)
        
        if loan_match:
            record_id = loan_match.group(0).upper()
            tool_output_str = check_loan_application_status(record_id)
            
            try:
                tool_data = json.loads(tool_output_str)
            except Exception:
                tool_data = {}
            
            # Check if loans.json returned an error (record not found)
            if "error" in tool_data:
                response_payload = {
                    "success": False,
                    "answer": f"Application {record_id} not found in Cred's records.",
                    "record_id": record_id,
                    "escalation_score": None,
                    "requires_escalation": False,
                    "metadata": {"error": tool_data["error"], "source": "loans_lookup"}
                }
                return json.dumps(response_payload)

            answer = (
                f"Application {record_id} is currently '{tool_data.get('status', 'Unknown')}' "
                f"with a loan amount of ₹{tool_data.get('loan_amount_inr', 0):,}."
            )
            response_payload = {
                "success": True,
                "answer": answer,
                "record_id": record_id,
                "escalation_score": tool_data.get("escalation_score"),
                "requires_escalation": tool_data.get("requires_escalation"),
                "metadata": {"source": "loans_lookup", "validated": True}
            }
            return json.dumps(response_payload)

        # 2. Policy search fallback
        if any(k in target_text.lower() for k in ["kyc", "emi", "fee", "penalty", "interest", "score", "closure", "joint", "nri", "policy"]):
            tool_output_str = rag_policy_search(target_text)
            response_payload = {
                "success": True,
                "answer": f"Based on Cred policy guidelines: {tool_output_str}",
                "record_id": None,
                "escalation_score": None,
                "requires_escalation": False,
                "metadata": {"source": "rag_kb"}
            }
            return json.dumps(response_payload)

        # 3. Default fallback
        response_payload = {
            "success": True,
            "answer": "According to Cred's operational guidelines, your request has been reviewed.",
            "record_id": None,
            "escalation_score": None,
            "requires_escalation": False,
            "metadata": {"source": "general_guidelines"}
        }
        return json.dumps(response_payload)

    def supports_function_calling(self) -> bool:
        return True