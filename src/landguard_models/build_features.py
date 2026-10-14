"""Feature engineering engine for land record risk modeling with strict leakage prevention
and verified parity between training/evaluation and inference paths."""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# Purely observable structured registry & relational features (Regime A & Regime B default)
REGISTRY_FEATURE_COLUMNS = [
    "transferred_area_decimal",
    "parcel_total_area_decimal",
    "area_ratio",
    "area_excess_flag",
    "cumulative_seller_area_ratio",
    "price_per_decimal",
    "has_previous_deed_ref",
    "is_ancestral_ref",
    "previous_deed_verified_flag",
    "chain_length",
    "seller_was_previous_buyer",
    "mutation_present",
    "mutation_pending_flag",
    "tax_year_delta",
    "conflicting_sale_flag",
]

# Observable OCR + Computer Vision document features (added only when include_document_evidence=True in Regime C / E)
DOCUMENT_EVIDENCE_COLUMNS = [
    "doc_plot_discrepancy_flag",
    "doc_area_discrepancy_flag",
    "cv_seal_absent_flag",
    "cv_visual_anomaly_score",
]

# Default operational feature columns (Registry-only, zero oracle shortcut flags)
FEATURE_COLUMNS = list(REGISTRY_FEATURE_COLUMNS)
ALL_OBSERVABLE_FEATURE_COLUMNS = list(REGISTRY_FEATURE_COLUMNS) + list(DOCUMENT_EVIDENCE_COLUMNS)

# Comprehensive ban list of simulator-only, ground-truth, and old oracle shortcut keys
FORBIDDEN_SIMULATION_KEYS = {
    "injected_tampering",
    "injected_modifications",
    "expected_rule_violations",
    "visual_tampering_overlay",
    "has_visual_anomaly",
    "visual_anomaly_score",
    "seal_omitted",
    "has_seal",
    "claimed_dag_plot_number",
    "scenario_category",
    "fraud_category",
    "is_fraud_risk",
    "ground_truth_label",
    "simulator_audit_metadata",
    "explanation",
}

FORBIDDEN_FEATURE_MATRIX_COLUMNS = FORBIDDEN_SIMULATION_KEYS | {
    "visual_tampering_flag",
    "seal_omitted_flag",
    "plot_discrepancy_flag",
}
FORBIDDEN_FEATURE_NAMES = FORBIDDEN_FEATURE_MATRIX_COLUMNS


def validate_no_leakage(data: Dict[str, Any]) -> None:
    """
    Validates that no forbidden ground-truth simulation or oracle shortcut metadata
    is present in the transaction input during feature extraction.
    """
    for key in FORBIDDEN_SIMULATION_KEYS:
        if key in data and data[key] is not None and data[key] is not False:
            raise ValueError(
                f"Target leakage violation: Forbidden simulation/shortcut key '{key}' "
                f"was passed directly into inference feature extraction."
            )
        # Also block explicit boolean False for oracle keys like 'has_seal' on transaction
        if key in ("has_seal", "has_visual_anomaly", "claimed_dag_plot_number", "is_fraud_risk") and key in data:
            raise ValueError(
                f"Target leakage violation: Oracle key '{key}' must not be present on transaction records."
            )


def validate_feature_matrix_columns(
    df: pd.DataFrame,
    allow_document_evidence: bool = False
) -> None:
    """
    Fails immediately if any forbidden simulation or removed oracle column enters the feature matrix.
    """
    bad_cols = set(df.columns) & FORBIDDEN_FEATURE_MATRIX_COLUMNS
    if bad_cols:
        raise ValueError(
            f"Forbidden or leaked columns detected in feature matrix: {sorted(bad_cols)}"
        )
    allowed = set(REGISTRY_FEATURE_COLUMNS)
    if allow_document_evidence:
        allowed |= set(DOCUMENT_EVIDENCE_COLUMNS)
    unexpected = set(df.columns) - allowed
    if unexpected:
        raise ValueError(
            f"Unexpected unverified columns in feature matrix: {sorted(unexpected)}"
        )


