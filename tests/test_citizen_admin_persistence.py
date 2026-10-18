"""Integration Test Suite: Citizen-Admin Persistence, Cross-Role Notifications & Live Tracking
Tests restart resilience across SQLite operational database without in-memory state leakage.
"""

import os
import json
import uuid
import tempfile
import pytest
from fastapi.testclient import TestClient

from src.landguard_data.database import LandGuardDatabase
from src.landguard_services.verification_service import VerificationService
from src.landguard_services.analytics_service import AnalyticsService
from src.landguard_services.case_service import CaseService
from src.landguard_services.complaint_service import ComplaintService
from src.landguard_services.notification_service import NotificationService
from src.landguard_web.app import app
from src.landguard_web.service import service


@pytest.fixture
def isolated_db_path(tmp_path):
    """Provides a fresh temporary SQLite database path for strict restart simulation."""
    db_file = tmp_path / "test_persistence.db"
    return str(db_file)


def test_verification_history_persistence_across_restart(isolated_db_path):
    """Verifies that verification runs persist in SQLite and survive a complete service restart."""
    db = LandGuardDatabase(db_path=isolated_db_path)
    verif_svc = VerificationService(db=db)
    analytics_svc = AnalyticsService(db=db)

    # 1. Run a verification for Citizen A
    citizen_a = "USR-CITIZEN-001"
    run_payload = {
        "user_id": citizen_a,
        "deed_number": "DEED-TEST-9999",
        "dag_plot_number": "9044",
        "transferred_area_decimal": 12.5,
        "execution_date": "2026-03-15",
        "seller_nid": "OWN-DEMO-01",
        "buyer_nid": "OWN-DEMO-02",
        "khatian_number": "812",
    }
    result_a = verif_svc.verify_transaction(confirmed_fields=run_payload)
    vid_a = result_a["verification_id"]
    assert vid_a.startswith("VRF-")

    # 2. Run a verification for Citizen B
    citizen_b = "USR-CITIZEN-TEST-002"
    result_b = verif_svc.verify_transaction(confirmed_fields={
        "user_id": citizen_b,
        "deed_number": "DEED-TEST-8888",
        "dag_plot_number": "6792",
        "transferred_area_decimal": 8.0,
    })
    vid_b = result_b["verification_id"]

    # 3. Simulate process restart by destroying service instances and instantiating brand new ones
    del verif_svc
    del analytics_svc
    del db

    # Brand-new service instances connected to the same SQLite database
    new_db = LandGuardDatabase(db_path=isolated_db_path)
    new_analytics = AnalyticsService(db=new_db)
    new_verif_svc = VerificationService(db=new_db)

    # Check Citizen A history
    history_a = new_analytics.get_audit_history(user_id=citizen_a)
    assert len(history_a) >= 1
    vids_a = [h["verification_id"] for h in history_a]
    assert vid_a in vids_a
    assert vid_b not in vids_a

    # Check Citizen B history
    history_b = new_analytics.get_audit_history(user_id=citizen_b)
    assert len(history_b) >= 1
    vids_b = [h["verification_id"] for h in history_b]
    assert vid_b in vids_b
    assert vid_a not in vids_b

    # Check single record lookup from SQLite
    rec_a = new_verif_svc.get_verification_record(vid_a)
    assert rec_a is not None
    assert rec_a["verification_id"] == vid_a
    assert rec_a["deed_number"] == "DEED-TEST-9999"
    assert rec_a["transferred_area_decimal"] == 12.5


def test_complaints_and_cases_persistence_across_restart(isolated_db_path):
    """Verifies that citizen complaints and spawned cases persist and appear in Admin docket after restart."""
    db = LandGuardDatabase(db_path=isolated_db_path)
    notif_svc = NotificationService(db=db)
    case_svc = CaseService(db=db, create_notification_fn=notif_svc.create_notification)
    complaint_svc = ComplaintService(
        db=db,
        create_case_fn=case_svc.create_case,
        create_notification_fn=notif_svc.create_notification,
    )

    citizen_id = "USR-CITIZEN-001"
    complaint_data = {
        "title": "Dispute on Plot 9044 Double Disposition",
        "dag_plot_number": "9044",
        "deed_number": "DEED-DISPUTE-101",
        "category": "SUSPECTED_DOUBLE_SALE",
        "narrative_description": "Multiple sales detected on ancestral dag holding.",
    }
    created_comp = complaint_svc.create_complaint(citizen_id, complaint_data)
    comp_id = created_comp["complaint_id"]
    linked_case_id = created_comp["linked_case_id"]

    assert comp_id.startswith("CMP-")
    assert linked_case_id is not None
    assert linked_case_id.startswith("CASE-")

    # Simulate server shutdown / restart
    del db, notif_svc, case_svc, complaint_svc

    new_db = LandGuardDatabase(db_path=isolated_db_path)
    new_notif_svc = NotificationService(db=new_db)
    new_case_svc = CaseService(db=new_db, create_notification_fn=new_notif_svc.create_notification)
    new_complaint_svc = ComplaintService(
        db=new_db,
        create_case_fn=new_case_svc.create_case,
        create_notification_fn=new_notif_svc.create_notification,
    )

    # 1. Admin Case Docket must contain the case
    admin_cases = new_case_svc.list_cases()
    assert any(c["case_id"] == linked_case_id for c in admin_cases)

    case_detail = new_case_svc.get_case(linked_case_id)
    assert case_detail is not None
    assert case_detail["dag_plot_number"] == "9044"
    assert case_detail["sla_state"] in ["ON_TRACK", "APPROACHING_DEADLINE", "OVERDUE"]

    # 2. Citizen complaint must exist and retain initial timeline
    comp_detail = new_complaint_svc.get_complaint(comp_id)
    assert comp_detail is not None
    assert comp_detail["complaint_id"] == comp_id
    assert len(comp_detail["timeline"]) >= 1
    assert comp_detail["timeline"][0]["title"] == "Complaint Submitted"


