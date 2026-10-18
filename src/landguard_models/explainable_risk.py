"""Phase 6 — Connects observed registry, OCR, and computer-vision evidence to explainable
human-review risk assessments while keeping deterministic rules and ML scores independently auditable."""

from typing import Dict, Any, List, Optional
from .build_features import extract_record_features
from .verification_rules import evaluate_verification_rules

FEATURE_SOURCE_MAP = {
    "transferred_area_decimal": "REGISTRY_DEED_RECORD",
    "parcel_total_area_decimal": "CADASTRAL_PARCEL_SURVEY",
    "area_ratio": "RELATIONAL_JOIN (Deed vs Parcel)",
    "area_excess_flag": "RELATIONAL_JOIN (Deed vs Parcel)",
    "cumulative_seller_area_ratio": "RELATIONAL_CHAIN_HISTORY",
    "price_per_decimal": "REGISTRY_DEED_RECORD",
    "has_previous_deed_ref": "REGISTRY_DEED_RECORD",
    "is_ancestral_ref": "REGISTRY_DEED_RECORD",
    "previous_deed_verified_flag": "RELATIONAL_CHAIN_HISTORY",
    "chain_length": "RELATIONAL_CHAIN_HISTORY",
    "seller_was_previous_buyer": "RELATIONAL_CHAIN_HISTORY",
    "mutation_present": "MUTATION_REVENUE_REGISTER",
    "mutation_pending_flag": "MUTATION_REVENUE_REGISTER",
    "tax_year_delta": "TAX_DAKHILA_REGISTER",
    "conflicting_sale_flag": "RELATIONAL_CHAIN_HISTORY",
    "doc_plot_discrepancy_flag": "OCR_DOCUMENT_EVIDENCE",
    "doc_area_discrepancy_flag": "OCR_DOCUMENT_EVIDENCE",
    "cv_seal_absent_flag": "VISION_PRESENCE_EVIDENCE",
    "cv_visual_anomaly_score": "VISION_ALTERATION_EVIDENCE",
}


