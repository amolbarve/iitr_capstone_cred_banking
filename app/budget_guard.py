# app/budget_guard.py
from fastapi import HTTPException

class BudgetExceededError(HTTPException):
    """Raised when an incoming query breaches per-request token or cost ceilings."""
    def __init__(self, detail: dict):
        super().__init__(status_code=429, detail=detail)

class RuntimeBudgetGuard:
    """
    Enforces hard per-request ceilings on token volume and estimated inference cost 
    prior to invoking downstream agents.
    """
    # Reference pricing: $0.25 per 1,000,000 input tokens
    INPUT_COST_PER_MILLION_TOKENS = 0.25

    # Hard operational caps per single request
    MAX_INPUT_TOKENS = 800
    MAX_COST_USD = 0.000200

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Heuristic character-to-token ratio (approx. 4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text.strip()) // 4)

    @classmethod
    def calculate_cost(cls, token_count: int) -> float:
        """Calculates estimated input cost in USD."""
        return (token_count / 1_000_000) * cls.INPUT_COST_PER_MILLION_TOKENS

    @classmethod
    def enforce_budget(cls, query: str) -> dict:
        """
        Evaluates input query against budget limits.
        Fails closed with HTTP 429 if either threshold is breached.
        """
        estimated_tokens = cls.estimate_tokens(query)
        estimated_cost = cls.calculate_cost(estimated_tokens)

        if estimated_tokens > cls.MAX_INPUT_TOKENS or estimated_cost > cls.MAX_COST_USD:
            rejection_payload = {
                "error": "BUDGET_CAP_EXCEEDED",
                "message": (
                    f"Request rejected at Runtime Layer: estimated token count ({estimated_tokens}) "
                    f"or estimated cost (${estimated_cost:.6f}) exceeds per-request threshold "
                    f"(Max Tokens: {cls.MAX_INPUT_TOKENS}, Max Cost: ${cls.MAX_COST_USD:.6f})."
                ),
                "budget_metrics": {
                    "estimated_tokens": estimated_tokens,
                    "max_token_cap": cls.MAX_INPUT_TOKENS,
                    "estimated_cost_usd": round(estimated_cost, 6),
                    "max_cost_usd": cls.MAX_COST_USD
                }
            }
            raise BudgetExceededError(detail=rejection_payload)

        return {
            "passed": True,
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
            "max_token_cap": cls.MAX_INPUT_TOKENS,
            "max_cost_usd": cls.MAX_COST_USD
        }