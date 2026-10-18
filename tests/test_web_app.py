"""Integration tests for LandGuard Web Application endpoints.
Tests UI rendering, health check, sample list, file upload validation,
bilingual OCR pipeline, statutory rule evaluation, ML scoring, and audit history.
"""

import os
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.landguard_web.app import app

client = TestClient(app)


def test_index_page_contains_banner_and_controls():
    """Verify that the landing page loads and contains mandatory synthetic demo banners."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "সিন্থেটিক ডেমো" in html or "SYNTHETIC DEMO" in html
    assert "ল্যান্ডগার্ড" in html or "LandGuard" in html

    # Also verify English request with explicit query parameter
    res_en = client.get("/?lang=en")
    assert res_en.status_code == 200
    html_en = res_en.text
    assert "Step 1: Document Ingestion" in html_en
    assert "Step 2: Human-in-the-Loop Confirmation" in html_en
    assert "Step 3 & 4: Statutory Verification" in html_en


def test_health_check_endpoint():
    """Verify that health check reports status and synthetic disclaimer."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["xgb_model_ready"] is True
    assert data["indexed_parcels"] > 0
    assert "SYNTHETIC DEMO" in data["disclaimer"]


def test_sample_cases_list():
    """Verify sample cases API returns curated evaluation scenarios."""
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) >= 6
    case_ids = {s["case_id"] for s in samples}
    assert "DEMO-CLEAN" in case_ids
    assert "DEMO-AREA-EXCESS" in case_ids
    assert "DEMO-ALTERED-PLOT" in case_ids
    assert "DEMO-DOUBLE-SALE" in case_ids
    assert "DEMO-MISSING-ARCHIVE" in case_ids
    assert "DEMO-VISUAL-TAMPERING" in case_ids