def extract_record_features(
    txn: Dict[str, Any],
    parcel: Dict[str, Any],
    history_txns: Optional[List[Dict[str, Any]]] = None,
    mutations: Optional[List[Dict[str, Any]]] = None,
    document_evidence: Optional[Dict[str, Any]] = None,
    include_document_evidence: bool = False
) -> Dict[str, float]:
    """
    Extracts purely factual, pre-investigation transactional and relational attributes.
    First validates that no forbidden simulation or oracle keys exist on `txn`.
    When `include_document_evidence=True`, appends OCR/Vision document-evidence features
    derived from `document_evidence`.
    """
    validate_no_leakage(txn)

    p_area = float(parcel.get("total_area_decimal", 1.0))
    t_area = float(txn.get("transferred_area_decimal", 0.0))
    consideration = float(txn.get("consideration_bdt", 0.0))

    area_ratio = round(t_area / max(0.01, p_area), 4)
    area_excess = 1.0 if t_area > p_area * 1.01 else 0.0
    price_per_dec = round(consideration / max(0.01, t_area), 2)

    prev_ref = str(txn.get("previous_deed_ref", "") or "")
    is_ancestral = 1.0 if prev_ref == "INHERITED_ANCESTRAL_CS_RECORD" else 0.0
    has_prev = 1.0 if prev_ref and not is_ancestral else 0.0

    # Verify whether referenced prior deed exists in title chain indices
    is_prev_verified = 0.0
    if is_ancestral:
        is_prev_verified = 1.0
    elif history_txns and has_prev:
        is_prev_verified = 1.0 if any(h.get("deed_number") == prev_ref for h in history_txns) else 0.0

    # Check chain of title: was current seller the transferee in preceding conveyance?
    seller_id = txn["seller_ids"][0] if txn.get("seller_ids") else ""
    seller_was_buyer = 0.0
    chain_len = 1.0

    if history_txns:
        chain_len = float(len(history_txns))
        for h in history_txns:
            if h.get("transaction_id") != txn.get("transaction_id"):
                if seller_id in h.get("buyer_ids", []):
                    seller_was_buyer = 1.0
                    break
    else:
        seller_was_buyer = 1.0 if is_ancestral else 0.0

    # Namzari mutation check: distinguish APPROVED vs PENDING vs unverified/REJECTED
    mut_case = str(txn.get("mutation_case_no", "") or "")
    mutation_present = 0.0
    mutation_pending = 0.0
    if mut_case:
        if mutations is not None:
            matching_muts = [m for m in mutations if m.get("mutation_case_no") == mut_case]
            if any(m.get("status", "APPROVED") == "APPROVED" for m in matching_muts):
                mutation_present = 1.0
            elif any(m.get("status") == "PENDING" for m in matching_muts):
                mutation_pending = 1.0
        else:
            mutation_present = 1.0

    # Tax fiscal gap
    exec_yr = int(str(txn.get("execution_date", "2020"))[:4])
    tax_yr = int(txn.get("tax_clearance_year", exec_yr))
    tax_delta = float(max(0, exec_yr - tax_yr))

    # Cumulative disposition by seller across current title tenure (distinguishes valid partial subdivision from double sale)
    prior_seller_area = 0.0
    if history_txns and seller_id:
        acq_indices = [
            i for i, h in enumerate(history_txns)
            if seller_id in h.get("buyer_ids", [])
        ]
        last_acq_idx = max(acq_indices) if acq_indices else -1
        for i, h in enumerate(history_txns):
            if i > last_acq_idx and h.get("transaction_id") != txn.get("transaction_id") and seller_id in h.get("seller_ids", []):
                prior_seller_area += float(h.get("transferred_area_decimal", 0.0))

    cumulative_seller_area = prior_seller_area + t_area
    cumulative_seller_ratio = round(cumulative_seller_area / max(0.01, p_area), 4)
    conflicting_sale = 1.0 if (prior_seller_area > 0.0 and cumulative_seller_ratio > 1.05) else 0.0

    feats: Dict[str, float] = {
        "transferred_area_decimal": t_area,
        "parcel_total_area_decimal": p_area,
        "area_ratio": area_ratio,
        "area_excess_flag": area_excess,
        "cumulative_seller_area_ratio": cumulative_seller_ratio,
        "price_per_decimal": price_per_dec,
        "has_previous_deed_ref": has_prev,
        "is_ancestral_ref": is_ancestral,
        "previous_deed_verified_flag": is_prev_verified,
        "chain_length": chain_len,
        "seller_was_previous_buyer": seller_was_buyer,
        "mutation_present": mutation_present,
        "mutation_pending_flag": mutation_pending,
        "tax_year_delta": tax_delta,
        "conflicting_sale_flag": conflicting_sale,
    }

    if include_document_evidence:
        doc_ev = document_evidence or {}
        parcel_dag = parcel.get("dag_plot_number")
        doc_dag = doc_ev.get("doc_dag_plot_number", parcel_dag)
        doc_plot_disc = 1.0 if (doc_dag is not None and parcel_dag is not None and str(doc_dag) != str(parcel_dag)) else 0.0

        doc_area = float(doc_ev.get("doc_transferred_area_decimal", t_area))
        doc_area_disc = 1.0 if abs(doc_area - t_area) > 0.5 else 0.0

        cv_seal_absent = 1.0 if not doc_ev.get("cv_seal_present", True) else 0.0
        cv_anom_score = float(doc_ev.get("cv_visual_anomaly_score", 0.0))

        feats["doc_plot_discrepancy_flag"] = doc_plot_disc
        feats["doc_area_discrepancy_flag"] = doc_area_disc
        feats["cv_seal_absent_flag"] = cv_seal_absent
        feats["cv_visual_anomaly_score"] = round(cv_anom_score, 4)

    return feats


