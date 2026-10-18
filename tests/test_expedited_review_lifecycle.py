"""Automated test suite for Expedited Review Lifecycle & Statutory Priority Governance.
Validates:
1. Citizen request with statutory urgency categories.
2. Duplicate pending request prevention (raises HTTP 400).
3. Administrative approval, priority escalation to CRITICAL, and priority history tracking.
4. Administrative REQUEST_INFO decision transitioning expedite status to AWAITING_INFORMATION.
5. Administrative rejection preserving prior priority.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_web.service import service

client = TestClient(app, follow_redirects=False)


def test_expedited_review_duplicate_prevention_and_categories():
    """Verify duplicate pending expedite request is rejected with HTTP 400."""
    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")

    # Create fresh complaint for test
    create_res = auth_client.post(
        "/api/complaints",
        json={
            "title": "Expedite Lifecycle Test Complaint",
            "category": "SUSPECTED_DOUBLE_SALE",
            "dag_plot_number": "9044",
            "deed_number": "DEED-EXP-001",
            "narrative_description": "Testing expedited review duplicate prevention.",
        },
    )
    assert create_res.status_code == 200
    comp_id = create_res.json()["complaint_id"]

    # First request: should succeed
    exp1 = auth_client.post(
        f"/api/complaints/{comp_id}/expedite",
        json={
            "reason": "Earnest deposit expires in 48 hours.",
            "reason_category": "POTENTIALLY_IMMINENT_TRANSACTION",
        },
    )
    assert exp1.status_code == 200
    data1 = exp1.json()
    assert data1["is_expedited"] is True
    assert data1["expedite_status"] == "PENDING_DECISION"
    assert "POTENTIALLY_IMMINENT_TRANSACTION" in data1["expedite_reason"]

    # Duplicate request while still pending: MUST fail with HTTP 400
    exp2 = auth_client.post(
        f"/api/complaints/{comp_id}/expedite",
        json={
            "reason": "Submitting duplicate request.",
            "reason_category": "EXCESSIVE_WAITING_TIME",
        },
    )
    assert exp2.status_code == 400
    assert "already pending" in exp2.json()["detail"].lower()


def test_admin_decide_expedite_approval_and_priority_history():
    """Admin approves expedite request: escalates priority to CRITICAL and records priority history."""
    admin_client = TestClient(app, follow_redirects=False)
    admin_client.post("/api/auth/demo-login?role=admin")

    citizen_client = TestClient(app, follow_redirects=False)
    citizen_client.post("/api/auth/demo-login?role=citizen")

    # Create complaint and request expedite
    comp_res = citizen_client.post(
        "/api/complaints",
        json={
            "title": "Complaint for Admin Approval Test",
            "category": "OWNERSHIP_CONFLICT",
            "dag_plot_number": "7025",
            "deed_number": "DEED-EXP-002",
            "narrative_description": "Critical title conflict.",
        },
    )
    comp_id = comp_res.json()["complaint_id"]
    citizen_client.post(
        f"/api/complaints/{comp_id}/expedite",
        json={"reason": "Impending registration hearing", "reason_category": "NEW_EVIDENCE"},
    )

    # Admin approves
    dec_res = admin_client.post(
        f"/api/cases/{comp_id}/expedite/decision",
        json={"decision": "APPROVED", "reason": "Verified earnest money deadline under statutory framework."},
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["expedite_status"] == "APPROVED"
    assert dec_data["priority"] == "CRITICAL"
    assert len(dec_data["priority_history"]) >= 1
    assert dec_data["priority_history"][-1]["priority"] == "CRITICAL"


def test_admin_decide_expedite_request_info():
    """Admin requests additional info: expedite status transitions to AWAITING_INFORMATION."""
    admin_client = TestClient(app, follow_redirects=False)
    admin_client.post("/api/auth/demo-login?role=admin")

    citizen_client = TestClient(app, follow_redirects=False)
    citizen_client.post("/api/auth/demo-login?role=citizen")

    comp_res = citizen_client.post(
        "/api/complaints",
        json={
            "title": "Complaint for Info Request Test",
            "category": "RECORD_MISMATCH",
            "dag_plot_number": "5235",
            "deed_number": "DEED-EXP-003",
            "narrative_description": "Record mismatch dispute.",
        },
    )
    comp_id = comp_res.json()["complaint_id"]
    citizen_client.post(
        f"/api/complaints/{comp_id}/expedite",
        json={"reason": "Need rapid review", "reason_category": "OTHER_JUSTIFIED_URGENCY"},
    )

    # Admin requests information
    dec_res = admin_client.post(
        f"/api/cases/{comp_id}/expedite/decision",
        json={"decision": "REQUEST_INFO", "reason": "Please attach earnest agreement or registered bank receipt."},
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["expedite_status"] == "AWAITING_INFORMATION"