def test_cross_role_case_update_and_citizen_notification(isolated_db_path):
    """Verifies that Admin updating case status/notes updates complaint timeline and notifies citizen in SQLite."""
    db = LandGuardDatabase(db_path=isolated_db_path)
    notif_svc = NotificationService(db=db)
    case_svc = CaseService(db=db, create_notification_fn=notif_svc.create_notification)
    complaint_svc = ComplaintService(
        db=db,
        create_case_fn=case_svc.create_case,
        create_notification_fn=notif_svc.create_notification,
    )

    citizen_id = "USR-CITIZEN-001"
    comp = complaint_svc.create_complaint(citizen_id, {
        "title": "Title Conflict Complaint",
        "dag_plot_number": "9044",
        "deed_number": "DEED-5555",
        "category": "TITLE_OVERLAP",
        "narrative_description": "Boundary dispute on north boundary.",
    })
    comp_id = comp["complaint_id"]
    case_id = comp["linked_case_id"]

    # Admin updates case status to UNDER_INVESTIGATION
    case_svc.update_case(case_id, {
        "status": "UNDER_INVESTIGATION",
        "assigned_by": "Senior Registrar M. Rahman",
    })

    # Admin adds investigator note
    case_svc.add_case_note(
        case_id=case_id,
        note_text="Field inspection scheduled for tomorrow morning.",
        author="Senior Registrar M. Rahman",
    )

    # Verify Complaint state in SQLite
    updated_comp = complaint_svc.get_complaint(comp_id)
    assert updated_comp["status"] == "UNDER_INVESTIGATION"
    timeline_titles = [t["title"] for t in updated_comp["timeline"]]
    assert "Status Updated: UNDER_INVESTIGATION" in timeline_titles
    assert "Investigator Note Added" in timeline_titles

    # Verify Notifications for Citizen in SQLite
    citizen_notifs = notif_svc.get_notifications(citizen_id)
    assert len(citizen_notifs) >= 2
    notif_messages = [n["message"] for n in citizen_notifs]
    assert any("UNDER_INVESTIGATION" in msg for msg in notif_messages)


def test_notification_id_synchronization_and_read_status(isolated_db_path):
    """Verifies that notification IDs match between memory and SQLite, and read status persists."""
    db = LandGuardDatabase(db_path=isolated_db_path)
    notif_svc = NotificationService(db=db)

    user_id = "USR-CITIZEN-001"
    notif = notif_svc.create_notification(
        recipient_user_id=user_id,
        title="Official Registry Notice",
        message="Your deed has been scheduled for verification.",
        link_url="/user/dashboard",
    )
    nid = notif["notification_id"]
    assert nid.startswith("NOTIF-")

    # Mark as read
    success = notif_svc.mark_notification_read(nid, user_id)
    assert success is True

    # Check persistence directly from SQLite connection
    db_notifs = db.get_notifications(user_id)
    matching = [n for n in db_notifs if n["notification_id"] == nid]
    assert len(matching) == 1
    assert matching[0]["is_read"] is True

    # Test batch mark all read
    notif_svc.create_notification(recipient_user_id=user_id, title="Alert 2", message="Msg 2")
    notif_svc.create_notification(recipient_user_id=user_id, title="Alert 3", message="Msg 3")
    count = notif_svc.mark_all_read(user_id)
    assert count >= 2

    unread = [n for n in db.get_notifications(user_id) if not n["is_read"]]
    assert len(unread) == 0


def test_live_complaint_api_endpoint(isolated_db_path):
    """Verifies GET /api/complaints/{id} and notification API endpoints via FastAPI TestClient."""
    db = LandGuardDatabase(db_path=isolated_db_path)
    service.rebind_database(db_path=isolated_db_path)

    client = TestClient(app)

    # 1. Login as citizen
    login_res = client.post("/api/auth/login", json={"email": "citizen@landguard.gov.bd", "password": "demo123"})
    assert login_res.status_code == 200

    # 2. File complaint
    comp_res = client.post("/api/complaints", json={
        "title": "API Test Complaint",
        "dag_plot_number": "9044",
        "deed_number": "DEED-API-1",
        "category": "SUSPECTED_DOUBLE_SALE",
        "narrative_description": "API live tracking verification test.",
    })
    assert comp_res.status_code == 200
    comp_id = comp_res.json()["complaint_id"]

    # 3. Query GET /api/complaints/{id}
    detail_res = client.get(f"/api/complaints/{comp_id}")
    assert detail_res.status_code == 200
    comp_json = detail_res.json()
    assert comp_json["complaint_id"] == comp_id
    assert len(comp_json["timeline"]) >= 1

    # 4. Check notifications endpoint
    notif_res = client.get("/api/notifications")
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert isinstance(notifs, list)
    assert len(notifs) >= 1

    # 5. Mark all notifications read
    read_all_res = client.post("/api/notifications/read-all")
    assert read_all_res.status_code == 200
    assert read_all_res.json()["success"] is True

    # Rebind back to operational database for server consistency
    service.rebind_database()
