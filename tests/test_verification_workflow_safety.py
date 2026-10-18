"""Focused regression tests for LandGuard Verify Deed workflow, OCR safety against incidental numbers,
CyberScan scanner wiring, manual input path, review stage integrity, rule-aware optional fields,
and report link preservation.
"""

import io
import os
import json
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from src.landguard_web.app import app
from src.landguard_web.service import service
from src.landguard_vision.run_ocr import extract_fields_from_text


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def citizen_client():
    client = TestClient(app, follow_redirects=False)
    client.post("/api/auth/demo-login?role=citizen")
    return client


def test_file_validation_rejects_invalid_extension_and_accepts_valid_image(client):
    """1. Upload and file-validation behavior: extension rejection, document type plausibility, and real image ingestion."""
    # A. Reject invalid extension (e.g. .exe)
    bad_file = io.BytesIO(b"malicious executable or raw text")
    res_bad = client.post(
        "/api/upload",
        files={"file": ("bad_payload.exe", bad_file, "application/octet-stream")},
    )
    assert res_bad.status_code == 400
    assert "Invalid file extension" in res_bad.json()["detail"]

    # B. Reject blank / unreadable image
    blank_img = Image.new("RGB", (300, 200), color=(255, 255, 255))
    buf_blank = io.BytesIO()
    blank_img.save(buf_blank, format="PNG")
    buf_blank.seek(0)
    res_blank = client.post(
        "/api/upload",
        files={"file": ("blank.png", buf_blank, "image/png")},
    )
    assert res_blank.status_code == 400
    assert "Unable to identify document type" in res_blank.json()["detail"]

    # C. Reject unrelated non-land document image (e.g. a restaurant recipe)
    unrelated_img = Image.new("RGB", (600, 400), color=(240, 240, 240))
    draw = ImageDraw.Draw(unrelated_img)
    draw.text((30, 30), "Grand Restaurant Menu\nSoup: $5.00\nSteak: $25.00\nDessert: $7.50\nOrder Total: $37.50", fill=(0, 0, 0))
    buf_unrelated = io.BytesIO()
    unrelated_img.save(buf_unrelated, format="PNG")
    buf_unrelated.seek(0)
    res_unrelated = client.post(
        "/api/upload",
        files={"file": ("restaurant_receipt.png", buf_unrelated, "image/png")},
    )
    assert res_unrelated.status_code == 400
    assert "Document Not Recognized as a Land Record" in res_unrelated.json()["detail"]

    # D. Accept valid synthetic land deed document
    real_sample_path = "data/full/images/IMG-8B4D3063.png"
    if os.path.exists(real_sample_path):
        with open(real_sample_path, "rb") as f:
            real_bytes = f.read()
        res_good = client.post(
            "/api/upload",
            files={"file": ("synthetic_deed.png", io.BytesIO(real_bytes), "image/png")},
        )
        assert res_good.status_code == 200
        data = res_good.json()
        assert "extracted_fields" in data
        assert "field_confidences" in data
        assert "sha256_hash" in data
        assert len(data["sha256_hash"]) == 64
        assert data.get("is_land_document") is True


def test_cyberscan_animation_and_stepper_elements_in_template(citizen_client):
    """2. Verify CyberScan animation elements, Phase 1 & 2 containers, error banner, and 4-step wizard present in template."""
    res = citizen_client.get("/user/verify")
    assert res.status_code == 200
    html = res.text

    # Stepper navigation stages
    assert "step-nav-1" in html
    assert "step-nav-2" in html
    assert "step-nav-3" in html
    assert "step-nav-4" in html

    # Input method panels & error banner
    assert "Upload Synthetic Deed Document" in html
    assert "upload-error-banner" in html
    assert "Enter Details Manually" in html
    assert "manual-entry-form" in html
    assert "f_man_deed_number" in html
    assert "f_man_dag_plot_number" in html

    # CyberScan AI animation elements (Phase 1 & Phase 2)
    assert "step-section-2-scan" in html
    assert "cyberscan-phase1-vortex" in html
    assert "vortexProgressCircle" in html
    assert "uploadPercentNum" in html
    assert "uploadLinearFill" in html
    assert "cyberscan-phase2-laserscan" in html
    assert "laser-line-anim" in html
    assert "laser-curtain-anim" in html
    assert "terminalLogBody" in html
    assert "boundingBoxOverlay" in html
    assert "imageScanFrame" in html
    assert "hud-corner" in html

    # Demo testing scenario section heading beneath inputs
    assert "Demo Testing Scenarios — Synthetic Benchmark Data" in html


