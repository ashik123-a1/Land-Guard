"""Unit tests for targeted synthetic expansion, 6-mechanism CV alterations,
Bengali numeral OCR extraction, and pre-1972 archival missing-evidence categorization."""

import os
import json
import pytest
import numpy as np
from PIL import Image, ImageDraw

from src.landguard_vision.visual_anomaly_baseline import (
    ALTERATION_TYPES,
    inject_controlled_tampering,
    detect_visual_anomalies,
)
from src.landguard_vision.run_ocr import extract_fields_from_text
from src.landguard_models.verification_rules import evaluate_verification_rules
from src.landguard_models.build_features import validate_no_leakage


def test_all_six_alteration_mechanisms_detected():
    assert len(ALTERATION_TYPES) == 6
    clean = Image.new("RGB", (900, 1100), color=(248, 248, 245))
    draw = ImageDraw.Draw(clean)
    for col_x in [100, 250, 400, 550]:
        draw.rectangle([col_x, 150, col_x + 140, 200], outline=(60, 60, 60), width=1)

    for idx, alt_type in enumerate(ALTERATION_TYPES):
        tampered, meta = inject_controlled_tampering(clean, tampering_type=alt_type, seed=idx + 10)
        res = detect_visual_anomalies(tampered)
        assert res["has_visual_anomaly"] is True, f"Failed to detect alteration {alt_type}"
        assert res["visual_anomaly_score"] > 0.0


def test_bengali_deed_and_khatian_number_extraction():
    # Bengali deed with slash format
    txt1 = "গণপ্রজাতন্ত্রী বাংলাদেশ সরকার | দলিল নং: ১২৩৪৫/২০২৩ | দাগ নং: ৯০৪৪ | জমি: ১০.৫০ শতক"
    f1 = extract_fields_from_text(txt1)
    assert f1.get("deed_number") == "DEED-2023-12345"
    assert f1.get("dag_plot_number") == "9044"
    assert f1.get("transferred_area_decimal") == "10.50"

    # Bengali deed with hyphen format and parenthetical plot
    txt2 = "সাব-রেজিস্ট্রি অফিস | দলিল নম্বর: ২০২৩-৮৮৯৯১ | দাগ (প্লট) নং: ৫৫৬৬ | খতিয়ান নম্বর: ৪৪৫৫"
    f2 = extract_fields_from_text(txt2)
    assert f2.get("deed_number") == "DEED-2023-88991"
    assert f2.get("dag_plot_number") == "5566"
    assert f2.get("khatian_number") == "4455"


def test_unindexed_pre1972_archive_is_missing_evidence():
    parcel = {"total_area_decimal": 20.0, "dag_plot_number": 401}
    txn = {
        "transaction_id": "TXN-CURRENT",
        "transferred_area_decimal": 12.0,
        "previous_deed_ref": "UNINDEXED_PRE1972_VOLUME_412",
        "seller_ids": ["OWN-99"],
    }
    history = [{"transaction_id": "TXN-PRIOR-01", "deed_number": "DEED-2001-9999", "buyer_ids": ["OWN-99"]}]
    is_risk, score, findings = evaluate_verification_rules(txn, parcel, history_txns=history)
    assert is_risk is False
    viol = next(f for f in findings if f["rule_code"] == "RULE_BROKEN_CHAIN_OF_TITLE")
    assert viol["category"] == "MISSING_EVIDENCE"
    assert viol["severity"] == "MEDIUM"


def test_targeted_expansion_records_and_manifest():
    rec_path = "data/targeted_expansion/records/targeted_records.json"
    mf_path = "data/targeted_expansion/manifests/targeted_manifest.json"
    assert os.path.exists(rec_path)
    assert os.path.exists(mf_path)

    with open(rec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = data["dataset_records"]
    assert len(records) == 100

    for r in records:
        validate_no_leakage(r["transaction"])

    with open(mf_path, "r", encoding="utf-8") as f:
        mf = json.load(f)
    assert len(mf["files"]) == 24
