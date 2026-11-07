# app/test_runtime_budget.py
import json
from budget_guard import RuntimeBudgetGuard, BudgetExceededError

def run_tests():
    print("=" * 60)
    print("  TESTING RUNTIME BUDGET GUARD (CAP: 800 TOKENS / $0.000200) ")
    print("=" * 60)

    # 1. Normal Query (Within Limits)
    normal_query = "What are the acceptable address proof documents for KYC verification?"
    print(f"\n[Test 1] Executing standard query: '{normal_query}'")
    try:
        telemetry = RuntimeBudgetGuard.enforce_budget(normal_query)
        print("  -> Status: PASSED")
        print(f"  -> Telemetry: {json.dumps(telemetry, indent=4)}")
    except BudgetExceededError as e:
        print(f"  -> Status: FAILED unexpectedly: {e.detail}")

    # 2. Oversized Query (Breaches Cap)
    # 850 tokens * ~4 characters = ~3400 characters
    oversized_query = "Explain all Cred policies. " + ("lorem ipsum dolor sit amet " * 200)
    print(f"\n[Test 2] Executing deliberately oversized query ({len(oversized_query)} chars, ~{len(oversized_query)//4} tokens)...")
    try:
        RuntimeBudgetGuard.enforce_budget(oversized_query)
        print("  -> Status: FAILED (Oversized query bypassed the guard!)")
    except BudgetExceededError as e:
        print("  -> Status: REJECTED AS EXPECTED (HTTP 429)")
        print(f"  -> Detail:\n{json.dumps(e.detail, indent=4)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_tests()