def test_ocr_safety_distinguishes_incidental_numbers_from_plot_numbers():
    """3. Verify OCR does NOT treat incidental digits (like '5331' in phone/support/postal text or mutation refs) as a Dag Plot number,
    while explicitly labelled plot numbers and Bengali numerals (০-৯) are extracted accurately."""
    # Text with incidental digits unrelated to plot/dag
    incidental_text = (
        "Dhaka Sub-Registry Office\n"
        "Helpline Phone: 5331, Postal Code: 1216\n"
        "Customer Support Ticket ID: 5331\n"
        "Mutation Case: MUT-2017-5331/Paba\n"
        "Deed No: DEED-2024-10024\n"
    )
    ext_incidental = extract_fields_from_text(incidental_text)
    assert ext_incidental.get("deed_number") == "DEED-2024-10024"
    assert ext_incidental.get("mutation_case_no") == "MUT-2017-5331/Paba"
    # Plot/Dag number MUST NOT be extracted from '5331' inside mutation case or phone number
    assert ext_incidental.get("dag_plot_number") is None

    # Text with explicit Bengali Dag No label and Bengali numerals (০-৯)
    explicit_bn_text = (
        "সাফ কবলা দলিল নং DEED-2023-88912\n"
        "মৌজা: সাভার | দাগ নং: ৫৩৩১ | খতিয়ান নং: ১০১\n"
    )
    ext_explicit = extract_fields_from_text(explicit_bn_text)
    assert ext_explicit.get("dag_plot_number") == "5331"
    assert ext_explicit.get("khatian_number") == "101"
    assert ext_explicit.get("_dag_plot_provenance") == "EXPLICIT_LABEL"

    # Text with explicit English Plot No label
    explicit_en_text = (
        "DEED OF CONVEYANCE DEED-2022-77112\n"
        "Plot No: 9044, Transferred Area: 10.50 Dec\n"
    )
    ext_en = extract_fields_from_text(explicit_en_text)
    assert ext_en.get("dag_plot_number") == "9044"


def test_field_uncertainty_labels_honest_status():
    """4. Honest status labels (REQUIRED_MISSING / OPTIONAL_ABSENT vs VERIFIED_OCR vs LOW_CONFIDENCE)."""
    extracted_partial = {
        "deed_number": "DEED-2024-11223",
        "dag_plot_number": "9044",
        "_dag_plot_provenance": "EXPLICIT_LABEL",
        # Area, NIDs, date intentionally omitted to test OPTIONAL_ABSENT status
    }
    uncertainties = service.documents_svc._compute_field_uncertainties(extracted_partial, [])

    # Dag plot extracted with explicit label -> VERIFIED_OCR (0.90)
    assert uncertainties["dag_plot_number"]["status"] == "VERIFIED_OCR"
    assert uncertainties["dag_plot_number"]["confidence"] >= 0.90

    # Optional absent transferred area -> OPTIONAL_ABSENT
    assert uncertainties["transferred_area_decimal"]["status"] in ["OPTIONAL_ABSENT", "MISSING"]
    assert uncertainties["transferred_area_decimal"]["confidence"] == 0.0

    # Optional absent seller NID -> OPTIONAL_ABSENT
    assert uncertainties["seller_nid"]["status"] in ["OPTIONAL_ABSENT", "MISSING"]
    assert uncertainties["seller_nid"]["confidence"] == 0.0

    # Schedule table extracted plot -> LOW_CONFIDENCE
    extracted_table = {
        "dag_plot_number": "4812",
        "_dag_plot_provenance": "TABLE_CONTEXT",
    }
    table_uncertainties = service.documents_svc._compute_field_uncertainties(extracted_table, [])
    assert table_uncertainties["dag_plot_number"]["status"] == "LOW_CONFIDENCE"
    assert table_uncertainties["dag_plot_number"]["confidence"] < 0.85


def test_canonical_lookup_distinguishes_mismatch_from_ocr_nondetection(client):
    """5. Canonical lookup mismatch vs OCR non-detection: unrecorded plot triggers RULE_PLOT_NOT_FOUND_IN_REGISTRY without claiming false fraud."""
    payload_unrecorded = {
        "confirmed_fields": {
            "deed_number": "DEED-2024-53310",
            "dag_plot_number": "5331",
            "transferred_area_decimal": 10.0,
            "execution_date": "2024-01-01",
            "seller_nid": "OWN-UNKNOWN-1",
            "buyer_nid": "OWN-UNKNOWN-2",
        },
        "image_path": None,
    }
    res = client.post("/api/verify", json=payload_unrecorded)
    assert res.status_code == 200
    data = res.json()
    assert data["dag_plot_number"] == "5331"
    assert data["cadastral_found"] is False
    assert data["overall_status"] in ["MISSING_EVIDENCE", "CONFIRMED_INCONSISTENCY", "REVIEW_REQUIRED"]
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_PLOT_NOT_FOUND_IN_REGISTRY" in rule_codes


def test_manual_input_path_executes_verification_successfully(client):
    """6. Manual input path invokes authoritative verification service for full and partial assessments."""
    # Full manual entry
    payload_manual = {
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
        },
        "image_path": None,
    }
    res = client.post("/api/verify", json=payload_manual)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "CLEAR_FOR_STANDARD_PROCESSING"
    assert data["dag_plot_number"] == "9044"
    assert "verification_id" in data

    # Partial assessment: Only dag_plot_number provided, transferred_area is absent
    payload_partial = {
        "confirmed_fields": {
            "dag_plot_number": "9044",
            "deed_number": None,
            "transferred_area_decimal": None,
            "execution_date": None,
            "seller_nid": None,
            "buyer_nid": None,
        },
        "image_path": None,
    }
    res_part = client.post("/api/verify", json=payload_partial)
    assert res_part.status_code == 200
    data_part = res_part.json()
    assert data_part["dag_plot_number"] == "9044"
    assert data_part["cadastral_found"] is True
    # Evaluates RULE_AREA_NOT_ASSESSED instead of falsely asserting area excess
    rule_codes = [r["rule_code"] for r in data_part["rules_triggered"]]
    assert "RULE_AREA_NOT_ASSESSED" in rule_codes
    assert "RULE_AREA_EXCEEDS_CAPACITY" not in rule_codes


