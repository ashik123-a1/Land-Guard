"""Phase 1 Acceptance Tests: Security & Authorization Hardening
Verifies:
1. Anonymous users cannot list or mutate private cases or complaints.
2. Citizen role cannot access investigator/admin case APIs (403 Forbidden).
3. Citizen A cannot access or expedite Citizen B's complaint (IDOR protection on API and UI).
4. Authorized Admin and Citizen workflows continue to operate smoothly.
5. Password hashing with PBKDF2-HMAC-SHA256 and constant-time comparison.
"""

import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app, service
from src.landguard_web.security import hash_password, verify_password


@pytest.fixture
def unauthenticated_client():
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def citizen_a_client():
    client = TestClient(app, follow_redirects=False)
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    return client


@pytest.fixture
def admin_client():
    client = TestClient(app, follow_redirects=False)
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    return client


def test_password_hashing_pbkdf2():
    """Verify PBKDF2 password hashing format and verification."""
    pw = "supersecret123"
    hashed = hash_password(pw)
    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert verify_password(pw, hashed) is True
    assert verify_password("wrongpassword", hashed) is False
    # Demo legacy password backward-compatibility
    assert verify_password("demo123", "demo123") is True


def test_anonymous_cannot_access_cases(unauthenticated_client):
    """Anonymous client must receive 401 Unauthorized for case endpoints."""
    res_list = unauthenticated_client.get("/api/cases")
    assert res_list.status_code == 401

    res_detail = unauthenticated_client.get("/api/cases/CASE-2026-001")
    assert res_detail.status_code == 401

    res_create = unauthenticated_client.post("/api/cases", json={"title": "Unauthorized Case"})
    assert res_create.status_code == 401


def test_anonymous_cannot_access_complaints(unauthenticated_client):
    """Anonymous client must receive 401 Unauthorized for complaints endpoints."""
    res_list = unauthenticated_client.get("/api/complaints")
    assert res_list.status_code == 401

    res_detail = unauthenticated_client.get("/api/complaints/CMP-2026-001")
    assert res_detail.status_code == 401

    res_create = unauthenticated_client.post("/api/complaints", json={"title": "Test", "category": "SUSPECTED_DOUBLE_SALE", "dag_plot_number": "100", "deed_number": "100", "narrative_description": "Test"})
    assert res_create.status_code == 401


def test_citizen_cannot_access_case_management(citizen_a_client):
    """Citizen role must receive 403 Forbidden for internal case APIs."""
    res_list = citizen_a_client.get("/api/cases")
    assert res_list.status_code == 403

    res_create = citizen_a_client.post("/api/cases", json={"title": "Breached Case"})
    assert res_create.status_code == 403

    res_note = citizen_a_client.post("/api/cases/CASE-2026-001/notes", json={"note": "Hacked note"})
    assert res_note.status_code == 403


def test_citizen_complaint_idor_prevention(citizen_a_client, admin_client):
    """Citizen A must not be able to view or mutate Citizen B's complaint."""
    # Create complaint under Citizen B (simulate separate user)
    comp_b = service.create_complaint(
        user_id="USR-CITIZEN-002",
        data={
            "title": "Private Citizen B Dispute",
            "category": "SUSPECTED_DOUBLE_SALE",
            "dag_plot_number": "5555",
            "deed_number": "DEED-2026-PRIVATE",
            "narrative_description": "Highly sensitive private boundary dispute.",
        }
    )
    b_id = comp_b["complaint_id"]

    # Citizen A (USR-CITIZEN-001) tries to access Citizen B's complaint via API
    res_api = citizen_a_client.get(f"/api/complaints/{b_id}")
    assert res_api.status_code == 403

    # Citizen A tries to expedite Citizen B's complaint via API
    res_exp = citizen_a_client.post(f"/api/complaints/{b_id}/expedite", json={"reason": "Malicious expedite"})
    assert res_exp.status_code == 403

    # Citizen A tries to view Citizen B's complaint via HTML UI
    res_ui = citizen_a_client.get(f"/user/complaints/{b_id}")
    assert res_ui.status_code == 303
    assert "/access-denied" in res_ui.headers["location"]

    # Admin CAN access Citizen B's complaint
    res_admin = admin_client.get(f"/api/complaints/{b_id}")
    assert res_admin.status_code == 200
    assert res_admin.json()["complaint_id"] == b_id


def test_authorized_admin_case_workflow(admin_client):
    """Authorized admin can list, view, update, and add notes to cases."""
    res_list = admin_client.get("/api/cases")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    case_id = res_list.json()[0]["case_id"]
    res_note = admin_client.post(f"/api/cases/{case_id}/notes", json={"note": "Official investigator note.", "author": "Inspector S. Karim"})
    assert res_note.status_code == 200
    assert any("Official investigator note." in n["note"] for n in res_note.json()["officer_notes"])


def test_production_security_guard(monkeypatch):
    """Verifies that demo login is restricted in production mode unless explicitly enabled."""
    from src.landguard_web.security import check_production_security

    # Development mode checks
    sec = check_production_security()
    assert "environment" in sec

    # Production mode: demo login blocked
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_DEMO_LOGIN_IN_PROD", raising=False)

    prod_client = TestClient(app, follow_redirects=False)
    res = prod_client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 403
    assert "disabled in production" in res.json()["detail"]

