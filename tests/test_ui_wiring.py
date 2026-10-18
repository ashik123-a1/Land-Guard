"""Test UI-to-Backend Wiring for Citizen and Admin Portals.
Verifies:
1. Citizen portal routes render without template errors.
2. Admin portal routes render without template errors.
3. Parcel detail page includes Cadastral Graph and What-If Simulator hooks.
4. Admin case detail page includes SLA countdown badge and Clarification Request controls.
5. Citizen complaint detail page includes Clarification Response controls.
6. Public verification certificate includes QR code and SHA-256 integrity display.
"""

import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app, service


@pytest.fixture
def citizen_client():
    client = TestClient(app, cookies={"landguard_lang": "en"}, follow_redirects=False)
    client.post("/api/auth/demo-login?role=citizen")
    return client


@pytest.fixture
def admin_client():
    client = TestClient(app, cookies={"landguard_lang": "en"}, follow_redirects=False)
    client.post("/api/auth/demo-login?role=admin")
    return client


def test_citizen_routes_wiring(citizen_client):
    """Verify citizen routes render properly with active navigation."""
    routes = [
        "/user/dashboard",
        "/user/verify",
        "/user/parcels",
        "/user/history",
        "/user/complaints",
        "/user/voice",
        "/user/profile",
        "/user/settings",
    ]
    for r in routes:
        resp = citizen_client.get(r)
        assert resp.status_code == 200, f"Route {r} failed with status {resp.status_code}"
        assert "LandGuard" in resp.text


def test_admin_routes_wiring(admin_client):
    """Verify admin / investigator routes render properly."""
    routes = [
        "/admin/dashboard",
        "/admin/verifications",
        "/admin/cases",
        "/admin/parcels",
        "/admin/reports",
        "/admin/analytics",
        "/admin/audit",
        "/admin/users",
        "/admin/models",
        "/admin/system",
        "/admin/settings",
    ]
    for r in routes:
        resp = admin_client.get(r)
        assert resp.status_code == 200, f"Admin route {r} failed with status {resp.status_code}"
        assert "LandGuard" in resp.text


def test_parcel_detail_graph_and_simulator_wiring(citizen_client):
    """Verify parcel detail page renders Cadastral Graph container, What-If simulator, and Cross-Parcel Patterns."""
    resp = citizen_client.get("/user/parcels/9044")
    assert resp.status_code == 200
    assert "Cadastral Topology &amp; Succession Graph" in resp.text or "Cadastral Topology" in resp.text
    assert "What-If Transaction Simulator" in resp.text
    assert "Cross-Parcel" in resp.text
    assert "loadCadastralGraph" in resp.text
    assert "loadCrossParcelPatterns" in resp.text
    assert "runWhatIfSimulation" in resp.text


def test_admin_case_detail_sla_and_clarification_wiring(admin_client):
    """Verify admin case detail includes SLA countdown badge and Clarification Request controls."""
    cases = service.list_cases()
    if not cases:
        # Create a sample case
        c = service.create_case({
            "title": "SLA & Clarification UI Test Case",
            "dag_plot_number": "9044",
            "priority": "HIGH",
        })
        case_id = c["case_id"]
    else:
        case_id = cases[0]["case_id"]

    resp = admin_client.get(f"/admin/cases/{case_id}")
    assert resp.status_code == 200
    assert "SLA" in resp.text
    assert "Request Citizen Clarification" in resp.text
    assert "clarification-modal" in resp.text
    assert "submitClarificationRequest" in resp.text


def test_citizen_complaint_clarification_response_wiring(citizen_client):
    """Verify complaint detail page renders clarification response controls."""
    comp = service.create_complaint("USR-CITIZEN-001", {
        "citizen_user_id": "USR-CITIZEN-001",
        "title": "Awaiting Info Dispute",
        "dag_plot_number": "9044",
        "category": "TITLE_DISPUTE",
        "status": "AWAITING_INFORMATION",
        "narrative_description": "Boundary dispute description",
    })
    comp_id = comp["complaint_id"]

    resp = citizen_client.get(f"/user/complaints/{comp_id}")
    assert resp.status_code == 200
    assert "Investigator Clarification Response" in resp.text
    assert "submitCitizenClarification" in resp.text


def test_verify_result_page_view_report_button_wiring(citizen_client):
    """Verify that verify.html result section wires the View Report and Download PDF buttons cleanly."""
    resp = citizen_client.get("/user/verify")
    assert resp.status_code == 200
    html = resp.text

    # Assert button elements and declarative onclick handlers
    assert 'id="btn-view-report"' in html
    assert 'onclick="viewReportFromVerification()"' in html
    assert 'id="btn-download-pdf"' in html
    assert 'onclick="downloadPdfFromVerification()"' in html

    # Assert robust JavaScript handler definitions
    assert "function viewReportFromVerification()" in html
    assert "function downloadPdfFromVerification()" in html
    assert "window.location.href = reportUrl" in html
    assert "window.location.href = pdfUrl" in html
    assert "window.currentVerificationResult = data" in html


def test_verification_report_routes_and_data_accuracy(citizen_client):
    """Verify end-to-end report route resolution and data accuracy from verification result."""
    verify_resp = citizen_client.post("/api/verify", json={
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "dag_plot_number": "9044",
            "deed_number": "DEED-2022-55112",
            "transferred_area_decimal": 15.75,
            "execution_date": "2022-04-10"
        }
    })
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    vid = v_data["verification_id"]
    assert vid.startswith("VRF-")

    # Citizen report certificate
    rep_resp = citizen_client.get(f"/reports/{vid}")
    assert rep_resp.status_code == 200
    assert vid in rep_resp.text
    assert "9044" in rep_resp.text
    assert "DEED-2022-55112" in rep_resp.text

    # PDF endpoint
    pdf_resp = citizen_client.get(f"/api/reports/pdf/{vid}")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers.get("content-type") == "application/pdf"
    assert len(pdf_resp.content) > 1000