def test_all_demo_benchmark_cards_load_configured_scenarios():
    """7. All demo cards load their intended configured scenarios with existing disk images."""
    sample_cases = service.get_sample_cases()
    assert len(sample_cases) >= 6

    case_ids = [c["case_id"] for c in sample_cases]
    assert "DEMO-CLEAN" in case_ids
    assert "DEMO-MUTATION-MISMATCH" in case_ids
    assert "DEMO-AREA-EXCESS" in case_ids
    assert "DEMO-DOUBLE-SALE" in case_ids
    assert "DEMO-VISUAL-TAMPERING" in case_ids
    assert "DEMO-ALTERED-PLOT" in case_ids

    # Each scenario must have valid preset_fields and an existing disk image file
    for c in sample_cases:
        pf = c["preset_fields"]
        assert "dag_plot_number" in pf and len(pf["dag_plot_number"]) > 0
        assert "deed_number" in pf and len(pf["deed_number"]) > 0
        img_path = c.get("image_path")
        if img_path:
            assert os.path.exists(img_path), f"Sample case image missing on disk: {img_path}"


def test_report_routes_and_pdf_links_preserved(client):
    """8. Report and PDF routes remain unchanged, functional, and intact."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 8.38,
            "execution_date": "2006-11-11",
            "seller_nid": "OWN-11CE5DD2",
            "buyer_nid": "OWN-CE177B4E",
        },
        "image_path": "data/full/images/IMG-24DCC9AE.png",
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    v_id = res.json()["verification_id"]

    # Verify report HTML route
    res_rep = client.get(f"/reports/{v_id}")
    assert res_rep.status_code == 200
    assert "STATUTORY AUDIT DOSSIER" in res_rep.text or "LandGuard" in res_rep.text

    # Verify report PDF endpoint
    res_pdf = client.get(f"/api/reports/pdf/{v_id}")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF")


def test_unindexed_plot_returns_missing_evidence_without_false_fraud(client):
    """9. Unindexed plot returns MISSING_EVIDENCE without false fraud or false area capacity violations."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2024-99999",
            "dag_plot_number": "99999",
            "transferred_area_decimal": 25.50,
            "execution_date": "2024-01-01",
        },
        "evidence_source": "MANUAL",
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["cadastral_found"] is False
    assert data["overall_status"] == "MISSING_EVIDENCE"
    assert data["ml_calibration"] == "NOT_ASSESSABLE"
    assert data["ml_risk_score"] is None
    assert data["ml_model_fallback"] is True

    # Must contain RULE_PLOT_NOT_FOUND_IN_REGISTRY
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_PLOT_NOT_FOUND_IN_REGISTRY" in rule_codes

    # Must NOT contain false CONFIRMED_INCONSISTENCY
    categories = [r["category"] for r in data["rules_triggered"]]
    assert "CONFIRMED_INCONSISTENCY" not in categories
    assert "RULE_AREA_EXCEEDS_CAPACITY" not in rule_codes


