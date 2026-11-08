# app/test_queries_demo.py
import requests

BASE_URL = "http://127.0.0.1:8000"

test_cases = [
    {
        "type": "In-Scope: Loan Status Inquiry",
        "payload": {
            "session_id": "demo_session_1",
            "query": "Can you check the status of my loan application CRED-LN-001?"
        }
    },
    {
        "type": "In-Scope: Repayment & EMI Policy",
        "payload": {
            "session_id": "demo_session_2",
            "query": "What is the penalty fee if my EMI payment is delayed past the due date?"
        }
    },
    {
        "type": "In-Scope: Foreclosure Terms",
        "payload": {
            "session_id": "demo_session_3",
            "query": "What are the foreclosure charges for closing my personal loan early?"
        }
    },
    {
        "type": "In-Scope: Reward Points Policy",
        "payload": {
            "session_id": "demo_session_4",
            "query": "How many reward points do I earn on dining categories using HDFC Regalia?"
        }
    },
    {
        "type": "In-Scope: KYC Documentation",
        "payload": {
            "session_id": "demo_session_5",
            "query": "What documents are required to complete my loan verification KYC?"
        }
    },
    {
        "type": "Out-of-Scope (Fallback Trigger)",
        "payload": {
            "session_id": "demo_session_fallback",
            "query": "Can you write a Python script to scrape live football match scores from the English Premier League?"
        }
    }
]

def run_query_demonstration():
    print("=" * 80)
    print("CRED SUPPORT AGENT: IN-SCOPE & OUT-OF-SCOPE DEMONSTRATION")
    print("=" * 80)
    
    for idx, test in enumerate(test_cases, 1):
        q_type = test["type"]
        payload = test["payload"]
        
        print(f"\n[{idx}] Testing: {q_type}")
        print(f"Query: \"{payload['query']}\"")
        
        response = requests.post(f"{BASE_URL}/ask", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("-" * 80)

if __name__ == "__main__":
    run_query_demonstration()