def extract_inference_features(
    txn: Dict[str, Any],
    parcel: Dict[str, Any],
    history_txns: Optional[List[Dict[str, Any]]] = None,
    mutations: Optional[List[Dict[str, Any]]] = None,
    document_evidence: Optional[Dict[str, Any]] = None,
    include_document_evidence: bool = False
) -> pd.DataFrame:
    """
    Production inference feature builder guaranteed to use the exact same logic
    and column ordering as `build_feature_dataframe`.
    """
    feats = extract_record_features(
        txn=txn,
        parcel=parcel,
        history_txns=history_txns,
        mutations=mutations,
        document_evidence=document_evidence,
        include_document_evidence=include_document_evidence,
    )
    cols = REGISTRY_FEATURE_COLUMNS + (DOCUMENT_EVIDENCE_COLUMNS if include_document_evidence else [])
    df = pd.DataFrame([feats], columns=cols)
    validate_feature_matrix_columns(df, allow_document_evidence=include_document_evidence)
    return df


def build_feature_dataframe(
    dataset_records: List[Dict[str, Any]],
    include_document_evidence: bool = False
) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    rows = []
    labels = []
    scenarios = []

    cols = REGISTRY_FEATURE_COLUMNS + (DOCUMENT_EVIDENCE_COLUMNS if include_document_evidence else [])

    for item in dataset_records:
        txn = item["transaction"]
        parcel = item["parcel"]
        history = item.get("history_transactions", [])
        mutations = item.get("mutations", [])
        doc_ev = item.get("document_evidence")

        feats = extract_record_features(
            txn=txn,
            parcel=parcel,
            history_txns=history,
            mutations=mutations,
            document_evidence=doc_ev,
            include_document_evidence=include_document_evidence,
        )
        rows.append(feats)

        labels.append(1 if item.get("is_fraud_risk", False) else 0)
        scenarios.append(item.get("scenario_id", "SCN-DEFAULT"))

    df_x = pd.DataFrame(rows, columns=cols)
    validate_feature_matrix_columns(df_x, allow_document_evidence=include_document_evidence)
    y = np.array(labels, dtype=int)

    return df_x, y, scenarios
