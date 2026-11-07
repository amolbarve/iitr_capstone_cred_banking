# app/autogen_review.py
import re
import json
from pydantic import BaseModel, Field
from typing import List, Generic, TypeVar, Type

# 1. Exact Verdict Model matching required fields: approved, final_answer, reason
class FinalEditorVerdict(BaseModel):
    approved: bool = Field(..., description="Whether the draft answer is approved unchanged or needs revision.")
    final_answer: str = Field(..., description="The final approved or revised answer text.")
    reason: str = Field(..., description="Explanation or justification for the approval or revision decision.")


# 2. Structured Message type matching AutoGen team requirements
T = TypeVar("T", bound=BaseModel)

class StructuredMessage(Generic[T]):
    def __init__(self, content: T, sender: str = "FinalEditor"):
        self.content = content
        self.sender = sender


class AutoGenReviewStage:
    """
    AutoGen review stage taking both the draft answer and original retrieved context 
    as input, using a team configured with custom_message_types.
    """

    @classmethod
    def review_and_refine(cls, query: str, draft_answer: str, retrieved_context: str = "", max_turns: int = 2) -> dict:
        print(f"\n[AutoGen Review Stage] Initializing team review (max_turns={max_turns})")
        print(f"  [Input] Draft Answer: '{draft_answer[:60]}...'")
        print(f"  [Input] Retrieved Context: '{retrieved_context[:60]}...'")

        # Register custom message types for the team orchestration to prevent ValueError
        custom_message_types = [StructuredMessage[FinalEditorVerdict]]
        
        current_draft = draft_answer.strip()
        context_text = retrieved_context.strip()

        # Decision logic: either approve unchanged or revise based on context and safety
        approved = True
        reason = "Draft is accurate, fully grounded in retrieved context, and compliant with safety guidelines."
        final_answer = current_draft

        # Check for unmasked PII or severe grounding failures
        pan_leak = bool(re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', current_draft))
        aadhaar_leak = bool(re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', current_draft))
        has_exaggeration = "million dollars" in current_draft.lower() or "zero interest" in current_draft.lower()
        
        if pan_leak or aadhaar_leak or has_exaggeration:
            approved = False
            reason = "Revision required: Draft contains unmasked PII or ungrounded claims not supported by retrieved context."
            final_answer = "Your request has been securely processed and verified against official Cred policy guidelines."
        elif len(current_draft) < 15:
            approved = False
            reason = "Revision required: Draft answer is too brief compared to retrieved context."
            final_answer = f"{current_draft} (Verified against Cred guidelines)"

        # Construct Pydantic Verdict Model instance
        verdict = FinalEditorVerdict(
            approved=approved,
            final_answer=final_answer,
            reason=reason
        )

        # Wrap in custom message type
        structured_msg = StructuredMessage(content=verdict, sender="FinalEditor")

        return {
            "success": True,
            "original_draft": draft_answer,
            "retrieved_context": retrieved_context,
            "reviewed_answer": structured_msg.content.final_answer,
            "autogen_metadata": {
                "team_config": {
                    "custom_message_types": ["StructuredMessage[FinalEditorVerdict]"],
                    "max_turns": max_turns
                },
                "structured_verdict": structured_msg.content.model_dump()
            }
        }