def build_explainable_risk_assessment(
    txn: Dict[str, Any],
    parcel: Dict[str, Any],
    history_txns: Optional[List[Dict[str, Any]]] = None,
    mutations: Optional[List[Dict[str, Any]]] = None,
    document_evidence: Optional[Dict[str, Any]] = None,
    ml_risk_probability: Optional[float] = None,
    ml_threshold: float = 0.50,
    include_document_evidence: bool = True,
    cadastral_found: bool = True,
) -> Dict[str, Any]:
    """
    Constructs a structured, auditable risk assessment distinguishing:
      - CONFIRMED_INCONSISTENCY: verifiable contradiction in available evidence
      - MISSING_EVIDENCE: required verification source or field is absent
      - REVIEW_REQUIRED: ambiguous or pending administrative state requiring officer check
      - RISK_INDICATOR: statistical/ML model or heuristic indicates elevated risk without confirmed contradiction
    Never labels a model prediction as confirmed legal fraud.
    """
    feats = extract_record_features(
        txn=txn,
        parcel=parcel,
        history_txns=history_txns,
        mutations=mutations,
        document_evidence=document_evidence,
        include_document_evidence=include_document_evidence and (document_evidence is not None),
    )

    is_rule_flagged, rule_score, findings = evaluate_verification_rules(
        txn=txn,
        parcel=parcel,
        history_txns=history_txns,
        mutations=mutations,
        document_evidence=document_evidence,
        include_document_evidence=include_document_evidence,
        cadastral_found=cadastral_found,
    )

    # Check if ML score independently elevates risk when no hard contradiction was confirmed
    # ONLY when cadastral parcel is indexed and essential transaction evidence is present
    seller_present = bool(txn.get("seller_ids"))
    area_present = txn.get("has_transferred_area_specified", True) and float(txn.get("transferred_area_decimal", 0.0)) > 0.0
    can_elevate_ml = cadastral_found and seller_present and area_present

    if can_elevate_ml and ml_risk_probability is not None and ml_risk_probability >= ml_threshold:
        has_confirmed = any(f["category"] == "CONFIRMED_INCONSISTENCY" for f in findings)
        if not has_confirmed:
            findings.append({
                "rule_code": "ML_ELEVATED_RISK_SCORE",
                "category": "RISK_INDICATOR",
                "severity": "MEDIUM",
                "evidence_source": "SUPERVISED_ML_MODEL",
                "reason": (
                    f"Supervised risk model assigned elevated risk score ({ml_risk_probability:.3f} >= {ml_threshold:.2f}) "
                    "based on multi-feature transactional profile; no standalone statutory contradiction confirmed."
                ),
            })

    categories_present = sorted({f["category"] for f in findings})
    if "CONFIRMED_INCONSISTENCY" in categories_present:
        overall_status = "CONFIRMED_INCONSISTENCY"
        recommended_action = (
            "HOLD_FOR_STATUTORY_VERIFICATION: Inspect physical volume register, Khatian survey sheet, "
            "and Namzari mutation dossier to resolve confirmed evidentiary contradiction."
        )
    elif "MISSING_EVIDENCE" in categories_present:
        overall_status = "MISSING_EVIDENCE"
        recommended_action = (
            "REQUEST_MISSING_RECORDS: Obtain missing historical deed index or mutation register extract "
            "before completing verification."
        )
    elif "REVIEW_REQUIRED" in categories_present:
        overall_status = "REVIEW_REQUIRED"
        recommended_action = (
            "MANUAL_OFFICER_REVIEW: Verify pending Namzari mutation status, subdivision sketch, "
            "or initialed clerical rectification mark."
        )
    elif "RISK_INDICATOR" in categories_present:
        overall_status = "RISK_INDICATOR"
        recommended_action = (
            "SECONDARY_SCREENING_RECOMMENDED: Statistical or heuristic risk indicators present "
            "(e.g., tax arrears or valuation gap); perform secondary clerk review."
        )
    else:
        overall_status = "CLEAR_FOR_STANDARD_PROCESSING"
        recommended_action = "PROCEED_WITH_STANDARD_REVIEW: No statutory contradictions or risk indicators observed."

    missing_or_uncertain: List[str] = [
        f["reason"] for f in findings if f["category"] in ("MISSING_EVIDENCE", "REVIEW_REQUIRED")
    ]
    if include_document_evidence and document_evidence is None:
        missing_or_uncertain.append("Physical document OCR/Vision evidence was not provided for inspection.")

    observed_evidence_with_sources = {
        k: {
            "value": v,
            "source": FEATURE_SOURCE_MAP.get(k, "UNKNOWN_SOURCE"),
        }
        for k, v in feats.items()
    }

    explanation_lines = [f"[{f['category']}] ({f['rule_code']}): {f['reason']}" for f in findings]
    if not explanation_lines:
        explanation_lines.append("All checked registry, chain-of-title, and mutation indicators are consistent.")

    return {
        "transaction_id": txn.get("transaction_id"),
        "parcel_id": parcel.get("parcel_id"),
        "overall_assessment_category": overall_status,
        "risk_categories_present": categories_present,
        "rule_engine_flagged": is_rule_flagged,
        "rule_engine_score": rule_score,
        "ml_model_score": round(float(ml_risk_probability), 4) if (ml_risk_probability is not None and can_elevate_ml) else None,
        "ml_threshold_used": round(float(ml_threshold), 4),
        "rules_triggered": findings,
        "observed_evidence": observed_evidence_with_sources,
        "missing_or_uncertain_evidence": missing_or_uncertain,
        "explanation_summary": " | ".join(explanation_lines),
        "recommended_human_action": recommended_action,
        "decision_support_disclaimer": (
            "This assessment supports human administrative review only and does NOT constitute "
            "judicial proof of fraud or automatic legal invalidation."
        ),
    }
