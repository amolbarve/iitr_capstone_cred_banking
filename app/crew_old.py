# app/crew.py
import os
os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-local-testing"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import json
from crewai import Agent, Task, Crew, Process
from mock_llm import MockCrewLLM
from memory import session_manager
from schemas import SupportResponseSchema
from guardrails import GuardrailsManager

def run_crew_with_session(user_query: str, session_id: str = "default_session") -> dict:
    # 1. Input-side Guardrail: Mask PII
    sanitized_query = GuardrailsManager.mask_input_pii(user_query)
    
    prior_history = session_manager.get_formatted_history(session_id)
    if prior_history:
        enriched_query = f"Previous Conversation Context:\n{prior_history}\n\nCurrent User Query: {sanitized_query}"
    else:
        enriched_query = sanitized_query

    session_manager.add_user_message(session_id, sanitized_query)

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

    support_task = Task(
        description=f"Address the user query incorporating session history: '{enriched_query}'.",
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
    
    try:
        if hasattr(result, "json_dict") and result.json_dict:
            structured_data = result.json_dict
        elif isinstance(result, dict):
            structured_data = result
        else:
            structured_data = json.loads(str(result))
    except Exception:
        structured_data = {
            "success": True,
            "answer": str(result),
            "metadata": {"fallback": True}
        }

    # 2. Output-side Guardrail: Validate Groundedness
    is_grounded = GuardrailsManager.validate_output_groundedness(structured_data.get("answer", ""), enriched_query)
    structured_data.setdefault("metadata", {})["guardrail_passed"] = is_grounded
    structured_data["metadata"]["pii_masked"] = (user_query != sanitized_query)

    session_manager.add_ai_message(session_id, structured_data.get("answer", str(structured_data)))
    return structured_data

if __name__ == "__main__":
    session = "member_alpha_01"
    
    print("\n================ TESTING INPUT PII MASKING & GROUNDEDNESS (TASK 10) ================")
    
    # Test 1: Valid input containing sensitive PII (PAN & Aadhaar)
    q1 = "Hi, my PAN is ABCDE1234F and Aadhaar is 1234 5678 9012. Can you check status for CRED-LN-001?"
    print(f"\n[Test 1] Original User Input with PII: {q1}")
    res1 = run_crew_with_session(q1, session_id=session)
    print(json.dumps(res1, indent=4))

    # Test 2: Guardrail Pass Example (Grounded policy query)
    q2 = "What are the KYC document requirements for personal loans?"
    print(f"\n[Test 2 - Pass Example] Grounded Query: {q2}")
    res2 = run_crew_with_session(q2, session_id="session_pass")
    print(json.dumps(res2, indent=4))

    # Test 3: Guardrail Fail / Ungrounded Example
    # Simulating an out-of-scope claim or hallucination that lacks context overlap
    print(f"\n[Test 3 - Fail Example Simulation]")
    ungrounded_answer = "Quantum cryptocurrency staking rewards will automatically clear your loan balance by tomorrow."
    forced_query = "Tell me about quantum crypto staking."
    
    # Direct validation check using GuardrailsManager
    fail_validation = GuardrailsManager.validate_output_groundedness(ungrounded_answer, forced_query)
    fail_payload = {
        "success": False,
        "answer": ungrounded_answer,
        "metadata": {
            "source": "simulated_hallucination",
            "guardrail_passed": fail_validation,
            "reason": "Answer lacks keyword overlap and grounding in Cred policy knowledge base."
        }
    }
    print(json.dumps(fail_payload, indent=4))