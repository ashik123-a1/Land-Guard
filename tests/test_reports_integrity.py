"""Comprehensive test suite for LandGuard Verification Report & Document Integrity System.
Validates:
1. Binary PDF dossier generation with ReportLab, appropriate headers, and synthetic data disclaimers.
2. Dynamic QR code PNG generation embedding public verification links.
3. Sanitized public verification API & web endpoints with strict citizen PII masking.
4. Report lifecycle management (VALID, WITHDRAWN, SUPERSEDED, RE_REVIEW_REQUIRED) with RBAC,
   SQLite persistence, and immutable audit event logging.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app, service
from src.landguard_data.database import LandGuardDatabase

client = TestClient(app, follow_redirects=False)


@pytest.fixture(scope="module")
def admin_session_cookie():
    """Authenticates as Admin / Senior Registrar."""
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    cookie = res.cookies.get("landguard_session")
    assert cookie is not None
    return cookie


@pytest.fixture(scope="module")
def citizen_session_cookie():
    """Authenticates as Citizen."""
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    cookie = res.cookies.get("landguard_session")
    assert cookie is not None
    return cookie


def test_binary_pdf_report_generation():
    """GET /api/reports/pdf/{id} returns binary application/pdf with valid PDF header and disclaimers."""
    res = client.get("/api/reports/pdf/VRF-HIST-001")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert "Content-Disposition" in res.headers
    assert "LandGuard_Dossier_VRF-HIST-001.pdf" in res.headers["Content-Disposition"]

    content = res.content
    assert content.startswith(b"%PDF-")
    assert len(content) > 2000


def test_binary_pdf_report_unknown_id_returns_404():
    """Querying PDF for an unknown verification ID must return 404."""
    res = client.get("/api/reports/pdf/VRF-UNKNOWN-999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_dynamic_qr_code_generation():
    """GET /api/reports/qr/{id} generates a valid PNG QR code image."""
    res = client.get("/api/reports/qr/VRF-HIST-001")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    # PNG magic number: \x89PNG\r\n\x1a\n
    assert res.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(res.content) > 200


def test_sanitized_public_verification_json():
    """GET /api/reports/public/{id} masks citizen PII (NID and phone) and exposes truthful audit fields."""
    res = client.get("/api/reports/public/VRF-HIST-001")
    assert res.status_code == 200
    data = res.json()

    assert data["verification_id"] == "VRF-HIST-001"
    assert "deed_number" in data
    assert "dag_plot_number" in data
    assert "overall_status" in data
    assert "report_status" in data
    assert "sha256_hash" in data
    assert len(data["sha256_hash"]) == 64
    assert data["disclaimer"] == "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"

    # PII Protection verification
    assert "seller_nid_masked" in data
    assert "***" in data["seller_nid_masked"] or "****" in data["seller_nid_masked"]
    assert "buyer_nid_masked" in data
    assert "***" in data["buyer_nid_masked"] or "****" in data["buyer_nid_masked"]

    # Raw unmasked PII keys must not be present
    assert "phone" not in data
    assert "seller_nid" not in data
    assert "buyer_nid" not in data


def test_public_verification_html_page():
    """GET /verify/public/{id} serves a responsive, bilingual verification certificate page."""
    res = client.get("/verify/public/VRF-HIST-001")
    assert res.status_code == 200
    text = res.text

    assert "SYNTHETIC DEMO &mdash; NOT AN OFFICIAL DOCUMENT" in text or "SYNTHETIC DEMO" in text
    assert "LandGuard Statutory Verification Dossier" in text
    assert "VRF-HIST-001" in text
    assert "/api/reports/qr/VRF-HIST-001" in text
    assert "/api/reports/pdf/VRF-HIST-001" in text
    assert "Cryptographic Record SHA-256 Digest" in text


def test_public_verification_html_unknown_redirects_to_not_found():
    """Accessing public verification for an unknown ID redirects (303) to /not-found."""
    res = client.get("/verify/public/VRF-NONEXISTENT-999")
    assert res.status_code == 303
    assert res.headers["location"] == "/not-found"


def test_report_lifecycle_status_update_rbac():
    """Updating report lifecycle status requires Admin or Investigator privileges."""
    # 1. Anonymous forbidden
    res_anon = client.patch(
        "/api/reports/VRF-HIST-001/status",
        json={"status": "WITHDRAWN", "reason": "Test audit"},
    )
    assert res_anon.status_code == 401

    # 2. Citizen forbidden (403)
    login_res = client.post("/api/auth/demo-login?role=citizen")
    c_citizen = TestClient(app, cookies={"landguard_session": login_res.cookies["landguard_session"]}, follow_redirects=False)
    res_citizen = c_citizen.patch(
        "/api/reports/VRF-HIST-001/status",
        json={"status": "WITHDRAWN", "reason": "Test audit"},
    )
    assert res_citizen.status_code == 403


def test_report_lifecycle_transition_and_sqlite_persistence(admin_session_cookie):
    """Admin transitions report to WITHDRAWN; verifies SQLite persistence, public view, and PDF."""
    c_admin = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)

    # 1. Reject invalid status
    bad_res = c_admin.patch(
        "/api/reports/VRF-HIST-001/status",
        json={"status": "INVALID_STATE", "reason": "Typo in status"},
    )
    assert bad_res.status_code == 400

    # 2. Transition to WITHDRAWN
    withdraw_reason = "Administrative investigation confirmed fraudulent seller impersonation in 2006 volume."
    res = c_admin.patch(
        "/api/reports/VRF-HIST-001/status",
        json={"status": "WITHDRAWN", "reason": withdraw_reason},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["report_status"] == "WITHDRAWN"
    assert data["status_reason"] == withdraw_reason

    # 3. Verify SQLite verification_runs table has updated status
    db = LandGuardDatabase()
    run = db.get_verification_run("VRF-HIST-001")
    assert run is not None
    assert run.get("report_status") == "WITHDRAWN"
    assert run.get("status_reason") == withdraw_reason

    # 4. Verify SQLite audit trail contains event
    events = db.get_audit_events_for_target("VERIFICATION_REPORT", "VRF-HIST-001")
    assert len(events) >= 1
    latest_event = events[0]
    assert latest_event["action_type"] == "VERIFICATION_REPORT_STATUS_UPDATED"
    assert latest_event["details"]["new_status"] == "WITHDRAWN"

    # 5. Verify Public JSON endpoint reports WITHDRAWN
    pub_res = client.get("/api/reports/public/VRF-HIST-001")
    assert pub_res.status_code == 200
    assert pub_res.json()["report_status"] == "WITHDRAWN"
    assert pub_res.json()["status_reason"] == withdraw_reason

    # 6. Verify Public HTML certificate displays WITHDRAWN warning
    html_res = client.get("/verify/public/VRF-HIST-001")
    assert html_res.status_code == 200
    assert "CERTIFICATE FORMALLY WITHDRAWN" in html_res.text
    assert withdraw_reason in html_res.text

    # 7. Verify PDF generates with WITHDRAWN status
    pdf_res = client.get("/api/reports/pdf/VRF-HIST-001")
    assert pdf_res.status_code == 200
    assert pdf_res.content.startswith(b"%PDF-")

    # 8. Restore to VALID status
    restore_res = c_admin.patch(
        "/api/reports/VRF-HIST-001/status",
        json={"status": "VALID", "reason": "Audit review concluded and cleared."},
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["report_status"] == "VALID"


def test_formatted_html_report_route(admin_session_cookie, citizen_session_cookie):
    """GET /reports/{id} displays a human-readable HTML view with role-aware PII masking."""
    # 1. Anonymous / Citizen view: displays sanitized public certificate with masked PII
    res_anon = client.get("/reports/VRF-HIST-001")
    assert res_anon.status_code == 200
    assert "text/html" in res_anon.headers["content-type"]
    assert "VRF-HIST-001" in res_anon.text
    assert "SYNTHETIC DEMO" in res_anon.text
    assert "Download PDF Verification Report" in res_anon.text
    # PII is masked
    assert "seller_nid_masked" in res_anon.text or "***" in res_anon.text

    # 2. Admin view: displays administrative evidence report with full dossier
    c_admin = TestClient(app, cookies={"landguard_session": admin_session_cookie}, follow_redirects=False)
    res_admin = c_admin.get("/reports/VRF-HIST-001")
    assert res_admin.status_code == 200
    assert "text/html" in res_admin.headers["content-type"]
    assert "VRF-HIST-001" in res_admin.text
    assert "STATUTORY VERIFICATION REPORT" in res_admin.text
    assert "Print Verification Report" in res_admin.text
    assert "Download PDF" in res_admin.text


def test_raw_json_report_api_endpoint_preserved():
    """GET /api/reports/{id} is strictly preserved as a JSON API endpoint for external integrators."""
    res = client.get("/api/reports/VRF-HIST-001")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    data = res.json()
    assert isinstance(data, dict)
    assert data["report_id"] == "REP-VRF-HIST-001"
    assert "verification" in data
    assert "sha256_certificate_hash" in data
    assert len(data["sha256_certificate_hash"]) == 64

    # Unknown ID returns 404 JSON
    res_404 = client.get("/api/reports/VRF-NONEXISTENT-999")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_formatted_report_unknown_id_redirects_to_not_found():
    """Accessing /reports/{unknown_id} redirects to /not-found."""
    res = client.get("/reports/VRF-UNKNOWN-99999")
    assert res.status_code == 303
    assert res.headers["location"] == "/not-found"


def test_printable_verification_routes():
    """GET /reports/{id}/print and /verify/print/{id} render printable HTML view."""
    res1 = client.get("/reports/VRF-HIST-001/print")
    assert res1.status_code == 200
    assert "STATUTORY VERIFICATION REPORT" in res1.text
    assert "window.print()" in res1.text

    res2 = client.get("/verify/print/VRF-HIST-001")
    assert res2.status_code == 200
    assert "STATUTORY VERIFICATION REPORT" in res2.text


def test_qr_code_decoding_and_configurable_base_url():
    """Validates that QR code PNG decodes correctly and respects PUBLIC_BASE_URL environment variable."""
    import os
    from src.landguard_reports.qr_generator import generate_verification_qr, decode_verification_qr

    # 1. Default fallback decoding
    qr_bytes = generate_verification_qr("VRF-HIST-001", base_url="http://127.0.0.1:8000")
    decoded_url = decode_verification_qr(qr_bytes)
    assert decoded_url == "http://127.0.0.1:8000/verify/public/VRF-HIST-001"

    # 2. Configured PUBLIC_BASE_URL environment variable
    custom_domain = "https://landguard.mohpw.gov.bd"
    os.environ["PUBLIC_BASE_URL"] = custom_domain
    try:
        qr_bytes_env = generate_verification_qr("VRF-HIST-001")
        decoded_url_env = decode_verification_qr(qr_bytes_env)
        assert decoded_url_env == f"{custom_domain}/verify/public/VRF-HIST-001"
    finally:
        os.environ.pop("PUBLIC_BASE_URL", None)

    # 3. Reject untrusted arbitrary Host header
    untrusted_bytes = generate_verification_qr("VRF-HIST-001", base_url="https://evil-phishing.com")
    decoded_untrusted = decode_verification_qr(untrusted_bytes)
    assert decoded_untrusted == "http://localhost:8000/verify/public/VRF-HIST-001"


def test_admin_and_printable_report_contains_embedded_qr_code(admin_session_cookie):
    """Ensures HTML certificate and printable report views cleanly embed the authenticity QR code."""
    v_id = "VRF-HIST-001"
    
    # 1. Admin report view (/admin/reports/{id})
    res_admin = client.get(f"/admin/reports/{v_id}", cookies={"landguard_session": admin_session_cookie})
    assert res_admin.status_code == 200
    assert f"/api/reports/qr/{v_id}" in res_admin.text
    assert "Authenticity QR" in res_admin.text
    assert "SHA-256 Cryptographic Evidence Integrity Hash:" in res_admin.text

    # 2. View Report route as Admin (/reports/{id})
    res_rep = client.get(f"/reports/{v_id}", cookies={"landguard_session": admin_session_cookie})
    assert res_rep.status_code == 200
    assert f"/api/reports/qr/{v_id}" in res_rep.text

    # 3. Printable route (/verify/print/{id})
    res_print = client.get(f"/verify/print/{v_id}")
    assert res_print.status_code == 200
    assert f"/api/reports/qr/{v_id}" in res_print.text


def test_pdf_report_contains_decodable_embedded_qr_code():
    """Extracts embedded image from binary PDF dossier and verifies it decodes to the canonical public verification URL."""
    import pymupdf
    from src.landguard_reports.qr_generator import decode_verification_qr

    v_id = "VRF-HIST-001"
    pdf_res = client.get(f"/api/reports/pdf/{v_id}")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"

    doc = pymupdf.open(stream=pdf_res.content, filetype="pdf")
    assert len(doc) >= 1

    decoded_urls = []
    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_img = doc.extract_image(xref)
            img_bytes = base_img["image"]
            try:
                decoded = decode_verification_qr(img_bytes)
                if decoded:
                    decoded_urls.append(decoded)
            except Exception:
                pass

    assert len(decoded_urls) >= 1, "Failed to decode any QR code image embedded in PDF"
    assert any(f"/verify/public/{v_id}" in u for u in decoded_urls), f"Expected /verify/public/{v_id} in {decoded_urls}"


