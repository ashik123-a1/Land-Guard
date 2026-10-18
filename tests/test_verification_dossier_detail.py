"""Comprehensive automated test suite for the LandGuard Verification Dossier Detail page.
Validates:
1. Investigator workspace rendering with verdict summary, 2-column deed & cadastral linkage,
   4 structured evidence signal modules, and authoritative statutory rules log.
2. Handling of missing/unindexed cadastral parcels and truthful non-exaggerated claims for clean titles.
3. Official Registrar / Investigator Determination workflow with RBAC enforcement, input validation,
   server-side persistence, and immutable audit logging in SQLite.
4. Escalation to formal investigation case with duplicate prevention and live linked case badge.
5. Printable verification report rendering with mandatory synthetic data disclaimers and SHA-256 integrity hash.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app, service
from src.landguard_data.database import LandGuardDatabase

client = TestClient(app, follow_redirects=False)


@pytest.fixture(scope="module")
def admin_session_cookie():
    """Authenticates as Admin / Senior Registrar and returns session cookie."""
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    cookie = res.cookies.get("landguard_session")
    assert cookie is not None
    return cookie


@pytest.fixture(scope="module")
def citizen_session_cookie():
    """Authenticates as Citizen and returns session cookie."""
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    cookie = res.cookies.get("landguard_session")
    assert cookie is not None
    return cookie


def test_unauthenticated_dossier_detail_redirects_to_login():
    """Unauthenticated access to verification dossier detail must redirect (303) to /login."""
    res = client.get("/admin/verifications/VRF-HIST-001")
    assert res.status_code == 303
    assert "/login?redirect=/admin/verifications/VRF-HIST-001" in res.headers["location"]


def test_citizen_dossier_detail_access_denied(citizen_session_cookie):
    """Citizens attempting to access investigator verification dossier must be blocked (303) to /access-denied."""
    c = TestClient(app, cookies={"landguard_session": citizen_session_cookie}, follow_redirects=False)
    res = c.get("/admin/verifications/VRF-HIST-001")
    assert res.status_code == 303
    assert res.headers["location"] == "/access-denied"


def test_dossier_detail_unknown_id_redirects_to_not_found(admin_session_cookie):
    """Querying an unknown verification ID must redirect to /not-found."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    res = c.get("/admin/verifications/VRF-UNKNOWN-999999")
    assert res.status_code == 303
    assert res.headers["location"] == "/not-found"


