"""Comprehensive regression tests covering all 12 Phase-7 verification requirements:
- Anti-leakage and forbidden oracle column rejection
- Training-to-inference feature parity
- Multi-entity group-disjoint split verification (parcel, seller, scenario, template cohort)
- Scenario reproducibility with fixed seed
- Document watermark and bounding box validity
- Multi-alteration CV detection across all 4 alteration types
- Bengali OCR matra realignment and digit normalization
- Explainable risk semantics (CONFIRMED_INCONSISTENCY, MISSING_EVIDENCE, REVIEW_REQUIRED, RISK_INDICATOR)
"""

import random
import pandas as pd
import pytest
from PIL import Image, ImageDraw

from src.landguard_data.generate_entities import generate_entities
from src.landguard_data.generate_scenarios import create_scenario, SCENARIO_TYPES
from src.landguard_data.generate_documents import build_sale_deed_document
from src.landguard_data.render_documents import render_document
from src.landguard_data.build_splits import assign_grouped_splits, verify_leakage_free
from src.landguard_models.build_features import (
    validate_no_leakage,
    validate_feature_matrix_columns,
    build_feature_dataframe,
    extract_inference_features,
    FORBIDDEN_SIMULATION_KEYS,
)
from src.landguard_models.explainable_risk import build_explainable_risk_assessment
from src.landguard_vision.visual_anomaly_baseline import (
    detect_visual_anomalies,
    inject_controlled_tampering,
    ALTERATION_TYPES,
)
from src.landguard_vision.run_ocr import _realign_unshaped_bengali_matras, _clean_ocr_line


def test_forbidden_oracle_keys_rejected_on_transaction():
    for bad_key in ["has_visual_anomaly", "has_seal", "claimed_dag_plot_number", "is_fraud_risk", "ground_truth_label", "simulator_audit_metadata"]:
        bad_txn = {"transaction_id": "TXN-12345678", bad_key: True}
        with pytest.raises(ValueError, match="Target leakage violation"):
            validate_no_leakage(bad_txn)


def test_forbidden_columns_rejected_in_feature_matrix():
    df = pd.DataFrame([{"transferred_area_decimal": 10.0, "visual_tampering_flag": 1.0}])
    with pytest.raises(ValueError, match="Forbidden or leaked columns"):
        validate_feature_matrix_columns(df, allow_document_evidence=True)


def test_training_to_inference_feature_parity():
    owners, parcels = generate_entities(count_owners=12, count_parcels=2, seed=42)
    scen, txns, muts, _ = create_scenario(SCENARIO_TYPES[0], parcels[0], owners[:6], random.Random(42))
    record = {
        "scenario_id": scen["scenario_id"],
        "is_fraud_risk": scen["is_fraud_risk"],
        "parcel": parcels[0],
        "transaction": txns[-1],
        "history_transactions": txns[:-1],
        "mutations": muts,
        "document_evidence": scen["document_evidence"],
    }

    for inc_doc in (False, True):
        X_train_df, _, _ = build_feature_dataframe([record], include_document_evidence=inc_doc)
        X_infer_df = extract_inference_features(
            txn=record["transaction"],
            parcel=record["parcel"],
            history_txns=record["history_transactions"],
            mutations=record["mutations"],
            document_evidence=record["document_evidence"],
            include_document_evidence=inc_doc,
        )
        assert list(X_train_df.columns) == list(X_infer_df.columns)
        pd.testing.assert_frame_equal(X_train_df, X_infer_df)


def test_scenario_reproducibility_and_clean_separation():
    owners, parcels = generate_entities(count_owners=12, count_parcels=2, seed=99)
    scen_type = next(s for s in SCENARIO_TYPES if s[0] == "EXAGGERATED_LAND_AREA")
    s1, t1, m1, tx1 = create_scenario(scen_type, parcels[0], owners[:6], random.Random(123))
    s2, t2, m2, tx2 = create_scenario(scen_type, parcels[0], owners[:6], random.Random(123))
    assert s1 == s2
    assert t1 == t2
    assert m1 == m2
    assert tx1 == tx2
    # Ensure zero oracle keys exist on transaction records
    for t in t1:
        validate_no_leakage(t)
    assert "document_evidence" in s1
    assert "simulator_audit_metadata" in s1


def test_multi_entity_group_disjoint_splits():
    owners, parcels = generate_entities(count_owners=180, count_parcels=30, seed=42)
    records = []
    rng = random.Random(42)
    for i in range(30):
        cohort = owners[i * 6 : (i + 1) * 6]
        scen, txns, muts, _ = create_scenario(SCENARIO_TYPES[i % len(SCENARIO_TYPES)], parcels[i], cohort, rng)
        records.append({
            "scenario_id": scen["scenario_id"],
            "parcel_id": parcels[i]["parcel_id"],
            "primary_seller_id": txns[-1]["seller_ids"][0],
            "template_cohort": f"TMPL-{(i // 3) + 1:02d}",
        })

    splits = assign_grouped_splits(records, group_key="template_cohort", seed=42)
    for key in ["template_cohort", "parcel_id", "primary_seller_id", "scenario_id"]:
        res = verify_leakage_free(splits, group_key=key)
        assert res["is_leakage_free"] is True


