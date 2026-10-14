"""Tests deterministic verification engine logic, rule trigger fidelity, and evidence categorization."""

import pytest
from src.landguard_models.verification_rules import evaluate_verification_rules


def test_clean_transaction_passes_all_rules():
    parcel = {"total_area_decimal": 15.0, "parcel_id": "PAR-TEST", "dag_plot_number": 302}
    txn = {
        "transferred_area_decimal": 10.0,
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": ["OWN-01"],
        "mutation_case_no": "MUT-2023-111",
    }
    mutations = [{"mutation_case_no": "MUT-2023-111", "status": "APPROVED"}]
    doc_ev = {
        "doc_dag_plot_number": 302,
        "doc_transferred_area_decimal": 10.0,
        "cv_seal_present": True,
        "cv_visual_anomaly_score": 0.05,
    }

    is_risk, score, findings = evaluate_verification_rules(
        txn, parcel, history_txns=[], mutations=mutations,
        document_evidence=doc_ev, include_document_evidence=True
    )
    assert is_risk is False
    assert score <= 0.10
    assert len(findings) == 0


def test_rule_area_excess_capacity():
    parcel = {"total_area_decimal": 15.0, "dag_plot_number": 302}
    txn = {
        "transferred_area_decimal": 25.0,  # Exceeds capacity
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": ["OWN-01"],
    }
    is_risk, score, findings = evaluate_verification_rules(txn, parcel, history_txns=[])
    assert is_risk is True
    viol = next(f for f in findings if f["rule_code"] == "RULE_AREA_EXCEEDS_CAPACITY")
    assert viol["category"] == "CONFIRMED_INCONSISTENCY"
    assert viol["severity"] == "CRITICAL"


def test_rule_plot_mismatch():
    parcel = {"total_area_decimal": 15.0, "dag_plot_number": 302}
    txn = {
        "transferred_area_decimal": 10.0,
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": ["OWN-01"],
    }
    doc_ev = {"doc_dag_plot_number": 999, "cv_seal_present": True, "cv_visual_anomaly_score": 0.0}
    is_risk, score, findings = evaluate_verification_rules(
        txn, parcel, history_txns=[], document_evidence=doc_ev, include_document_evidence=True
    )
    assert is_risk is True
    viol = next(f for f in findings if f["rule_code"] == "RULE_PLOT_MISMATCH_WITH_KHATIAN")
    assert viol["category"] == "CONFIRMED_INCONSISTENCY"
    assert "999" in viol["reason"]


def test_rule_broken_chain_and_missing_evidence():
    parcel = {"total_area_decimal": 15.0, "dag_plot_number": 302}
    txn = {
        "transferred_area_decimal": 10.0,
        "previous_deed_ref": "DEED-1999-5555",
        "seller_ids": ["OWN-01"],
    }

    # Positive case: history registry exists, but deed is missing -> CONFIRMED_INCONSISTENCY
    history = [{"deed_number": "DEED-2005-1111", "transaction_id": "TXN-01", "buyer_ids": ["OWN-01"], "seller_ids": ["OWN-00"]}]
    is_risk, _, findings = evaluate_verification_rules(txn, parcel, history_txns=history)
    assert is_risk is True
    viol = next(f for f in findings if f["rule_code"] == "RULE_BROKEN_CHAIN_OF_TITLE")
    assert viol["category"] == "CONFIRMED_INCONSISTENCY"

    # Missing evidence case: history is None -> MISSING_EVIDENCE
    is_risk2, _, findings2 = evaluate_verification_rules(txn, parcel, history_txns=None)
    viol2 = next(f for f in findings2 if f["rule_code"] == "RULE_BROKEN_CHAIN_OF_TITLE")
    assert viol2["category"] == "MISSING_EVIDENCE"


def test_rule_conflicting_double_disposition():
    parcel = {"total_area_decimal": 15.0, "dag_plot_number": 302}
    seller_id = "OWN-SELLER-01"
    txn = {
        "transaction_id": "TXN-CURRENT",
        "transferred_area_decimal": 10.0,
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": [seller_id],
    }
    # Prior transaction where seller already sold 10.0 decimals on a 15.0 decimal parcel (cumulative 20.0 > 15.0)
    history = [
        {
            "transaction_id": "TXN-PRIOR-SALE",
            "deed_number": "DEED-2022-7777",
            "transferred_area_decimal": 10.0,
            "seller_ids": [seller_id],
            "buyer_ids": ["OWN-COMPETING-BUYER"]
        }
    ]
    is_risk, score, findings = evaluate_verification_rules(txn, parcel, history_txns=history)
    assert is_risk is True
    viol = next(f for f in findings if f["rule_code"] == "RULE_CONFLICTING_DOUBLE_DISPOSITION")
    assert viol["category"] == "CONFIRMED_INCONSISTENCY"
    assert viol["severity"] == "CRITICAL"


def test_rule_unverified_and_pending_mutation_record():
    parcel = {"total_area_decimal": 15.0, "dag_plot_number": 302}
    txn = {
        "transferred_area_decimal": 10.0,
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": ["OWN-01"],
        "mutation_case_no": "MUT-2024-UNREGISTERED",
    }
    mutations = [{"mutation_case_no": "MUT-2024-LEGIT", "status": "APPROVED"}]
    is_risk, _, findings = evaluate_verification_rules(txn, parcel, history_txns=[], mutations=mutations)
    assert is_risk is True
    viol = next(f for f in findings if f["rule_code"] == "RULE_UNVERIFIED_MUTATION_RECORD")
    assert viol["category"] == "CONFIRMED_INCONSISTENCY"

    # Pending mutation should produce REVIEW_REQUIRED and not auto-flag as confirmed fraud by itself
    txn_pending = dict(txn, mutation_case_no="MUT-2024-PENDING")
    muts_pending = [{"mutation_case_no": "MUT-2024-PENDING", "status": "PENDING"}]
    is_risk_p, _, findings_p = evaluate_verification_rules(txn_pending, parcel, history_txns=[], mutations=muts_pending)
    assert is_risk_p is False
    viol_p = next(f for f in findings_p if f["rule_code"] == "RULE_MUTATION_PENDING_REVIEW")
    assert viol_p["category"] == "REVIEW_REQUIRED"


def test_rule_mandatory_seal_and_visual_tampering():
    parcel = {"total_area_decimal": 15.0, "dag_plot_number": 302}
    txn = {
        "transferred_area_decimal": 10.0,
        "previous_deed_ref": "INHERITED_ANCESTRAL_CS_RECORD",
        "seller_ids": ["OWN-01"],
    }
    doc_ev = {
        "doc_dag_plot_number": 302,
        "doc_transferred_area_decimal": 10.0,
        "cv_seal_present": False,
        "cv_visual_anomaly_detected": True,
        "cv_visual_anomaly_score": 0.85,
    }
    is_risk, _, findings = evaluate_verification_rules(
        txn, parcel, history_txns=[], document_evidence=doc_ev, include_document_evidence=True
    )
    assert is_risk is True
    assert any(f["rule_code"] == "RULE_MANDATORY_REGISTRAR_SEAL_ABSENT" and f["category"] == "CONFIRMED_INCONSISTENCY" for f in findings)
    assert any(f["rule_code"] == "RULE_VISUAL_TAMPERING_DETECTED" and f["category"] == "CONFIRMED_INCONSISTENCY" for f in findings)
