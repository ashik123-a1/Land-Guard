"""Tests machine learning feature extraction, model fitting, and evaluation."""

import pytest
import pandas as pd
import numpy as np
from src.landguard_models.build_features import (
    extract_record_features,
    validate_no_leakage,
    FEATURE_COLUMNS,
    FORBIDDEN_SIMULATION_KEYS
)
from src.landguard_models.train_baselines import train_logistic_regression, train_random_forest
from src.landguard_models.train_xgboost import train_xgboost_model


def test_feature_extraction_and_training():
    parcel = {"total_area_decimal": 20.0, "parcel_id": "PAR-TEST01", "dag_plot_number": 501}
    txn = {
        "transferred_area_decimal": 25.0, # exceeds capacity
        "consideration_bdt": 2500000.0,
        "previous_deed_ref": "DEED-2015-1100",
        "seller_ids": ["OWN-01"],
        "mutation_case_no": "MUT-2022-100",
        "execution_date": "2022-05-10",
        "tax_clearance_year": 2022,
    }
    doc_ev = {
        "doc_dag_plot_number": 501,
        "doc_transferred_area_decimal": 25.0,
        "cv_seal_present": True,
        "cv_visual_anomaly_score": 0.0,
    }
    
    feats = extract_record_features(txn, parcel, document_evidence=doc_ev, include_document_evidence=False)
    assert set(feats.keys()) == set(FEATURE_COLUMNS)
    assert feats["area_excess_flag"] == 1.0
    
    feats_doc = extract_record_features(txn, parcel, document_evidence=doc_ev, include_document_evidence=True)
    assert feats_doc["doc_plot_discrepancy_flag"] == 0.0
    
    # Dummy training test
    X = pd.DataFrame([feats] * 10)
    y = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    
    lr, scaler = train_logistic_regression(X, y)
    assert lr is not None
    
    rf = train_random_forest(X, y)
    assert rf is not None
    
    xgb = train_xgboost_model(X, y, X, y)
    assert xgb is not None


def test_no_simulation_metadata_in_features():
    """Asserts that simulation metadata cannot be passed to inference and raises ValueError immediately."""
    for forbidden_key in FORBIDDEN_SIMULATION_KEYS:
        leaky_input = {forbidden_key: "tampered_value"}
        with pytest.raises(ValueError, match="Target leakage violation"):
            validate_no_leakage(leaky_input)
            
    # Verify extract_record_features rejects injected_tampering if maliciously attached to transaction
    parcel = {"total_area_decimal": 20.0, "dag_plot_number": 501}
    txn = {
        "transferred_area_decimal": 10.0,
        "consideration_bdt": 1000000.0,
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": ["OWN-01"],
        "mutation_case_no": "MUT-2022-100",
        "execution_date": "2022-05-10",
        "tax_clearance_year": 2022,
        "injected_tampering": {"field": "dag_plot_number", "is_tampered": True}
    }
    with pytest.raises(ValueError, match="Target leakage violation"):
        extract_record_features(txn, parcel)