def test_rendered_document_watermark_and_bounding_boxes():
    owners, parcels = generate_entities(count_owners=6, count_parcels=1, seed=42)
    scen, txns, _, _ = create_scenario(SCENARIO_TYPES[0], parcels[0], owners, random.Random(42))
    doc = build_sale_deed_document(txns[-1], parcels[0], owners[0], owners[1], template_id="TMPL-DEED-1")
    assert doc["watermark_text"] == "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"
    img, full_text, bboxes, has_sig, has_seal = render_document(doc)
    w, h = img.size
    assert "DEED OF SALE" in full_text
    assert has_sig is True
    assert has_seal is True
    for box_name, box in bboxes.items():
        y1, x1, y2, x2 = box
        assert 0 <= y1 < y2 <= h, f"Invalid y bounds for {box_name}: {box}"
        assert 0 <= x1 < x2 <= w, f"Invalid x bounds for {box_name}: {box}"


def test_all_four_controlled_alteration_types_detected():
    clean = Image.new("RGB", (900, 1100), color=(248, 248, 245))
    draw = ImageDraw.Draw(clean)
    for col_x in [100, 250, 400, 550]:
        draw.rectangle([col_x, 150, col_x + 140, 200], outline=(60, 60, 60), width=1)

    for idx, alt_type in enumerate(ALTERATION_TYPES):
        tampered, meta = inject_controlled_tampering(clean, tampering_type=alt_type, seed=idx + 10)
        res = detect_visual_anomalies(tampered)
        assert res["has_visual_anomaly"] is True, f"Failed to detect alteration type {alt_type}"
        assert res["visual_anomaly_score"] > 0.0


def test_bengali_matra_realignment_and_digit_cleaning():
    from src.landguard_vision.evaluate_ocr import normalize_text
    # Unshaped Pillow rendering of C1 + M + C2 causes Tesseract to decode C1 + C2 + M (e.g. 'তারখি', 'জলোর')
    unshaped = "SYNTHETIC DEMO তারখি ও জলোর নং ১২৩৪"
    realigned = _realign_unshaped_bengali_matras(unshaped)
    cleaned = normalize_text(_clean_ocr_line(realigned))
    assert "তারিখ" in cleaned
    assert "জেলার" in cleaned
    assert "1234" in cleaned
    assert "SYNTHETIC DEMO" not in cleaned


def test_explainable_risk_four_semantic_categories():
    parcel = {"total_area_decimal": 15.0, "parcel_id": "PAR-TEST", "dag_plot_number": 302}
    txn = {
        "transaction_id": "TXN-12345678",
        "transferred_area_decimal": 22.0,  # Triggers CONFIRMED_INCONSISTENCY (area > 15.0)
        "consideration_bdt": 500000.0,
        "previous_deed_ref": "DEED-1998-999",
        "seller_ids": ["OWN-01"],
        "mutation_case_no": "MUT-2024-PENDING",
        "execution_date": "2024-05-01",
        "tax_clearance_year": 2020,        # Tax lag = 4 yrs -> RISK_INDICATOR
    }
    mutations = [{"mutation_case_no": "MUT-2024-PENDING", "status": "PENDING"}]  # Triggers REVIEW_REQUIRED
    doc_ev = {
        "doc_dag_plot_number": 302,
        "doc_transferred_area_decimal": 22.0,
        "cv_seal_present": False,          # Triggers REVIEW_REQUIRED
        "cv_visual_anomaly_score": 0.80,   # Triggers REVIEW_REQUIRED
    }
    # Passing history_txns=None triggers MISSING_EVIDENCE for previous_deed_ref
    report = build_explainable_risk_assessment(
        txn=txn,
        parcel=parcel,
        history_txns=None,
        mutations=mutations,
        document_evidence=doc_ev,
        include_document_evidence=True,
        ml_risk_probability=0.92,
    )
    cats = set(report["risk_categories_present"])
    assert "CONFIRMED_INCONSISTENCY" in cats
    assert "MISSING_EVIDENCE" in cats
    assert "REVIEW_REQUIRED" in cats
    assert "RISK_INDICATOR" in cats
    assert report["overall_assessment_category"] == "CONFIRMED_INCONSISTENCY"
    assert "HOLD_FOR_STATUTORY_VERIFICATION" in report["recommended_human_action"]
