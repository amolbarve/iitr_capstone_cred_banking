# app/governance.py
import time
from guardrails import GuardrailsManager
from autogen_review import AutoGenReviewStage
from budget_guard import RuntimeBudgetGuard, BudgetExceededError

class AIGovernanceManager:
    """
    Implements the 4-Layer AI-Governance Architecture:
      Layer 1: Input & Data Guardrails (PII Masking & Sanitization)
      Layer 2: Runtime & Execution Guardrails (Token/Cost Budget Caps, Tool Gating)
      Layer 3: Multi-Agent Review & Grounding (AutoGen max_turns=2 FinalEditor)
      Layer 4: Telemetry, Audit Logging & Evaluation Metrics
    """

    @classmethod
    def process_governed_request(cls, user_query: str, session_id: str, execution_callback) -> dict:
        start_time = time.time()

        # -------------------------------------------------------------
        # LAYER 1: Input & Data Guardrails
        # -------------------------------------------------------------
        sanitized_query = GuardrailsManager.mask_input_pii(user_query)
        pii_detected = (user_query != sanitized_query)

        # -------------------------------------------------------------
        # LAYER 2: Runtime Layer Budget & Execution Guardrails
        # -------------------------------------------------------------
        # Intercepts query; raises HTTP 429 if token count > 800 or cost > $0.000200
        budget_telemetry = RuntimeBudgetGuard.enforce_budget(user_query)

        # Execute downstream crew agent logic
        try:
            execution_result = execution_callback(sanitized_query, session_id)
            raw_draft = execution_result.get("answer", "")
            retrieved_context = execution_result.get("context", "")
            success = execution_result.get("success", True)
        except Exception as e:
            success = False
            raw_draft = f"Execution error: {str(e)}"
            retrieved_context = ""
            execution_result = {}

        # -------------------------------------------------------------
        # LAYER 3: Multi-Agent Review & Grounding
        # -------------------------------------------------------------
        review_output = AutoGenReviewStage.review_and_refine(
            query=sanitized_query,
            draft_answer=raw_draft,
            retrieved_context=retrieved_context,
            max_turns=2
        )
        final_answer = review_output["reviewed_answer"]
        is_grounded = GuardrailsManager.validate_output_groundedness(final_answer, sanitized_query)

        # -------------------------------------------------------------
        # LAYER 4: Telemetry & Audit Logging
        # -------------------------------------------------------------
        latency = round(time.time() - start_time, 3)
        governance_audit = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": session_id,
            "layers_passed": {
                "layer_1_input_guardrail": {
                    "passed": True,
                    "pii_masked": pii_detected
                },
                "layer_2_runtime_budget_guardrail": {
                    "passed": budget_telemetry["passed"],
                    "estimated_tokens": budget_telemetry["estimated_tokens"],
                    "estimated_cost_usd": budget_telemetry["estimated_cost_usd"]
                },
                "layer_3_multi_agent_review": {
                    "passed": review_output["autogen_metadata"]["structured_verdict"]["approved"]
                },
                "layer_4_telemetry_audit": {
                    "passed": is_grounded,
                    "latency_seconds": latency
                }
            },
            "runtime_budget": budget_telemetry,
            "autogen_governance_metadata": review_output["autogen_metadata"]
        }

        return {
            "success": success and is_grounded,
            "answer": final_answer,
            "metadata": {
                "governance_audit": governance_audit,
                "record_id": execution_result.get("record_id"),
                "escalation_score": execution_result.get("escalation_score")
            }
        }