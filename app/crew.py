# app/crew.py
import json
import re
from crewai import Agent, Task, Crew, Process
from mock_llm import MockCrewLLM
from tools import check_loan_application_status, rag_policy_search
from guardrails import GuardrailsManager
from memory import session_manager
from schemas import SupportResponseSchema
from autogen_review import AutoGenReviewStage

def run_crew_with_session(user_query: str, session_id: str = "default_session") -> dict:
    # 1. Input-side Guardrail: Mask PII
    sanitized_query = GuardrailsManager.mask_input_pii(user_query)
    session_manager.add_user_message(session_id, sanitized_query)

    # 2. Retrieve multi-turn history
    prior_history = session_manager.get_formatted_history(session_id)
    enriched_query = f"Previous Conversation Context:\n{prior_history}\n\nCurrent User Query: {sanitized_query}" if prior_history else sanitized_query

    # 3. Check for Loan Lookup & Escalation
    loan_match = re.search(r"CRED-LN-\d+", enriched_query, re.IGNORECASE)
    record_id = None
    escalation_score = None
    requires_escalation = False
    retrieved_tool_context = ""

    if loan_match:
        raw_match = loan_match.group(0).upper()
        record_id = re.sub(r"[-_\s]", "-", raw_match)        # --- PASS AGENT ROLE HERE ---
        
        tool_output_str = check_loan_application_status(record_id, agent_role="LookupAgent")
        retrieved_tool_context = tool_output_str
        try:
            tool_data = json.loads(tool_output_str)
            escalation_score = tool_data.get("escalation_score")
            requires_escalation = tool_data.get("requires_escalation")
        except Exception:
            pass
    elif any(k in enriched_query.lower() for k in ["kyc", "emi", "fee", "penalty", "interest", "score", "closure", "joint", "nri", "policy", "nach"]):
        retrieved_tool_context = rag_policy_search(enriched_query)

    # 4. Instantiate the 3 Required CrewAI Agents
    mock_llm = MockCrewLLM()

    retrieval_agent = Agent(
        role="Policy Retrieval Specialist",
        goal="Retrieve exact policy guidelines and terms from the Cred knowledge base.",
        backstory="An expert compliance officer who navigates Cred policy documentation accurately.",
        tools=[],
        llm=mock_llm,
        verbose=False
    )

    lookup_agent = Agent(
        role="Loan Application Specialist",
        goal="Retrieve real-time loan application records and compute escalation scores.",
        backstory="A lending-operations analyst who manages customer application records.",
        tools=[],
        llm=mock_llm,
        verbose=False
    )

    composer_agent = Agent(
        role="Customer Support Composer",
        goal="Synthesize information from policies and application records into clear member responses.",
        backstory="A senior support representative skilled at delivering grounded and empathetic support.",
        tools=[],
        llm=mock_llm,
        verbose=False
    )

    # 5. Define CrewAI Task and Execute Crew
    support_task = Task(
        description=(
            f"User Query: '{enriched_query}'.\n"
            f"Context Data: '{retrieved_tool_context}'."
        ),
        expected_output="A JSON object conforming strictly to SupportResponseSchema.",
        agent=composer_agent,
        output_json=SupportResponseSchema
    )

    crew = Crew(
        agents=[retrieval_agent, lookup_agent, composer_agent],
        tasks=[support_task],
        process=Process.sequential,
        verbose=False
    )

    result = crew.kickoff(inputs={"user_query": enriched_query})
    
    # Extract draft answer from CrewAI
    draft_answer = ""
    try:
        if hasattr(result, "json_dict") and result.json_dict:
            draft_answer = result.json_dict.get("answer", "")
        elif isinstance(result, dict):
            draft_answer = result.get("answer", "")
        else:
            draft_answer = json.loads(str(result)).get("answer", str(result))
    except Exception:
        draft_answer = str(result)

    # Fallback to direct context if Mock LLM returned generic boilerplate
    if not draft_answer or "default response" in draft_answer.lower():
        if record_id and 'tool_data' in locals() and "status" in tool_data:
            draft_answer = f"Application {record_id} is currently '{tool_data.get('status')}' with an amount of ₹{tool_data.get('loan_amount_inr', 0):,}."
        elif retrieved_tool_context:
            draft_answer = f"Based on Cred policy guidelines: {retrieved_tool_context}"
        else:
            draft_answer = "Your request has been recorded and reviewed under Cred's guidelines."

    # 6. Output-side Guardrail: Groundedness Validation
    is_grounded = GuardrailsManager.validate_output_groundedness(draft_answer, enriched_query)

    # 7. Task 14: AutoGen Review Stage (max_turns=2)
    review_output = AutoGenReviewStage.review_and_refine(
        query=user_query,
        draft_answer=draft_answer,
        retrieved_context=retrieved_tool_context,
        max_turns=2
    )
    final_answer = review_output.get("reviewed_answer", draft_answer)

    # 8. Save final turn to session memory
    session_manager.add_ai_message(session_id, final_answer)

    return {
        "success": is_grounded,
        "answer": final_answer,
        "record_id": record_id,
        "escalation_score": escalation_score,
        "requires_escalation": requires_escalation,
        "metadata": {
            "source": "loans_lookup" if record_id else "rag_kb",
            "guardrail_passed": is_grounded,
            "pii_masked": (user_query != sanitized_query),
            "autogen_review": review_output.get("autogen_metadata", {})
        }
    }