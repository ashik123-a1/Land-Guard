"""Automated test suite for LandGuard Clarification Workflow and SLA Overdue Tracking.
Validates:
1. Investigation case clarification workflow:
   - Admin requests clarification -> status transitions to AWAITING_INFORMATION.
   - Citizen receives in-app notification and responds -> status transitions back to UNDER_REVIEW.
   - All state changes, notes, and events persist in SQLite.
2. Deterministic SLA tracking:
   - Critical priority: 24h SLA.
   - High priority: 48h SLA.
   - Normal priority: 120h SLA.
   - Computes hours_remaining, hours_overdue, and marks overdue state.
3. Overdue cases REST API endpoint GET /api/cases/overdue with RBAC.
"""

import datetime
import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app, service
from src.landguard_data.database import LandGuardDatabase

client = TestClient(app, follow_redirects=False)


@pytest.fixture(scope="module")
def admin_session_cookie():
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    return res.cookies.get("landguard_session")


@pytest.fixture(scope="module")
def citizen_session_cookie():
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    return res.cookies.get("landguard_session")


def test_case_clarification_workflow(admin_session_cookie, citizen_session_cookie):
    """Test full cycle of clarification request, citizen notification, response, and SQLite persistence."""
    c_admin = TestClient(app, cookies={"landguard_session": admin_session_cookie})
    c_citizen = TestClient(app, cookies={"landguard_session": citizen_session_cookie})

    case_id = "CASE-2026-001"
    question = "Please submit the certified family partition sketch (Bonton-nama) registered in 2012."

    # 1. Anonymous cannot request clarification
    anon_client = TestClient(app, follow_redirects=False)
    anon_res = anon_client.post(
        f"/api/cases/{case_id}/clarification/request",
        json={"question": question},
    )
    assert anon_res.status_code == 401

    # 2. Admin requests clarification
    req_res = c_admin.post(
        f"/api/cases/{case_id}/clarification/request",
        json={"question": question},
    )
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["success"] is True
    assert req_data["status"] == "AWAITING_INFORMATION"

    # 3. Verify SQLite note and status
    db = LandGuardDatabase()
    notes = db.get_case_notes(case_id)
    assert any("[CLARIFICATION REQUESTED]" in n["note"] and question in n["note"] for n in notes)

    db_case = db.get_case(case_id)
    assert db_case["status"] == "AWAITING_INFORMATION"

    # 4. Verify citizen received notification
    notifs = service.get_notifications("USR-CITIZEN-001")
    assert any("Clarification Requested" in n["title"] for n in notifs)

    # 5. Citizen responds
    response_text = "I have uploaded the certified Bonton-nama copy under deed archive reference 2012-PABA-881."
    resp_res = c_citizen.post(
        f"/api/cases/{case_id}/clarification/respond",
        json={"response": response_text},
    )
    assert resp_res.status_code == 200
    resp_data = resp_res.json()
    assert resp_data["success"] is True
    assert resp_data["status"] == "UNDER_REVIEW"

    # 6. Verify SQLite note and restored status
    notes_after = db.get_case_notes(case_id)
    assert any("[CITIZEN CLARIFICATION RESPONSE]" in n["note"] and response_text in n["note"] for n in notes_after)

    db_case_after = db.get_case(case_id)
    assert db_case_after["status"] == "UNDER_REVIEW"


def test_sla_calculation_and_overdue_detection():
    """Verify deterministic SLA computation correctly flags overdue cases based on priority and elapsed hours."""
    now = datetime.datetime.now()

    # Case 1: Created 60 hours ago with HIGH priority (SLA is 48h) -> OVERDUE
    overdue_case = {
        "case_id": "CASE-TEST-OVERDUE",
        "created_at": (now - datetime.timedelta(hours=60)).isoformat(),
        "priority": "HIGH",
        "status": "UNDER_REVIEW",
    }
    sla_result_1 = service.compute_case_sla(overdue_case)
    assert sla_result_1["sla_target_hours"] == 48
    assert sla_result_1["is_overdue"] is True
    assert sla_result_1["hours_overdue"] >= 11.0
    assert sla_result_1["sla_state"] == "OVERDUE"

    # Case 2: Created 4 hours ago with NORMAL priority (SLA is 120h) -> ON TRACK
    active_case = {
        "case_id": "CASE-TEST-ACTIVE",
        "created_at": (now - datetime.timedelta(hours=4)).isoformat(),
        "priority": "NORMAL",
        "status": "UNDER_REVIEW",
    }
    sla_result_2 = service.compute_case_sla(active_case)
    assert sla_result_2["sla_target_hours"] == 120
    assert sla_result_2["is_overdue"] is False
    assert sla_result_2["hours_remaining"] >= 115.0
    assert sla_result_2["sla_state"] == "ON_TRACK"

    # Case 3: Resolved case -> not overdue
    resolved_case = {
        "case_id": "CASE-TEST-RESOLVED",
        "created_at": (now - datetime.timedelta(days=10)).isoformat(),
        "priority": "CRITICAL",
        "status": "RESOLVED",
    }
    sla_result_3 = service.compute_case_sla(resolved_case)
    assert sla_result_3["is_overdue"] is False
    assert sla_result_3["sla_state"] == "RESOLVED"


