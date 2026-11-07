# app/test_autogen_demo.py
import json
from autogen_review import AutoGenReviewStage

def demonstrate_autogen_review():
    print("==================================================")
    print("  AUTOGEN REVIEW STAGE: 2-QUERY DEMONSTRATION     ")
    print("==================================================\n")

    # --- CASE 1: Approval Unchanged (Fully Grounded & Safe) ---
    query_1 = "What are the KYC document requirements and acceptable address proofs?"
    draft_1 = "According to Cred policy guidelines: Acceptable KYC documents include Aadhaar, PAN card, and passport. Address proofs include utility bills or voter ID."
    context_1 = "Acceptable KYC documents include Aadhaar, PAN card, and passport. Address proofs include utility bills or voter ID."

    print(f"--- [CASE 1: Approved Unchanged Test] ---")
    print(f"Query: {query_1}")
    print(f"Draft: {draft_1}")
    
    result_1 = AutoGenReviewStage.review_and_refine(
        query=query_1,
        draft_answer=draft_1,
        retrieved_context=context_1,
        max_turns=2
    )
    
    print(f"Result Verdict Approved: {result_1['autogen_metadata']['structured_verdict']['approved']}")
    print(f"Result Reason: {result_1['autogen_metadata']['structured_verdict']['reason']}")
    print(f"Final Answer: {result_1['reviewed_answer']}\n")


    # --- CASE 2: Draft Revision (Deliberately Injected Ungrounded Claim / PII) ---
    query_2 = "Can you check the status of my loan application?"
    # Deliberately injected ungrounded claim and raw PII
    draft_2 = "Your loan is approved for 10 million dollars instantly with zero interest. My PAN is ABCDE1234F."
    context_2 = "Loan applications undergo manual underwriting with standard rates."

    print(f"--- [CASE 2: Draft Revision Test (Injected Ungrounded Claim / PII)] ---")
    print(f"Query: {query_2}")
    print(f"Injected Draft: {draft_2}")
    
    result_2 = AutoGenReviewStage.review_and_refine(
        query=query_2,
        draft_answer=draft_2,
        retrieved_context=context_2,
        max_turns=2
    )
    
    print(f"Result Verdict Approved: {result_2['autogen_metadata']['structured_verdict']['approved']}")
    print(f"Result Reason: {result_2['autogen_metadata']['structured_verdict']['reason']}")
    print(f"Revised Final Answer: {result_2['reviewed_answer']}\n")
    print("==================================================")

if __name__ == "__main__":
    demonstrate_autogen_review()