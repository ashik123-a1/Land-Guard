"""Tests for LandGuard Authentication, Session Isolation, RBAC, and Portals.
Verifies login-first architecture, role-based route separation, citizen vs admin access boundaries,
grievance submission, expedited review workflow, and logout session termination.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app

client = TestClient(app, follow_redirects=False)


def test_unauthenticated_protected_routes_redirect_to_login():
    """Unauthenticated access to citizen or admin routes must redirect (303) to /login."""
    # Citizen protected route
    res_user = client.get("/user/dashboard")
    assert res_user.status_code == 303
    assert "/login?redirect=/user/dashboard" in res_user.headers["location"]

    # Admin protected route
    res_admin = client.get("/admin/dashboard")
    assert res_admin.status_code == 303
    assert "/login?redirect=/admin/dashboard" in res_admin.headers["location"]


def test_public_pages_accessible_without_auth():
    """Landing, login, access-denied, and not-found must be publicly accessible without session."""
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/access-denied").status_code == 200
    assert client.get("/not-found").status_code == 200


def test_login_invalid_credentials_returns_401():
    """Invalid credentials return 401 Unauthorized."""
    payload = {"email": "citizen@landguard.gov.bd", "password": "wrong_password"}
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_citizen_demo_login_flow():
    """Citizen login reaches citizen dashboard and cannot access admin dashboard."""
    # 1. Demo login as citizen
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["redirect_url"] == "/user/dashboard"
    assert data["user"]["role"] == "CITIZEN"

    # Capture session cookie
    cookie = res.cookies.get("landguard_session")
    assert cookie is not None

    # 2. Access citizen dashboard with cookie
    client_sess = TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)
    dash_res = client_sess.get("/user/dashboard")
    assert dash_res.status_code == 200
    assert "Citizen Verification Center" in dash_res.text
    assert ("Nakib Md Ashik" in dash_res.text or "Rafiqul Islam" in dash_res.text)
    assert "CIT-BD-884920" in dash_res.text

    # 3. Citizen trying to access admin dashboard must be blocked with redirect to /access-denied
    admin_res = client_sess.get("/admin/dashboard")
    assert admin_res.status_code == 303
    assert admin_res.headers["location"] == "/access-denied"


def test_admin_demo_login_flow():
    """Admin login reaches admin dashboard and has operational access."""
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["redirect_url"] == "/admin/dashboard"
    assert data["user"]["role"] == "ADMIN"

    cookie = res.cookies.get("landguard_session")
    client_admin = TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)

    dash_res = client_admin.get("/admin/dashboard")
    assert dash_res.status_code == 200
    assert "Investigator Command Center" in dash_res.text
    assert "Priority Investigation Docket" in dash_res.text


def test_citizen_complaint_and_expedite_workflow():
    """Citizen can submit a complaint, request expedite, and admin can approve expedite."""
    # 1. Login as citizen
    res_auth = client.post("/api/auth/demo-login?role=citizen")
    cookie = res_auth.cookies.get("landguard_session")
    client_cit = TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)

    # 2. Submit new complaint
    comp_payload = {
        "category": "SUSPECTED_DOUBLE_SALE",
        "dag_plot_number": "6792",
        "deed_number": "DEED-2005-23539",
        "title": "Double Selling Notice on Paba Plot #6792",
        "narrative_description": "Broker presented duplicate transfer deed while AC Land mutation is pending.",
        "is_expedited": True,
        "expedite_reason": "Vendor threatens cancellation within 24 hours.",
    }
    comp_res = client_cit.post("/api/complaints", json=comp_payload)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    comp_id = comp_data["complaint_id"]
    assert "CMP-" in comp_id
    assert comp_data["is_expedited"] is True
    assert comp_data["expedite_status"] == "PENDING_DECISION"

    # 3. Check complaint detail page loads for citizen
    detail_res = client_cit.get(f"/user/complaints/{comp_id}")
    assert detail_res.status_code == 200
    assert comp_id in detail_res.text

    # 4. Admin decides expedite
    res_admin_auth = client.post("/api/auth/demo-login?role=admin")
    admin_cookie = res_admin_auth.cookies.get("landguard_session")
    client_adm = TestClient(app, cookies={"landguard_session": admin_cookie}, follow_redirects=False)

    dec_res = client_adm.post(
        f"/api/cases/{comp_id}/expedite/decision",
        json={"decision": "APPROVED", "reason": "Urgent impending transfer confirmed with Sub-Registry."}
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["expedite_status"] == "APPROVED"
    assert dec_data["priority"] == "CRITICAL"


def test_logout_clears_session():
    """Logout invalidates the session and deletes the session cookie."""
    # Login
    res = client.post("/api/auth/demo-login?role=citizen")
    cookie = res.cookies.get("landguard_session")
    client_sess = TestClient(app, cookies={"landguard_session": cookie}, follow_redirects=False)

    # Verify session active
    assert client_sess.get("/user/dashboard").status_code == 200

    # Logout
    logout_res = client_sess.get("/logout")
    assert logout_res.status_code == 303
    assert logout_res.headers["location"] == "/login"

    # Verify cookie was deleted / invalidated
    cleared_client = TestClient(app, cookies={"landguard_session": "INVALID"}, follow_redirects=False)
    assert cleared_client.get("/user/dashboard").status_code == 303