def test_missing_optional_fields_on_indexed_plot_returns_missing_evidence_without_false_ml_risk(client):
    """10. Missing optional fields (no seller ID, no mutation, no prior deed) return MISSING_EVIDENCE without 99% ML fraud."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 8.38,
            "execution_date": "2006-11-11",
            # seller_nid, buyer_nid, previous_deed_ref, mutation_case_no intentionally omitted
        },
        "evidence_source": "UPLOAD",
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["cadastral_found"] is True
    assert data["overall_status"] == "MISSING_EVIDENCE"
    assert data["ml_calibration"] == "INSUFFICIENT_EVIDENCE"
    assert data["ml_risk_score"] is None
    assert data["ml_model_fallback"] is True

    # No hard contradiction
    categories = [r["category"] for r in data["rules_triggered"]]
    assert "CONFIRMED_INCONSISTENCY" not in categories
    assert "ML_ELEVATED_RISK_SCORE" not in [r["rule_code"] for r in data["rules_triggered"]]


def test_pilot_parcel_5083_loaded_and_verified_properly(client):
    """11. Pilot parcel #5083 (Fatehabad, 67.53 dec) from pilot_records.json is indexed and does not exceed capacity."""
    payload = {
        "confirmed_fields": {
            "deed_number": "DEED-2007-4783",
            "dag_plot_number": "5083",
            "transferred_area_decimal": 67.53,
            "execution_date": "2007-05-15",
        },
        "evidence_source": "UPLOAD",
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["cadastral_found"] is True
    assert data["cadastral_parcel"]["mouza"] == "Fatehabad"
    assert abs(data["cadastral_parcel"]["total_area_decimal"] - 67.53) < 0.01

    # Transferred area 67.53 does NOT exceed parcel capacity 67.53
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_AREA_EXCEEDS_CAPACITY" not in rule_codes


def test_demo_clean_and_mutation_mismatch_preserves_expected_findings(client):
    """12. Benchmark scenarios evaluate according to authoritative synthetic ground truth."""
    # DEMO-CLEAN
    clean_sample = next(c for c in service.get_sample_cases() if c["case_id"] == "DEMO-CLEAN")
    res_clean = client.post("/api/verify", json={
        "confirmed_fields": clean_sample["preset_fields"],
        "image_path": clean_sample["image_path"],
        "evidence_source": "BENCHMARK",
    })
    assert res_clean.status_code == 200
    clean_data = res_clean.json()
    assert clean_data["overall_status"] == "CLEAR_FOR_STANDARD_PROCESSING"
    assert clean_data["ml_calibration"] == "LOW_RISK"
    assert len(clean_data["rules_triggered"]) == 0

    # DEMO-MUTATION-MISMATCH
    mut_sample = next(c for c in service.get_sample_cases() if c["case_id"] == "DEMO-MUTATION-MISMATCH")
    res_mut = client.post("/api/verify", json={
        "confirmed_fields": mut_sample["preset_fields"],
        "image_path": mut_sample["image_path"],
        "evidence_source": "BENCHMARK",
    })
    assert res_mut.status_code == 200
    mut_data = res_mut.json()
    assert mut_data["overall_status"] == "CONFIRMED_INCONSISTENCY"
    mut_rule_codes = [r["rule_code"] for r in mut_data["rules_triggered"]]
    assert "RULE_UNVERIFIED_MUTATION_RECORD" in mut_rule_codes


def test_mutation_record_classification_and_clean_verification(client):
    """13. Real mutation record (IMG-F0EA2687.png) classifies as MUTATION_RECORD and verifies cleanly without deed penalties."""
    mut_img_path = "data/full/images/IMG-F0EA2687.png"
    if not os.path.exists(mut_img_path):
        pytest.skip(f"Image {mut_img_path} not found")

    with open(mut_img_path, "rb") as f:
        img_bytes = f.read()

    res_upload = client.post(
        "/api/upload",
        files={"file": ("IMG-F0EA2687.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()

    assert upload_data.get("document_type") == "MUTATION_RECORD"
    assert upload_data.get("is_uncertain") is False
    ext = upload_data.get("extracted_fields", {})
    assert ext.get("mutation_case_no") == "MUT-2001-9502/Rupsha"
    assert ext.get("dag_plot_number") == "9044"
    assert ext.get("mutation_status") == "APPROVED"

    # Verify transaction with MUTATION_RECORD type
    payload = {
        "document_type": "MUTATION_RECORD",
        "confirmed_fields": {
            "document_type": "MUTATION_RECORD",
            "mutation_case_no": ext.get("mutation_case_no"),
            "dag_plot_number": ext.get("dag_plot_number"),
            "transferred_area_decimal": ext.get("transferred_area_decimal", 9.24),
            "mutation_status": "APPROVED",
            "khatian_number": ext.get("khatian_number", "1420"),
        },
        "image_path": mut_img_path,
        "evidence_source": "UPLOAD",
    }
    res_verify = client.post("/api/verify", json=payload)
    assert res_verify.status_code == 200
    verify_data = res_verify.json()

    assert verify_data["cadastral_found"] is True
    assert verify_data["overall_status"] == "CLEAR_FOR_STANDARD_PROCESSING"
    assert len(verify_data["rules_triggered"]) == 0
    # Must NOT have failed for lack of deed seller NID or sale consideration
    rule_codes = [r["rule_code"] for r in verify_data["rules_triggered"]]
    assert "RULE_SELLER_NID_NOT_VERIFIED" not in rule_codes
    assert "RULE_BUYER_NID_NOT_VERIFIED" not in rule_codes


def test_sale_deed_boundary_plot_disambiguation(client):
    """14. Deed with boundary plots (IMG-4F67AAA0.png) extracts true plot 9044, not South boundary plot 9045."""
    deed_img_path = "data/full/images/IMG-4F67AAA0.png"
    if not os.path.exists(deed_img_path):
        pytest.skip(f"Image {deed_img_path} not found")

    with open(deed_img_path, "rb") as f:
        img_bytes = f.read()

    res_upload = client.post(
        "/api/upload",
        files={"file": ("IMG-4F67AAA0.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()

    assert upload_data.get("document_type") == "SALE_DEED"
    ext = upload_data.get("extracted_fields", {})
    # MUST be 9044, never 9045 from "South: Plot #9045"
    assert ext.get("dag_plot_number") == "9044"


def test_dynamic_document_forms_and_uncertainty_elements_in_template(citizen_client):
    """15. Verify dynamic document type switcher, all 5 form groups, and uncertainty banner in verify template."""
    res = citizen_client.get("/user/verify")
    assert res.status_code == 200
    html = res.text

    # Uncertainty banner
    assert "doc-uncertain-banner" in html
    assert "Document Type Uncertain" in html

    # Tab switcher buttons
    assert "tab-btn-sale-deed" in html
    assert "tab-btn-mutation-record" in html
    assert "tab-btn-khatian-porcha" in html
    assert "tab-btn-tax-receipt" in html
    assert "tab-btn-parcel-map" in html

    # Form groups
    assert "form-group-sale-deed" in html
    assert "form-group-mutation-record" in html
    assert "form-group-khatian-porcha" in html
    assert "form-group-tax-receipt" in html
    assert "form-group-parcel-map" in html

    # Key inputs in type-specific groups
    assert "f_active_document_type" in html
    assert "f_mut_case_no" in html
    assert "f_mut_dag_plot" in html
    assert "f_mut_status" in html
    assert "f_kh_khatian_no" in html
    assert "f_kh_survey_type" in html
    assert "f_tax_holding_no" in html
    assert "f_map_dag_plot" in html

    # JS function presence
    assert "function switchDocumentType" in html
    assert "function syncCrossFields" in html


def test_case_a_deed_of_sale_submission_and_capacity_verification(client):
    """16. Case A: Deed of Sale (IMG-3F674C0B.png) upload, review auto-fill, and statutory verification."""
    img_path = "data/full/images/IMG-3F674C0B.png"
    if not os.path.exists(img_path):
        pytest.skip(f"Image {img_path} not found")

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    # Step 1: Upload
    res_upload = client.post(
        "/api/upload",
        files={"file": ("IMG-3F674C0B.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data.get("document_type") == "SALE_DEED"

    ext = upload_data.get("extracted_fields", {})
    assert ext.get("deed_number") == "DEED-2011-41265"
    assert ext.get("dag_plot_number") == "4099"
    assert float(ext.get("transferred_area_decimal")) == pytest.approx(69.64, rel=1e-2)
    assert ext.get("execution_date") == "2011-10-27"
    assert ext.get("seller_nid") == "SYN-7393638546"
    assert ext.get("buyer_nid") == "SYN-7725228728"
    assert float(ext.get("consideration_bdt")) == pytest.approx(5974000.0, rel=1e-2)

    # Step 2: Verification submission with confirmed fields
    payload = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": ext.get("deed_number"),
            "dag_plot_number": ext.get("dag_plot_number"),
            "transferred_area_decimal": float(ext.get("transferred_area_decimal")),
            "execution_date": ext.get("execution_date"),
            "seller_nid": ext.get("seller_nid"),
            "buyer_nid": ext.get("buyer_nid"),
            "previous_deed_ref": ext.get("previous_deed_ref"),
            "mutation_case_no": ext.get("mutation_case_no"),
            "consideration_bdt": float(ext.get("consideration_bdt")),
            "khatian_number": ext.get("khatian_number"),
        },
        "image_path": img_path,
        "evidence_source": "UPLOAD",
    }
    res_verify = client.post("/api/verify", json=payload)
    assert res_verify.status_code == 200
    data = res_verify.json()

    assert data["cadastral_found"] is True
    assert data["dag_plot_number"] == "4099"
    # Plot 4099 registered holding capacity is 29.66 dec; transferring 69.64 dec legitimately triggers capacity excess
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_AREA_EXCEEDS_CAPACITY" in rule_codes
    assert data["overall_status"] == "CONFIRMED_INCONSISTENCY"
    assert "verification_id" in data
    assert data["verification_id"].startswith("VRF-")


def test_case_b_mutation_order_submission_and_rule_verification(client):
    """17. Case B: Mutation Order (IMG-04A1B22B.png) upload, review auto-fill, and statutory verification."""
    img_path = "data/full/images/IMG-04A1B22B.png"
    if not os.path.exists(img_path):
        pytest.skip(f"Image {img_path} not found")

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    # Step 1: Upload
    res_upload = client.post(
        "/api/upload",
        files={"file": ("IMG-04A1B22B.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data.get("document_type") == "MUTATION_RECORD"

    ext = upload_data.get("extracted_fields", {})
    assert ext.get("mutation_case_no") == "MUT-2006-5364/Rupsha"
    assert ext.get("dag_plot_number") == "7873"
    assert ext.get("execution_date") == "2007-05-03"
    assert float(ext.get("transferred_area_decimal")) == pytest.approx(81.95, rel=1e-2)
    assert ext.get("mutation_status") == "APPROVED"

    # Step 2: Verification submission with confirmed fields
    payload = {
        "document_type": "MUTATION_RECORD",
        "confirmed_fields": {
            "document_type": "MUTATION_RECORD",
            "dag_plot_number": ext.get("dag_plot_number"),
            "mutation_case_no": ext.get("mutation_case_no"),
            "transferred_area_decimal": float(ext.get("transferred_area_decimal")),
            "execution_date": ext.get("execution_date"),
            "mutation_status": ext.get("mutation_status", "APPROVED"),
            "khatian_number": ext.get("khatian_number"),
            "applicant_name": ext.get("applicant_name"),
            "upazila": ext.get("upazila"),
        },
        "image_path": img_path,
        "evidence_source": "UPLOAD",
    }
    res_verify = client.post("/api/verify", json=payload)
    assert res_verify.status_code == 200
    data = res_verify.json()

    assert data["cadastral_found"] is True
    assert data["dag_plot_number"] == "7873"
    # Mutation record should be evaluated under mutation rules, not false conveyance deed rules
    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_SELLER_NOT_TITLEHOLDER" not in rule_codes
    assert "RULE_BROKEN_CHAIN_OF_TITLE" not in rule_codes
    assert "verification_id" in data


def test_dynamic_form_hidden_inputs_do_not_block_submission(citizen_client):
    """18. Verify HTML and JS safety contract: novalidate on form, data-type-required attributes, and disabled toggle."""
    res = citizen_client.get("/user/verify")
    assert res.status_code == 200
    html = res.text

    # Form has novalidate to prevent hidden inputs from blocking form submission
    assert '<form id="verify-form" novalidate' in html

    # Required inputs have data-type-required="true"
    assert 'id="f_dag_plot_number" data-type-required="true"' in html
    assert 'id="f_mut_case_no" data-type-required="true"' in html
    assert 'id="f_mut_dag_plot" data-type-required="true"' in html
    assert 'id="f_kh_khatian_no" data-type-required="true"' in html
    assert 'id="f_kh_dag_plot" data-type-required="true"' in html
    assert 'id="f_tax_holding_no" data-type-required="true"' in html
    assert 'id="f_tax_dag_plot" data-type-required="true"' in html
    assert 'id="f_map_dag_plot" data-type-required="true"' in html

    # switchDocumentType script manages disabled and required attributes
    assert "ctrl.disabled = false;" in html
    assert "ctrl.disabled = true;" in html
    assert "ctrl.required = false;" in html
    assert "ctrl.getAttribute('data-type-required') === 'true'" in html

    # isVerifying duplicate submission guard
    assert "let isVerifying = false;" in html
    assert "if (isVerifying) return;" in html


def test_mutation_applicant_extraction_and_absent_khatian_honesty(client):
    """19. Verify Mutation Order extraction on real image IMG-F79D53F3:
    - Applicant / Mutated Owner extracts 'Habibur Ali' with VERIFIED_OCR status.
    - Khatian number is genuinely absent and honestly preserved as None / OPTIONAL_ABSENT (no fabrication).
    - When Khatian is present in other text, regex extracts it accurately.
    - Submission executes cleanly with honest rule verification.
    """
    img_path = "data/full/images/IMG-F79D53F3.png"
    assert os.path.exists(img_path), f"Source image {img_path} must exist"

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    res = client.post(
        "/api/upload",
        files={"file": ("IMG-F79D53F3.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res.status_code == 200
    data = res.json()

    assert data.get("document_type") == "MUTATION_RECORD"
    ext = data.get("extracted_fields", {})
    confs = data.get("field_confidences", {})

    # Key fields extracted accurately
    assert ext.get("mutation_case_no") == "MUT-2007-1130/Keraniganj"
    assert ext.get("dag_plot_number") == "2438"
    assert ext.get("transferred_area_decimal") == "59.95"
    assert ext.get("mutation_status") == "APPROVED"
    assert ext.get("applicant_name") == "Habibur Ali"

    # Confidences: Applicant is VERIFIED_OCR green
    app_conf = confs.get("applicant_name", {})
    assert app_conf.get("status") == "VERIFIED_OCR"
    assert app_conf.get("level") == "green"
    assert app_conf.get("confidence", 0) >= 0.85

    # Khatian is honestly absent from IMG-F79D53F3 (no fabrication)
    assert ext.get("khatian_number") is None
    kh_conf = confs.get("khatian_number", {})
    assert kh_conf.get("status") == "OPTIONAL_ABSENT"
    assert kh_conf.get("level") == "slate"

    # Verify Khatian extraction works when text genuinely contains Khatian
    sample_text_bn = "উপজেলা ভূমি অফিস\nহাল খতিয়ান নং: ১২৩৪\nদাগ নং: ৫৬৭৮\nআবেদনকারী: হাবিবুর রহমান"
    extracted_bn = extract_fields_from_text(sample_text_bn)
    assert extracted_bn.get("khatian_number") == "1234"
    assert extracted_bn.get("dag_plot_number") == "5678"
    assert extracted_bn.get("applicant_name") == "হাবিবুর রহমান"

    sample_text_en = "MUTATION ORDER\nMutated Khatian No: 4567\nPlot No: 8899\nMutated Owner: Salma Begum"
    extracted_en = extract_fields_from_text(sample_text_en)
    assert extracted_en.get("khatian_number") == "4567"
    assert extracted_en.get("dag_plot_number") == "8899"
    assert extracted_en.get("applicant_name") == "Salma Begum"

    # Statutory verification submission for IMG-F79D53F3
    payload = {
        "document_type": "MUTATION_RECORD",
        "confirmed_fields": {
            "document_type": "MUTATION_RECORD",
            "mutation_case_no": ext.get("mutation_case_no"),
            "dag_plot_number": ext.get("dag_plot_number"),
            "transferred_area_decimal": float(ext.get("transferred_area_decimal")),
            "execution_date": ext.get("execution_date"),
            "mutation_status": ext.get("mutation_status", "APPROVED"),
            "khatian_number": ext.get("khatian_number"),
            "applicant_name": ext.get("applicant_name"),
            "upazila": ext.get("upazila"),
        },
        "image_path": img_path,
        "evidence_source": "UPLOAD",
    }
    res_verify = client.post("/api/verify", json=payload)
    assert res_verify.status_code == 200
    v_data = res_verify.json()

    assert v_data["cadastral_found"] is True
    assert v_data["dag_plot_number"] == "2438"
    assert "verification_id" in v_data
    # Unverified mutation record triggered legitimately because case 1130 belongs to Keraniganj, not Dhamrai Plot 2438
    rules = [r["rule_code"] for r in v_data["rules_triggered"]]
    assert "RULE_UNVERIFIED_MUTATION_RECORD" in rules
    # ML risk is None (rendered as Insufficient Data) because there is no seller NID in a mutation order
    assert v_data["ml_risk_score"] is None


def test_case_a_distinction_processable_ocr_pass_vs_conflicting_statutory_transfer(client):
    """20. Case A distinction (IMG-3F674C0B.png / 01_land_deeds_conveyance_working_04):
    - Confirms sample is an untampered, processable image (PROCESSABLE_PASS in OCR).
    - Confirms canonical cadastral capacity of Plot 4099 is genuinely 29.66 decimal.
    - Confirms seller 'SYN-7393638546' (Farida Khan) is genuinely absent from Plot 4099 title chain (held by OWN-7EEDCC65).
    - Confirms statutory verification yields CONFIRMED_INCONSISTENCY with RULE_AREA_EXCEEDS_CAPACITY,
      RULE_SELLER_NOT_TITLEHOLDER, and legitimate elevated ML risk (>90%).
    - Verifies test library manifest correctly labels sample as PROCESSABLE_PASS_LEGAL_CONFLICT.
    """
    img_path = "data/full/images/IMG-3F674C0B.png"
    assert os.path.exists(img_path), f"Source image {img_path} must exist"

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    # 1. OCR Extraction: Processable Pass (all fields extract with exact precision)
    res_upload = client.post(
        "/api/upload",
        files={"file": ("IMG-3F674C0B.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data.get("document_type") == "SALE_DEED"
    ext = upload_data.get("extracted_fields", {})
    assert ext.get("deed_number") == "DEED-2011-41265"
    assert ext.get("dag_plot_number") == "4099"
    assert float(ext.get("transferred_area_decimal")) == pytest.approx(69.64, rel=1e-2)
    assert ext.get("execution_date") == "2011-10-27"
    assert ext.get("seller_nid") == "SYN-7393638546"

    # 2. Canonical Registry Lookup for Plot 4099
    # Plot 4099 is indexed as PAR-0148B44C in Barabkunda, Sitakunda, Chattogram with total area 29.66 dec
    payload = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": ext.get("deed_number"),
            "dag_plot_number": ext.get("dag_plot_number"),
            "transferred_area_decimal": float(ext.get("transferred_area_decimal")),
            "execution_date": ext.get("execution_date"),
            "seller_nid": ext.get("seller_nid"),
            "buyer_nid": ext.get("buyer_nid"),
            "previous_deed_ref": ext.get("previous_deed_ref"),
            "mutation_case_no": ext.get("mutation_case_no"),
            "consideration_bdt": float(ext.get("consideration_bdt", 5974000.0)),
            "khatian_number": ext.get("khatian_number"),
        },
        "image_path": img_path,
        "evidence_source": "UPLOAD",
    }
    res_verify = client.post("/api/verify", json=payload)
    assert res_verify.status_code == 200
    v_data = res_verify.json()

    # 3. Legal Statutory Verification Outcome
    assert v_data["cadastral_found"] is True
    assert v_data["dag_plot_number"] == "4099"
    parcel = v_data.get("cadastral_parcel", {})
    assert float(parcel.get("total_area_decimal", 0.0)) == pytest.approx(29.66, rel=1e-2)

    rule_codes = [r["rule_code"] for r in v_data["rules_triggered"]]
    # Contradiction 1: Area excess (69.64 dec transferred on 29.66 dec parcel)
    assert "RULE_AREA_EXCEEDS_CAPACITY" in rule_codes
    # Contradiction 2: Seller Farida Khan (SYN-7393638546) is not in Plot 4099 title chain
    assert "RULE_SELLER_NOT_TITLEHOLDER" in rule_codes
    # Missing optional evidence: No mutation case cited on sale deed
    assert "RULE_UNVERIFIED_MUTATION_RECORD" in rule_codes

    # ML model legitimately flags high risk due to extreme area excess ratio (>200%) and seller contradiction
    assert v_data["ml_risk_score"] is not None
    assert v_data["ml_risk_score"] > 0.90
    assert v_data["overall_status"] == "CONFIRMED_INCONSISTENCY"

    # 4. Ashik Test Data Library Manifest Verification
    manifest_path = "F:/ashik test data/SAMPLE_MANIFEST.json"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        matched = [s for s in manifest.get("samples", []) if s.get("sample_id") == "01_land_deeds_conveyance_working_04"]
        if matched:
            s_entry = matched[0]
            assert s_entry.get("is_fraud_risk") is True
            assert s_entry.get("expected_outcome") == "PROCESSABLE_PASS_LEGAL_CONFLICT"
            assert s_entry.get("expected_legal_outcome") == "CONFIRMED_INCONSISTENCY"


def test_empty_optional_fields_on_clean_plot_does_not_trigger_false_risk_or_inconsistency(client):
    """21. Empty optional fields (previous_deed_ref, mutation_case_no, khatian_number) on a verified legitimate parcel:
    - Vendor OWN-11CE5DD2 holds registered deed DEED-2001-35323 and approved mutation MUT-2001-9502/Rupsha.
    - When optional fields are omitted or left blank in review form, relational engine resolves verified records.
    - Does NOT trigger false CONFIRMED_INCONSISTENCY or false RULE_UNVERIFIED_MUTATION_RECORD.
    - Yields CLEAR_FOR_STANDARD_PROCESSING with low ML risk (<15%).
    """
    payload = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 8.38,
            "execution_date": "2006-11-11",
            "seller_nid": "OWN-11CE5DD2",
            "buyer_nid": "OWN-CE177B4E",
            "previous_deed_ref": "",
            "mutation_case_no": "",
            "khatian_number": "",
            "consideration_bdt": 955246.39,
        },
        "evidence_source": "UPLOAD",
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["cadastral_found"] is True
    assert data["overall_status"] == "CLEAR_FOR_STANDARD_PROCESSING"
    assert data["ml_calibration"] == "LOW_RISK"
    assert data["ml_risk_score"] is not None
    assert data["ml_risk_score"] < 0.15
    assert len(data["rules_triggered"]) == 0


def test_missing_required_fields_and_accidental_payload_omissions(client):
    """22. Distinguish accidental omissions and missing required fields from fraud:
    - Omission of seller_nid returns MISSING_EVIDENCE without false ML risk (ml_calibration=INSUFFICIENT_EVIDENCE).
    - Omission of transferred_area_decimal returns RULE_AREA_NOT_ASSESSED under MISSING_EVIDENCE.
    - Missing dag_plot_number returns RULE_PLOT_NOT_FOUND_IN_REGISTRY under MISSING_EVIDENCE.
    - None of these omissions declare fraudulent CONFIRMED_INCONSISTENCY.
    """
    # Case 1: seller_nid accidentally omitted
    p_no_seller = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "9044",
            "transferred_area_decimal": 8.38,
            "execution_date": "2006-11-11",
        },
        "evidence_source": "UPLOAD",
    }
    r1 = client.post("/api/verify", json=p_no_seller).json()
    assert r1["overall_status"] == "MISSING_EVIDENCE"
    assert r1["ml_risk_score"] is None
    assert r1["ml_calibration"] == "INSUFFICIENT_EVIDENCE"
    r1_codes = [r["rule_code"] for r in r1["rules_triggered"]]
    assert "RULE_SELLER_NOT_TITLEHOLDER" in r1_codes
    assert "CONFIRMED_INCONSISTENCY" not in [r["category"] for r in r1["rules_triggered"]]

    # Case 2: transferred_area_decimal omitted
    p_no_area = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "9044",
            "execution_date": "2006-11-11",
            "seller_nid": "OWN-11CE5DD2",
        },
        "evidence_source": "UPLOAD",
    }
    r2 = client.post("/api/verify", json=p_no_area).json()
    assert r2["overall_status"] == "MISSING_EVIDENCE"
    assert r2["ml_risk_score"] is None
    r2_codes = [r["rule_code"] for r in r2["rules_triggered"]]
    assert "RULE_AREA_NOT_ASSESSED" in r2_codes
    assert "RULE_AREA_EXCEEDS_CAPACITY" not in r2_codes

    # Case 3: dag_plot_number missing
    p_no_plot = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2006-18946",
            "dag_plot_number": "",
            "transferred_area_decimal": 8.38,
            "execution_date": "2006-11-11",
            "seller_nid": "OWN-11CE5DD2",
        },
        "evidence_source": "UPLOAD",
    }
    r3 = client.post("/api/verify", json=p_no_plot).json()
    assert r3["cadastral_found"] is False
    assert r3["overall_status"] == "MISSING_EVIDENCE"
    assert "RULE_PLOT_NOT_FOUND_IN_REGISTRY" in [r["rule_code"] for r in r3["rules_triggered"]]


def test_missing_mutation_reference_on_unmutated_vendor_returns_missing_evidence(client):
    """23. Missing mutation reference when vendor has NO mutation on record:
    - Returns RULE_UNVERIFIED_MUTATION_RECORD with category MISSING_EVIDENCE.
    - Does NOT falsely escalate to CONFIRMED_INCONSISTENCY.
    """
    from src.landguard_models.verification_rules import evaluate_verification_rules
    parcel = {"dag_plot_number": 9044, "total_area_decimal": 9.24}
    txn = {
        "transaction_id": "TXN-TEST-NOMUT",
        "document_type": "SALE_DEED",
        "seller_ids": ["OWN-UNMUTATED-VENDOR"],
        "transferred_area_decimal": 5.0,
        "mutation_case_no": "",
    }
    is_risk, score, findings = evaluate_verification_rules(txn, parcel, history_txns=[], mutations=[])
    mut_findings = [f for f in findings if f["rule_code"] == "RULE_UNVERIFIED_MUTATION_RECORD"]
    assert len(mut_findings) == 1
    assert mut_findings[0]["category"] == "MISSING_EVIDENCE"
    assert mut_findings[0]["reason"] == "No mutation case cited in transaction record."


def test_genuine_area_excess_and_conflicting_ownership_preserved_plot_4099(client):
    """24. Plot 4099 (IMG-3F674C0B.png / 01_land_deeds_conveyance_working_04):
    - Confirms genuine parcel capacity is 29.66 decimal.
    - Confirms transferred area 69.64 decimal genuinely triggers RULE_AREA_EXCEEDS_CAPACITY (CONFIRMED_INCONSISTENCY).
    - Confirms seller Farida Khan genuinely triggers RULE_SELLER_NOT_TITLEHOLDER (CONFIRMED_INCONSISTENCY).
    - Confirms missing mutation reference produces RULE_UNVERIFIED_MUTATION_RECORD (MISSING_EVIDENCE).
    - Confirms ML model flags legitimate high risk (>90%).
    - Confirms overall status is CONFIRMED_INCONSISTENCY without artificial modification.
    """
    payload = {
        "document_type": "SALE_DEED",
        "confirmed_fields": {
            "document_type": "SALE_DEED",
            "deed_number": "DEED-2011-41265",
            "dag_plot_number": "4099",
            "transferred_area_decimal": 69.64,
            "execution_date": "2011-10-27",
            "seller_nid": "SYN-7393638546",
            "buyer_nid": "SYN-7725228728",
            "previous_deed_ref": "",
            "mutation_case_no": "",
            "khatian_number": "",
            "consideration_bdt": 5974000.0,
        },
        "evidence_source": "UPLOAD",
    }
    res = client.post("/api/verify", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["cadastral_found"] is True
    assert data["dag_plot_number"] == "4099"
    assert data["cadastral_parcel"]["total_area_decimal"] == pytest.approx(29.66, rel=1e-2)
    assert data["overall_status"] == "CONFIRMED_INCONSISTENCY"
    assert data["ml_risk_score"] > 0.90
    assert data["ml_calibration"] == "ELEVATED_RISK"

    rule_codes = [r["rule_code"] for r in data["rules_triggered"]]
    assert "RULE_AREA_EXCEEDS_CAPACITY" in rule_codes
    assert "RULE_SELLER_NOT_TITLEHOLDER" in rule_codes
    assert "RULE_UNVERIFIED_MUTATION_RECORD" in rule_codes






