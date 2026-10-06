import time
import sys
import os

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_test_user():
    username = f"testuser_{time.time_ns()}"
    email = f"{username}@example.com"

    response = client.post(
        "/api/v1/auth/register",
        params={
            "username": username,
            "email": email,
            "password": "Test@12345",
            "role": "TESTER"
        }
    )

    assert response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": username,
            "password": "Test@12345"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


# --------------------------------------------------
# AUTHENTICATION TEST
# --------------------------------------------------

def test_authentication():
    headers = create_test_user()

    response = client.get(
        "/api/v1/auth/me",
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "username" in data
    assert data["role"] == "TESTER"


# --------------------------------------------------
# ISSUE CREATE + READ TEST
# --------------------------------------------------

def test_issue_create_and_read():
    headers = create_test_user()

    response = client.post(
    "/api/v1/issues/",
    json={
        "title": "Automated Test Issue",
        "description": "Issue created during pytest",
        "severity": "MINOR",
        "priority": "MEDIUM",
        "project_id": 6,
        "category_id": 1,
        "reproduction_steps": "Run pytest",
        "affected_modules": "Testing",
        "environment_details": "Test Environment",
        "estimated_effort": 2
    },
    headers=headers
)
    assert response.status_code == 200

    data = response.json()

    assert "issue_id" in data
    assert data["status"] == "REPORTED"

    issue_id = data["issue_id"]

    get_response = client.get(
        f"/api/v1/issues/{issue_id}",
        headers=headers
    )
    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert get_response.status_code == 200

    issue = get_response.json()

    assert issue["issue_id"] if "issue_id" in issue else issue["id"] == issue_id
    assert issue["status"] == "REPORTED"


# --------------------------------------------------
# ISSUE LIST FILTER TEST
# --------------------------------------------------

def test_issue_filters():
    headers = create_test_user()

    response = client.get(
        "/api/v1/issues/",
        params={
            "project_id": 6,
            "severity": "MINOR",
            "search": "button"
        },
        headers=headers
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# --------------------------------------------------
# INVALID WORKFLOW TEST
# --------------------------------------------------

def test_invalid_workflow_transition():
    headers = create_test_user()

    # B-005 is currently REPORTED.
    # REPORTED -> RESOLVED is invalid.
    response = client.patch(
        "/api/v1/issues/5/status",
        params={
            "status": "RESOLVED"
        },
        headers=headers
    )

    assert response.status_code == 400

    assert "Invalid transition" in response.json()["detail"]


# --------------------------------------------------
# DUPLICATE DETECTION TEST
# --------------------------------------------------

def test_duplicate_detection():
    headers = create_test_user()

    response = client.post(
        "/api/v1/issues/check-duplicates",
        params={
            "title": "Profile page is not loading",
            "project_id": 4
        },
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "is_duplicate" in data
    assert "duplicates" in data