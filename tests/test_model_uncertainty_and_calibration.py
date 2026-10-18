"""Test Model Uncertainty, Calibration, and Truthful Fallback.
Verifies:
1. When no image is provided, CV visual checks are reported as NOT_CHECKED.
2. When image is missing or invalid, CV reports INCONCLUSIVE or NOT_CHECKED gracefully without crashing.
3. Visual presence detection is strictly separated from legal authenticity verification.
4. XGBoost risk scores are properly calibrated (LOW_RISK, MODERATE_RISK, ELEVATED_RISK).
5. If ML model inference is disabled or encounters corrupt features, statutory rule engine provides robust fallback.
"""

import os
import pytest
from src.landguard_web.app import service


def test_verification_without_image_truthful_signals():
    """Verify that when no document image is uploaded, CV checks are NOT_CHECKED and authenticity is False."""
    confirmed = {
        "deed_number": "DEED-TEST-NOIMG",
        "dag_plot_number": "9044",
        "transferred_area_decimal": 4.0,
        "execution_date": "2024-05-10",
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-01",
        "consideration_bdt": 1200000.0,
    }
    result = service.verify_transaction(confirmed_fields=confirmed, image_path=None)

    assert result["verification_id"].startswith("VRF-")
    cv = result["cv_evidence"]
    assert cv["cv_checked"] is False
    assert cv["cv_status"] == "NOT_CHECKED"
    assert cv["seal_status"] == "NOT_CHECKED"
    assert cv["signature_status"] == "NOT_CHECKED"
    assert cv["authenticity_verified"] is False
    assert "unverified" in cv["authenticity_note"].lower()


def test_verification_with_missing_image_file():
    """Verify missing image file on disk does not crash and reports NOT_CHECKED with reason."""
    confirmed = {
        "deed_number": "DEED-TEST-MISSING",
        "dag_plot_number": "9044",
        "transferred_area_decimal": 2.5,
    }
    result = service.verify_transaction(confirmed_fields=confirmed, image_path="non_existent_image_file_9999.png")

    cv = result["cv_evidence"]
    assert cv["cv_status"] == "NOT_CHECKED"
    assert cv["cv_error_reason"] is not None
    assert "not found" in cv["cv_error_reason"].lower()


def test_verification_with_corrupt_image_file(tmp_path):
    """Verify corrupt/invalid image file reports INCONCLUSIVE gracefully without crashing."""
    bad_img = tmp_path / "corrupt_deed.png"
    bad_img.write_text("This is not a real PNG image content.")

    confirmed = {
        "deed_number": "DEED-TEST-CORRUPT",
        "dag_plot_number": "9044",
        "transferred_area_decimal": 2.0,
    }
    result = service.verify_transaction(confirmed_fields=confirmed, image_path=str(bad_img))

    cv = result["cv_evidence"]
    assert cv["cv_status"] == "INCONCLUSIVE"
    assert cv["cv_error_reason"] is not None
    assert cv["visual_anomaly_score"] == 0.0
    assert cv["authenticity_verified"] is False


def test_ml_score_calibration():
    """Verify XGBoost risk calibration thresholds map into truthful categories."""
    confirmed = {
        "deed_number": "DEED-TEST-CALIB",
        "dag_plot_number": "9044",
        "transferred_area_decimal": 3.0,
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-01",
    }
    result = service.verify_transaction(confirmed_fields=confirmed)

    score = result.get("ml_risk_score")
    calibration = result.get("ml_calibration")
    assert calibration in ["LOW_RISK", "MODERATE_RISK", "ELEVATED_RISK", "STATUTORY_FALLBACK"]

    if score is not None:
        if score < 0.25:
            assert calibration == "LOW_RISK"
        elif score < 0.65:
            assert calibration == "MODERATE_RISK"
        else:
            assert calibration == "ELEVATED_RISK"


def test_fallback_statutory_when_ml_disabled(monkeypatch):
    """Verify that when XGBoost model is None, service falls back to statutory rules without error."""
    # Temporarily set xgb_model to None
    monkeypatch.setattr(service, "xgb_model", None)

    confirmed = {
        "deed_number": "DEED-TEST-FALLBACK",
        "dag_plot_number": "9044",
        "transferred_area_decimal": 3.0,
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-01",
    }
    result = service.verify_transaction(confirmed_fields=confirmed)

    assert result["ml_model_fallback"] is True
    assert result["overall_status"] in ["CLEAR_FOR_STANDARD_PROCESSING", "REVIEW_REQUIRED", "CONFIRMED_INCONSISTENCY"]
    assert "SYNTHETIC DEMO" in result["synthetic_disclaimer"]
