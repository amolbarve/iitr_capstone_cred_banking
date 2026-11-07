# app/test_least_autonomy.py
from tools import check_loan_application_status
from tool_security import UnauthorizedToolAccessError

def test_least_autonomy_enforcement():
    print("--- Testing Principle of Least Autonomy ---")

    # 1. Authorized call by LookupAgent (Should succeed)
    try:
        res = check_loan_application_status("CRED-LN-001", agent_role="LookupAgent")
        print("-> LookupAgent access: SUCCESS")
    except Exception as e:
        print(f"-> LookupAgent access failed unexpectedly: {e}")

    # 2. Unauthorized call by PolicyRAGAgent (Should raise PermissionError)
    try:
        check_loan_application_status("CRED-LN-001", agent_role="PolicyRAGAgent")
        print("-> PolicyRAGAgent access: UNEXPECTED SUCCESS (Violation)")
    except UnauthorizedToolAccessError as e:
        print(f"-> PolicyRAGAgent access correctly BLOCKED:\n   '{e}'")

if __name__ == "__main__":
    test_least_autonomy_enforcement()