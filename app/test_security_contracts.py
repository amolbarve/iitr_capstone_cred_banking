# app/test_security_contracts.py
import pytest
import json
from tools import check_loan_application_status
from tool_security import UnauthorizedToolAccessError
from crew import run_crew_with_session

class TestLeastAutonomyContract:

    def test_unauthorized_agent_cannot_access_loan_status(self):
        """
        Verifies that unauthorized agents attempting to access the restricted tool
        trigger an UnauthorizedToolAccessError.
        """
        # Explicitly pass a mismatched authorized role to trigger the security block
        with pytest.raises((UnauthorizedToolAccessError, PermissionError)) as exc_info:
            check_loan_application_status("CRED-LN-001", agent_role="PolicyRetrievalSpecialist")
        assert "Access Denied" in str(exc_info.value)

    def test_authorized_lookup_agent_succeeds(self):
        """
        Verifies that the designated LookupAgent can execute the tool successfully.
        """
        res_str = check_loan_application_status("CRED-LN-001", agent_role="LookupAgent")
        data = json.loads(res_str)
        assert data.get("record_id") == "CRED-LN-001"
        assert "status" in data
        assert "escalation_score" in data

    def test_end_to_end_crew_execution_passes_role_properly(self):
        """
        Ensures run_crew_with_session executes loan lookups successfully.
        """
        query = "Can you check the current status of application CRED-LN-001?"
        session_id = "test_contract_session"

        response = run_crew_with_session(query, session_id=session_id)

        assert "Access Denied" not in response.get("answer", "")
        assert response.get("record_id") == "CRED-LN-001"
        assert response.get("escalation_score") is not None


class TestFastAPIEndpointSecurity:

    def test_api_endpoint_loan_lookup_e2e(self):
        """
        Ensures the HTTP endpoint processes loan lookup requests correctly.
        """
        from fastapi.testclient import TestClient
        from api import app

        client = TestClient(app)
        payload = {
            "query": "My PAN is ABCDE1234F. Check loan application CRED-LN-001.",
            "session_id": "test_api_session_01"
        }

        response = client.post("/ask", json=payload)
        assert response.status_code == 200
        
        body = response.json()
        assert "Access Denied" not in body.get("answer", "")
        assert body.get("record_id") == "CRED-LN-001"