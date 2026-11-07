# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SupportResponseSchema(BaseModel):
    """Enforces a strict structured output schema for all Cred support agent responses."""
    success: bool = Field(..., description="Indicates whether the request was successfully processed.")
    answer: str = Field(..., description="The primary response or resolution provided to the member.")
    record_id: Optional[str] = Field(None, description="The loan application ID referenced, if applicable.")
    escalation_score: Optional[float] = Field(None, description="Computed escalation score if a loan record was evaluated.")
    requires_escalation: Optional[bool] = Field(None, description="Flag indicating if immediate operational escalation is required.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context, metrics, or trace metadata.")