def test_dossier_detail_page_renders_all_components(admin_session_cookie):
    """Verified dossier renders compact verdict summary, 2-column linkage, 4 evidence modules, and rules log."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    res = c.get("/admin/verifications/VRF-HIST-001?lang=en")
    assert res.status_code == 200
    html = res.text

    # Top Controls
    assert "Back to Verification Queue" in html
    assert "Print Verification Report" in html
    assert "Export Dossier (JSON)" in html
    assert "/api/reports/html/VRF-HIST-001" in html
    assert "/api/reports/VRF-HIST-001" in html

    # 1. Compact Verdict Banner & Disclaimers
    assert "ALGORITHMIC VERIFICATION RESULT" in html
    assert "DOSSIER #VRF-HIST-001" in html
    assert "Recommended Action:" in html
    assert "Algorithmic Gate" in html
    assert "XGBoost Risk" in html
    assert "Payload Hash" in html
    assert "Statutory Verification Scope &amp; Legal Disclaimers" in html
    assert "Low algorithmic risk is not proof of clean legal title" in html

    # 2. Two-Column Deed & Cadastral Linkage Card
    assert "Deed Conveyance Record" in html
    assert "Cadastral Registry Index" in html
    assert "Deed Reference" in html
    assert "Execution Date" in html
    assert "Claimed Dag Plot" in html
    assert "Transferred Area" in html
    assert "Primary Vendor" in html
    assert "Primary Transferee" in html
    assert "Cadastral Parcel ID" in html
    assert "Recorded Parcel Capacity" in html
    assert "Capacity Post-Transfer" in html

    # 3. Structured Evidence Panel (4 distinct modules)
    assert "Multi-Modal Evidence &amp; Verification Signals" in html
    assert "Supervised ML Risk Signal" in html
    assert "Decision Threshold: &tau; = 0.35" in html
    assert "Non-Oracle Model Signal" in html
    assert "Computer Vision Anomaly Analysis" in html
    assert "Visual Seal &amp; Signature Detection" in html
    assert "Sub-Registry Seal" in html
    assert "Registrar Signature" in html
    assert "Audit Record Payload SHA-256" in html
    assert "PAYLOAD INTEGRITY HASH" in html
    assert "copyDigest()" in html

    # 4. Authoritative Statutory Rules Evidence Log
    assert "Authoritative Statutory Rules Evidence Log" in html
    assert "No Statutory Contradictions Triggered" in html

    # Verify flagged case renders statutory citations and procedural next steps
    res_flagged = c.get("/admin/verifications/VRF-HIST-002?lang=en")
    assert res_flagged.status_code == 200
    assert "Statutory Authority:" in res_flagged.text
    assert "Procedural Next Step:" in res_flagged.text

    # 5. Authorized Review Workspace
    assert "Authorized Review Workspace" in html
    assert "Approve Standard" in html
    assert "Request Archives" in html
    assert "Field Inspection" in html
    assert "Refer to AC (Land)" in html
    assert "Record Official Determination" in html

    # Mandatory Synthetic Disclaimer
    assert "SYNTHETIC DEMO — NOT AN OFFICIAL LEGAL TITLE CERTIFICATE" in html


def test_clean_title_dossier_truthful_rules_statement(admin_session_cookie):
    """When a transaction has no flagged rules, the log displays truthful, non-exaggerated finding."""
    # Run a verified clean transaction from canonical dataset
    clean_verif = service.verify_transaction(
        confirmed_fields={
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 8.38,
            "execution_date": "2006-11-11",
            "seller_nid": "OWN-11CE5DD2",
            "buyer_nid": "OWN-CE177B4E",
            "previous_deed_ref": "DEED-2001-35323",
            "mutation_case_no": "MUT-2006-5364/Rupsha",
            "consideration_bdt": 955246.39,
            "khatian_number": "1420",
        }
    )
    assert clean_verif["overall_status"] == "CLEAR_FOR_STANDARD_PROCESSING"
    assert len(clean_verif["rules_triggered"]) == 0
    v_id = clean_verif["verification_id"]

    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    res = c.get(f"/admin/verifications/{v_id}?lang=en")
    assert res.status_code == 200
    html = res.text

    assert "No Statutory Contradictions Triggered" in html
    assert "No configured statutory contradictions triggered during algorithmic evaluation" in html
    # Must NOT claim blanket 16 statutory predicates satisfied
    assert "All 16 statutory predicates satisfied" not in html


def test_human_determination_api_recording_and_sqlite_persistence(admin_session_cookie):
    """Authorized officer records a determination; verifies SQLite audit event and record update."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    target_id = "VRF-HIST-001"

    payload = {
        "decision": "REQUEST_ARCHIVES",
        "reason": "Referenced Book 1 volume 1971 appears faded in microfiche. Requested senior archivist manual inspection.",
    }
    res = c.post(f"/api/verifications/{target_id}/decision", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["determination"]["decision"] == "REQUEST_ARCHIVES"
    assert "Referenced Book 1 volume 1971" in data["determination"]["reason"]

    # Verify updated record reflected in subsequent GET request
    detail_res = c.get(f"/admin/verifications/{target_id}")
    assert detail_res.status_code == 200
    assert "REQUEST_ARCHIVES" in detail_res.text
    assert "Referenced Book 1 volume 1971" in detail_res.text

    # Verify SQLite audit log contains the event
    db = LandGuardDatabase()
    events = db.get_recent_audit_events(limit=20)
    matching = [
        e for e in events
        if e.get("target_id") == target_id and e.get("action_type") == "VERIFICATION_DETERMINATION_RECORDED"
    ]
    assert len(matching) >= 1
    assert matching[0]["details"]["decision"] == "REQUEST_ARCHIVES"


def test_human_determination_api_rbac_enforcement(citizen_session_cookie):
    """Citizens and unauthenticated requests must be blocked from recording determinations."""
    target_id = "VRF-HIST-001"
    payload = {"decision": "APPROVE_STANDARD", "reason": "Citizen attempt to override finding"}

    # 1. Unauthenticated request -> 403 Forbidden
    c_anon = TestClient(app, follow_redirects=False)
    res_anon = c_anon.post(f"/api/verifications/{target_id}/decision", json=payload)
    assert res_anon.status_code == 403

    # 2. Citizen request -> 403 Forbidden
    c_cit = TestClient(app, cookies={"landguard_session": citizen_session_cookie}, follow_redirects=False)
    res_cit = c_cit.post(f"/api/verifications/{target_id}/decision", json=payload)
    assert res_cit.status_code == 403


def test_human_determination_api_validation(admin_session_cookie):
    """Blank reason or invalid decision type returns 400 Bad Request."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    target_id = "VRF-HIST-001"

    # Missing reason
    res_blank = c.post(f"/api/verifications/{target_id}/decision", json={"decision": "APPROVE_STANDARD", "reason": "   "})
    assert res_blank.status_code == 400
    assert "Statutory justification and notes are required" in res_blank.json()["detail"]

    # Invalid decision type
    res_invalid = c.post(f"/api/verifications/{target_id}/decision", json={"decision": "ILLEGAL_DECISION", "reason": "Some note"})
    assert res_invalid.status_code == 400
    assert "Invalid decision" in res_invalid.json()["detail"]


def test_case_escalation_and_duplicate_prevention(admin_session_cookie):
    """Escalating a dossier opens a case; re-escalating returns the existing case without duplicate."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    target_id = "VRF-HIST-002"

    payload = {
        "title": "Investigation: Double Sale on Plot #7025",
        "deed_number": "DEED-2017-55696",
        "dag_plot_number": "7025",
        "verification_id": target_id,
        "priority": "HIGH",
        "assigned_officer": "Inspector S. Karim",
        "statutory_finding": "CONFIRMED_INCONSISTENCY",
        "ml_risk_score": 0.945,
        "evidence_summary": "Initial escalation from dossier detail.",
        "initial_note": "Docket created for double disposition.",
    }

    # 1. First escalation
    res1 = c.post("/api/cases", json=payload)
    assert res1.status_code == 200
    case1 = res1.json()
    case_id = case1["case_id"]
    assert case_id.startswith("CASE-")

    # 2. Second escalation with identical verification_id must detect duplicate
    res2 = c.post("/api/cases", json=payload)
    assert res2.status_code == 200
    case2 = res2.json()
    assert case2["case_id"] == case_id
    assert case2.get("is_duplicate") is True

    # 3. Dossier detail page now shows the linked case badge
    detail_res = c.get(f"/admin/verifications/{target_id}?lang=en")
    assert detail_res.status_code == 200
    assert f"Open Linked Case ({case_id})" in detail_res.text
    assert f"/admin/cases/{case_id}" in detail_res.text


def test_printable_verification_report_has_synthetic_disclaimer(admin_session_cookie):
    """Printable verification report endpoint contains mandatory synthetic disclaimer and certificate hash."""
    target_id = "VRF-HIST-001"

    # HTML Printable Report
    res_html = client.get(f"/api/reports/html/{target_id}?lang=en")
    assert res_html.status_code == 200
    assert "LANDGUARD AI — STATUTORY VERIFICATION REPORT" in res_html.text
    assert "SYNTHETIC DEMO" in res_html.text
    assert "NOT AN OFFICIAL LEGAL TITLE CERTIFICATE" in res_html.text
    assert "SHA-256 Cryptographic Evidence Integrity Hash" in res_html.text

    # Raw JSON Dossier
    res_json = client.get(f"/api/reports/{target_id}")
    assert res_json.status_code == 200
    data = res_json.json()
    assert "sha256_certificate_hash" in data
    assert len(data["sha256_certificate_hash"]) == 64
    assert "SYNTHETIC DEMO" in data["watermark_notice"]


def test_seal_and_signature_detection_terminology(admin_session_cookie):
    """Seal and signature evidence strictly separates visual detection from authenticity verification."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)

    # 1. Inspect seeded record where detector detected visual seal & signature
    res = c.get("/admin/verifications/VRF-HIST-001")
    assert res.status_code == 200
    html = res.text

    # Title & Subtitle
    assert "Visual Seal &amp; Signature Detection" in html
    assert "Visual Presence Detection" in html

    # Status labels must be DETECTED, never "AUTHENTICITY VERIFIED" or "VERIFIED"
    assert "DETECTED" in html
    assert "AUTHENTICITY VERIFIED" not in html
    assert "Registrar Signature</span>" in html

    # Must contain explicit visual detection disclaimer
    assert "Visual Detection Only:" in html
    assert "legal authenticity have not been established" in html

    # 2. Test a transaction without an image where CV check was NOT run -> NOT CHECKED
    uninspected = service.verify_transaction(
        confirmed_fields={
            "deed_number": "DEED-TEST-UNINSPECTED",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 5.0,
        },
        image_path=None,
    )
    v_id = uninspected["verification_id"]
    res_uninspected = c.get(f"/admin/verifications/{v_id}")
    assert res_uninspected.status_code == 200
    html_un = res_uninspected.text
    assert "NOT CHECKED" in html_un


def test_sha256_audit_record_payload_wording(admin_session_cookie):
    """SHA-256 digest is honestly labeled as Audit Record Payload Hash and explains consistency checking."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    res = c.get("/admin/verifications/VRF-HIST-001")
    assert res.status_code == 200
    html = res.text

    assert "Audit Record Payload SHA-256" in html
    assert "PAYLOAD INTEGRITY HASH" in html
    assert "Canonical Audit Record Payload Digest:" in html
    assert "Consistency Verification:" in html
    assert "Verifies data payload consistency against recorded audit history" in html
    assert "does not prove legal title or physical document unalterability" in html


def test_multiple_determination_history_preservation(admin_session_cookie):
    """Consecutive determinations on the same dossier are preserved in SQLite and rendered as history."""
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)

    # Create fresh verification so history starts at 0
    fresh_verif = service.verify_transaction(
        confirmed_fields={
            "deed_number": "DEED-TEST-HIST-001",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 5.0,
        }
    )
    target_id = fresh_verif["verification_id"]

    # Step 1: Submit first determination
    payload_1 = {
        "decision": "REQUEST_ARCHIVES",
        "reason": "Initial review: Volume 1968 requires physical archivist lookup.",
    }
    res_1 = c.post(f"/api/verifications/{target_id}/decision", json=payload_1)
    assert res_1.status_code == 200

    # Step 2: Submit second determination (updating decision)
    payload_2 = {
        "decision": "FLAG_FOR_FIELD_INSPECTION",
        "reason": "Archivist confirmed ledger entry, but boundary stone position is contested. Escalated to field survey.",
    }
    res_2 = c.post(f"/api/verifications/{target_id}/decision", json=payload_2)
    assert res_2.status_code == 200

    # Step 3: Fetch detail page and verify both determinations exist in history
    res_detail = c.get(f"/admin/verifications/{target_id}")
    assert res_detail.status_code == 200
    html = res_detail.text

    # Active determination card shows newest decision
    assert "FLAG_FOR_FIELD_INSPECTION" in html
    assert "boundary stone position is contested" in html

    # Determination history section displays both
    assert "Prior Determination History (2 Events)" in html
    assert "Volume 1968 requires physical archivist lookup" in html
    assert "ACTIVE" in html


def test_honest_data_fallbacks_no_invented_values(admin_session_cookie):
    """When parcel or deed attributes are missing, the page renders 'Not available' without inventing fake data."""
    # Create verification for an unindexed plot with no prior deed reference
    unindexed = service.verify_transaction(
        confirmed_fields={
            "deed_number": "DEED-TEST-UNINDEXED",
            "dag_plot_number": "99999",  # unindexed plot
            "transferred_area_decimal": 12.0,
            "previous_deed_ref": "",     # intentionally blank
        }
    )
    # Manually remove mock fallback fields from the unindexed parcel to test template robustness
    unindexed["cadastral_parcel"] = None
    unindexed["previous_deed_ref"] = None

    v_id = unindexed["verification_id"]
    c = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    res = c.get(f"/admin/verifications/{v_id}")
    assert res.status_code == 200
    html = res.text

    # Must display Not available honestly
    assert "Not available" in html
    # Must NOT invent hardcoded fallback land class
    assert "Nal (Agricultural)" not in html