def test_upload_validation_rejects_invalid_extension():
    """Verify that upload rejects unsupported file extensions with 400 Bad Request."""
    fake_payload = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    response = client.post(
        "/api/upload",
        files={"file": ("malicious.exe", fake_payload, "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


def test_upload_and_ocr_extraction_on_synthetic_image():
    """Verify upload and OCR parsing on a synthetic test document."""
    # Create simple valid test image in memory
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/upload",
        files={"file": ("test_doc.png", buf, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "field_confidences" in data
    assert "deed_number" in data["field_confidences"]
    assert "dag_plot_number" in data["field_confidences"]
    assert "cv_preview" in data


def test_verification_clean_deed():
    """Verify clean legitimate deed routes to CLEAR_FOR_STANDARD_PROCESSING with low risk score."""
    payload = {
        "confirmed_fields": {
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
        },
        "image_path": "data/full/images/IMG-24DCC9AE.png",
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "CLEAR_FOR_STANDARD_PROCESSING"
    assert data["rule_engine_flagged"] is False
    assert len(data["rules_triggered"]) == 0
    assert data["ml_risk_score"] < 0.35
    assert "PROCEED_WITH_STANDARD_REVIEW" in data["recommended_action"]


def test_verification_area_excess_statutory_contradiction():
    """Verify area excess deed routes to CONFIRMED_INCONSISTENCY."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2012-85693",
            "dag_plot_number": "9262",
            "transferred_area_decimal": 203.89,  # exceeds parcel area 87.25
            "execution_date": "2012-05-18",
            "seller_nid": "OWN-8B4D3063",
            "buyer_nid": "OWN-BUYER-02",
            "previous_deed_ref": "DEED-2005-20185",
            "mutation_case_no": "MUT-2012-2083/Sitakunda",
            "consideration_bdt": 15500000.0,
        },
        "image_path": "data/full/images/IMG-8B4D3063.png",
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "CONFIRMED_INCONSISTENCY"
    assert data["rule_engine_flagged"] is True
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_AREA_EXCEEDS_CAPACITY" in rule_codes
    assert "HOLD_FOR_STATUTORY_VERIFICATION" in data["recommended_action"]


def test_verification_unindexed_pre1972_routes_to_missing_evidence():
    """Verify unindexed pre-1972 reference routes to MISSING_EVIDENCE, not fraud."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2013-52068",
            "dag_plot_number": "9289",
            "transferred_area_decimal": 11.58,
            "execution_date": "2013-07-23",
            "seller_nid": "OWN-76EB16AC",
            "buyer_nid": "OWN-87924578",
            "previous_deed_ref": "UNINDEXED_PRE1972_VOLUME_189",
            "mutation_case_no": "MUT-2013-1845/Keraniganj",
            "consideration_bdt": 1646073.97,
        },
        "image_path": "data/targeted_expansion/images/IMG-EXP-0001.png",
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "MISSING_EVIDENCE"
    assert any(r["category"] == "MISSING_EVIDENCE" for r in data["rules_triggered"])
    assert "REQUEST_MISSING_RECORDS" in data["recommended_action"]


def test_verification_visual_tampering_detected():
    """Verify visual paste-over seam is detected by CV and triggers statutory finding."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2021-65260",
            "dag_plot_number": "5235",
            "transferred_area_decimal": 49.50,
            "execution_date": "2021-08-28",
            "seller_nid": "OWN-ADC08EC2",
            "buyer_nid": "OWN-C796273C",
            "previous_deed_ref": "DEED-2017-81623",
            "mutation_case_no": "MUT-2021-7367/Hathazari",
            "consideration_bdt": 6649816.61,
        },
        "image_path": "data/targeted_expansion/images/IMG-EXP-0013.png",
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["cv_evidence"]["visual_anomaly_detected"] is True
    assert data["cv_evidence"]["visual_anomaly_score"] > 0.70
    assert data["overall_status"] == "CONFIRMED_INCONSISTENCY"
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_VISUAL_TAMPERING_DETECTED" in rule_codes


def test_audit_history_and_officer_diff_tracking():
    """Verify that officer edits are tracked in diff and history is logged and clearable."""
    original_ocr = {
        "deed_number": "DEED-2006-18946",
        "dag_plot_number": "9040",  # OCR read 9040 with misread digit
    }
    confirmed = {
        "deed_number": "DEED-2006-18946",
        "dag_plot_number": "9044",  # Officer corrected to 9044
        "transferred_area_decimal": 8.38,
        "execution_date": "2006-11-11",
        "seller_nid": "OWN-11CE5DD2",
        "buyer_nid": "OWN-CE177B4E",
        "previous_deed_ref": "DEED-2001-35323",
        "mutation_case_no": "MUT-2006-5364/Rupsha",
    }
    response = client.post(
        "/api/verify",
        json={
            "confirmed_fields": confirmed,
            "original_ocr_fields": original_ocr,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["field_edits_by_user"]) >= 1
    diff = next(d for d in data["field_edits_by_user"] if d["field"] == "dag_plot_number")
    assert diff["ocr_raw_value"] == "9040"
    assert diff["confirmed_value"] == "9044"

    # Check history endpoint
    h_res = client.get("/api/history")
    assert h_res.status_code == 200
    history = h_res.json()
    assert len(history) >= 1
    assert history[0]["verification_id"] == data["verification_id"]

    # Clear history
    c_res = client.post("/api/history/clear")
    assert c_res.status_code == 200
    assert len(client.get("/api/history").json()) == 0


def test_dashboard_stats_endpoint():
    """Verify that dashboard statistics endpoint returns truthful dataset and model metrics."""
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert "dataset" in data
    assert data["dataset"]["total_canonical_records"] == 100000
    assert data["dataset"]["total_parcels"] == 10000
    assert data["dataset"]["total_khatians"] == 30000
    assert data["dataset"]["total_transactions"] == 25000
    assert data["dataset"]["total_scenarios"] == 2500
    assert data["dataset"]["fraud_scenarios"] == 1664
    assert data["dataset"]["legitimate_scenarios"] == 836

    assert "model_performance" in data
    assert data["model_performance"]["accuracy"] == 0.982
    assert data["model_performance"]["recall"] == 0.9940
    assert data["model_performance"]["features_count"] == 19
    assert data["model_performance"]["status"] in ["ONLINE", "FALLBACK"]

    assert "session" in data
    assert data["session"]["indexed_plots"] > 0


def test_parcel_search_and_detail_endpoints():
    """Verify searching parcels and retrieving detailed parcel card with chain of title."""
    # Search for plot 9044
    res = client.get("/api/parcels/search?q=9044")
    assert res.status_code == 200
    parcels = res.json()
    assert len(parcels) >= 1
    assert any(str(p["dag_plot_number"]) == "9044" for p in parcels)

    # Get details for plot 9044
    d_res = client.get("/api/parcels/9044")
    assert d_res.status_code == 200
    detail = d_res.json()
    assert "parcel" in detail
    assert "chain_of_title" in detail
    assert len(detail["chain_of_title"]) >= 4  # CS, SA, RS, BS
    assert "history_transactions" in detail
    assert "mutations" in detail
    assert "tax_status" in detail


def test_case_management_workflow():
    """Verify investigator case lifecycle: list, create, view, update, and add note."""
    # Authenticate as Admin/Investigator for protected case management endpoints
    auth_res = client.post("/api/auth/demo-login?role=admin")
    assert auth_res.status_code == 200

    # List initial cases
    res = client.get("/api/cases")
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) >= 2  # Seeded default cases

    # Create a new case
    new_payload = {
        "title": "Investigation: Area Excess on Plot 9262",
        "deed_number": "DEED-2012-85693",
        "dag_plot_number": "9262",
        "priority": "HIGH",
        "assigned_officer": "Registrar Hasan",
        "statutory_finding": "CONFIRMED_INCONSISTENCY",
        "ml_risk_score": 0.975,
        "evidence_summary": "Claimed transferred area 203.89 decimal exceeds parcel capacity 87.25 decimal.",
        "initial_note": "Case opened for manual ledger verification.",
    }
    c_res = client.post("/api/cases", json=new_payload)
    assert c_res.status_code == 200
    created = c_res.json()
    case_id = created["case_id"]
    assert case_id.startswith("CASE-")

    # Get case details
    g_res = client.get(f"/api/cases/{case_id}")
    assert g_res.status_code == 200
    assert g_res.json()["dag_plot_number"] == "9262"

    # Update case status
    u_res = client.patch(f"/api/cases/{case_id}", json={"status": "UNDER_REVIEW", "priority": "CRITICAL"})
    assert u_res.status_code == 200
    assert u_res.json()["status"] == "UNDER_REVIEW"
    assert u_res.json()["priority"] == "CRITICAL"

    # Add note
    n_res = client.post(f"/api/cases/{case_id}/notes", json={"note": "Survey inspector dispatched to plot site.", "author": "Registrar Hasan"})
    assert n_res.status_code == 200
    updated_notes = n_res.json()["officer_notes"]
    assert len(updated_notes) >= 2
    assert "Survey inspector dispatched" in updated_notes[-1]["note"]


def test_verification_mutation_mismatch_scenario():
    """Verify that registration-mutation mismatch triggers RULE_UNVERIFIED_MUTATION_RECORD."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2017-55696",
            "dag_plot_number": "7025",
            "transferred_area_decimal": 47.94,
            "execution_date": "2017-09-21",
            "seller_nid": "OWN-C5CE099C",
            "buyer_nid": "OWN-7C16128D",
            "previous_deed_ref": "DEED-2011-17890",
            "mutation_case_no": "MUT-2017-5331/Paba",
            "consideration_bdt": 3221507.33,
            "khatian_number": "384",
        }
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "CONFIRMED_INCONSISTENCY"
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_UNVERIFIED_MUTATION_RECORD" in rule_codes
    assert data["ml_risk_score"] > 0.70

    # Test report export on this verification
    rep_res = client.get(f"/api/reports/{data['verification_id']}")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert "sha256_certificate_hash" in rep_data
    assert len(rep_data["sha256_certificate_hash"]) == 64

    # Test printable HTML report (default Bengali and explicit English)
    html_res = client.get(f"/api/reports/html/{data['verification_id']}")
    assert html_res.status_code == 200
    assert "সিন্থেটিক ডেমো" in html_res.text or "SYNTHETIC DEMO" in html_res.text

    html_res_en = client.get(f"/api/reports/html/{data['verification_id']}?lang=en")
    assert html_res_en.status_code == 200
    assert "SYNTHETIC DEMO" in html_res_en.text
    assert "STATUTORY VERIFICATION REPORT" in html_res_en.text