def test_overdue_cases_endpoint_rbac(admin_session_cookie, citizen_session_cookie):
    """GET /api/cases/overdue requires admin/investigator access and returns overdue cases."""
    c_admin = TestClient(app, cookies={"landguard_session": admin_session_cookie})
    c_citizen = TestClient(app, cookies={"landguard_session": citizen_session_cookie})
    anon_client = TestClient(app, follow_redirects=False)

    # 1. Anonymous rejected (401)
    assert anon_client.get("/api/cases/overdue").status_code == 401

    # 2. Citizen rejected (403)
    assert c_citizen.get("/api/cases/overdue").status_code == 403

    # 3. Admin succeeds (200)
    res = c_admin.get("/api/cases/overdue")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_sla_escalations_idempotent_notification(admin_session_cookie):
    """Verifies that SLA breach generates real audit note, in-app notification, and is idempotent on repeat sweeps."""
    now = datetime.datetime.now()
    case_id = "CASE-SLA-ESCALATE-TEST"
    service.cases[case_id] = {
        "case_id": case_id,
        "title": "Breached SLA Investigation",
        "dag_plot_number": "9044",
        "created_at": (now - datetime.timedelta(hours=72)).isoformat(),
        "updated_at": (now - datetime.timedelta(hours=72)).isoformat(),
        "priority": "HIGH",
        "status": "OPEN",
        "assigned_officer": "Inspector S. Karim",
        "officer_notes": [],
    }

    # First sweep: produces escalation event, note, and notification
    events = service.process_sla_escalations()
    assert any(e["case_id"] == case_id for e in events)

    c = service.get_case(case_id)
    notes = c.get("officer_notes", [])
    assert any("[SLA OVERDUE ESCALATION]" in n["note"] for n in notes)

    notifs = service.get_notifications("USR-ADMIN-001")
    assert any(f"SLA Overdue: Case {case_id}" in n["title"] for n in notifs)

    # Second sweep: idempotent guarantee (zero duplicate escalations)
    repeat_events = service.process_sla_escalations()
    assert not any(e["case_id"] == case_id for e in repeat_events)


def test_case_reassignment_and_priority_history():
    """Verifies case reassignment records assignment history, and priority change logs priority history."""
    case_id = "CASE-2026-001"
    orig = service.get_case(case_id)
    orig_officer = orig.get("assigned_officer", "Senior Registrar M. Rahman")

    # 1. Reassign officer
    updated = service.update_case(
        case_id,
        {
            "assigned_officer": "Special Investigator T. Ahmed",
            "assigned_by": "Chief Registrar",
        },
    )
    assert updated["assigned_officer"] == "Special Investigator T. Ahmed"
    assert "assignment_history" in updated
    assert len(updated["assignment_history"]) >= 1
    last_assign = updated["assignment_history"][-1]
    assert last_assign["previous_officer"] == orig_officer
    assert last_assign["new_officer"] == "Special Investigator T. Ahmed"
    assert last_assign["assigned_by"] == "Chief Registrar"

    notes = updated.get("officer_notes", [])
    assert any("[OFFICER REASSIGNED]" in n["note"] and "Special Investigator T. Ahmed" in n["note"] for n in notes)

    # 2. Priority escalation with reason
    updated_prio = service.update_case(
        case_id,
        {
            "priority": "CRITICAL",
            "priority_reason": "Statutory high-risk double-selling suspected with imminent execution",
            "escalated_by": "Chief Registrar",
        },
    )
    assert updated_prio["priority"] == "CRITICAL"
    assert "priority_history" in updated_prio
    last_prio = updated_prio["priority_history"][-1]
    assert last_prio["new_priority"] == "CRITICAL"
    assert "imminent execution" in last_prio["reason"]

