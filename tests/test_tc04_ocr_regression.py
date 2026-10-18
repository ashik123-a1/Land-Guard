"""Regression tests for TC-04 OCR extraction, full-width punctuation normalization,
bilingual label noise rejection, honest uncertainty reporting, and canonical statutory verification.
"""

import os
import pytest
from PIL import Image

from src.landguard_vision.run_ocr import run_ocr, extract_fields_from_text, _clean_ocr_line
from src.landguard_web.service import LandGuardVerificationService


def test_tc04_full_width_punctuation_normalization():
    """Verifies that unicode full-width punctuation produced by DBNet/RapidOCR is normalized to ASCII."""
    raw_rapid_line = "\u53ef\u53ef/Dag\uff08Plot\uff09No:8210"
    cleaned = _clean_ocr_line(raw_rapid_line)
    assert "(" in cleaned and ")" in cleaned
    assert "\uff08" not in cleaned and "\uff09" not in cleaned
    extracted = extract_fields_from_text(cleaned)
    assert extracted.get("dag_plot_number") == "8210"
    assert extracted.get("_dag_plot_provenance") == "EXPLICIT_LABEL"


def test_tc04_compound_bilingual_label_noise_rejection():
    """Verifies that internal label noise like '059' in 'দাগ নং/059 (Plot) No: 8210' is discarded."""
    noisy_line = "দাগ নং/059 (Plot) No: 8210"
    extracted = extract_fields_from_text(noisy_line)
    # 059 was followed immediately by '(Plot) No:' and should not be picked as the plot number
    assert extracted.get("dag_plot_number") == "8210"
    assert extracted.get("dag_plot_number") != "059"


def test_tc04_image_extraction_honesty_and_provenance():
    """Verifies end-to-end OCR extraction on actual IMG-025DAECA.png without ground-truth injection."""
    sample_path = os.path.abspath(r"F:\ashik test data\MANUAL_TEST_PACK\samples\IMG-025DAECA.png")
    if not os.path.exists(sample_path):
        sample_path = os.path.abspath(r"data/full/images/IMG-025DAECA.png")

    assert os.path.exists(sample_path), f"Sample {sample_path} must exist for regression test"
    img = Image.open(sample_path)
    txt, lines, extracted = run_ocr(img, engine="auto")

    assert extracted.get("deed_number") == "DEED-2005-23539"
    assert extracted.get("transferred_area_decimal") == "31.82"
    assert extracted.get("dag_plot_number") == "8210"
    assert extracted.get("_dag_plot_provenance") == "EXPLICIT_LABEL"


def test_tc04_canonical_statutory_verification_on_confirmed_plot():
    """Verifies that when plot 8210 is confirmed, canonical lookup operates on parcel 8210 and triggers area/title rules."""
    svc = LandGuardVerificationService()
    res = svc.verify_transaction(confirmed_fields={
        "document_type": "DEED_OF_SALE",
        "deed_number": "DEED-2005-23539",
        "dag_plot_number": "8210",
        "transferred_area_decimal": 31.82,
        "execution_date": "2005-07-22",
        "seller_nid": "SYN-4713493618",
        "buyer_nid": "SYN-1671902294",
        "mouza": "Fatehabad",
        "upazila": "Hathazari",
        "district": "Chattogram",
    })

    assert res.get("overall_status") == "CONFIRMED_INCONSISTENCY"
    assert res.get("cadastral_found") is True
    # Canonical capacity of Plot 8210 in Fatehabad is 19.84 dec
    assert float(res.get("cadastral_parcel", {}).get("total_area_decimal")) == 19.84
    rules = [r.get("rule_code") for r in res.get("rules_triggered", [])]
    assert "RULE_AREA_EXCEEDS_CAPACITY" in rules
    assert "RULE_SELLER_NOT_TITLEHOLDER" in rules
    assert res.get("ml_risk_score") > 0.95


def test_regression_tc05_and_tc11_intact():
    """Verifies that previously passing TC-05 and TC-11 continue to operate as expected."""
    svc = LandGuardVerificationService()

    # TC-05 Case A Plot 4099
    tc05_path = os.path.abspath(r"F:\ashik test data\MANUAL_TEST_PACK\samples\IMG-3F674C0B.png")
    if not os.path.exists(tc05_path):
        tc05_path = os.path.abspath(r"data/full/images/IMG-3F674C0B.png")
    with open(tc05_path, "rb") as f:
        up5 = svc.process_document_upload(f.read(), "IMG-3F674C0B.png")
    assert up5.get("document_type") == "SALE_DEED"
    assert up5.get("extracted_fields", {}).get("dag_plot_number") == "4099"
    assert up5.get("extracted_fields", {}).get("transferred_area_decimal") == "69.64"

    # TC-11 Non-Land gatekeeper rejection
    tc11_path = os.path.abspath(r"F:\ashik test data\MANUAL_TEST_PACK\samples\restaurant_menu.png")
    if not os.path.exists(tc11_path):
        tc11_path = os.path.abspath(r"data/samples/restaurant_menu.png")
    with open(tc11_path, "rb") as f:
        with pytest.raises(ValueError, match="Document Not Recognized as a Land Record"):
            svc.process_document_upload(f.read(), "restaurant_menu.png")


def test_unrelated_documents_not_assigned_fabricated_plots():
    """Verifies that generic text without valid plot labels is never assigned fabricated dag_plot_numbers."""
    unrelated_text = "Coffee Shop Menu\nEspresso: 120 BDT\nCappuccino: 180 BDT\nTotal: 300 BDT"
    extracted = extract_fields_from_text(unrelated_text)
    assert extracted.get("dag_plot_number") is None
    assert extracted.get("deed_number") is None
