"""Deterministic verification engine providing statutory checks, explainable findings,
and strict four-category evidence distinction:
- CONFIRMED_INCONSISTENCY: a specific, verifiable contradiction in available evidence
- MISSING_EVIDENCE: required information is absent
- REVIEW_REQUIRED: evidence is ambiguous or conflicting (e.g., pending mutation, clerical correction mark)
- RISK_INDICATOR: heuristic suggests elevated risk (e.g., multi-year tax arrears, fire-sale price)
"""

from typing import Dict, Any, List, Tuple, Optional


def evaluate_verification_rules(
    txn: Dict[str, Any],
    parcel: Dict[str, Any],
    history_txns: Optional[List[Dict[str, Any]]] = None,
    mutations: Optional[List[Dict[str, Any]]] = None,
    khatian_records: Optional[List[Dict[str, Any]]] = None,
    document_evidence: Optional[Dict[str, Any]] = None,
    include_document_evidence: bool = True
) -> Tuple[bool, float, List[Dict[str, Any]]]:
    """
    Evaluates transactional facts against statutory verification rules using real relational comparisons.
    Returns (is_flagged_risk, confidence_score, findings_list).
    """
    findings: List[Dict[str, Any]] = []

    t_area = float(txn.get("transferred_area_decimal", 0.0))
    p_area = float(parcel.get("total_area_decimal", 0.0))
    consideration = float(txn.get("consideration_bdt", 0.0))
    deed_type = str(txn.get("deed_type", "Sale Deed (Kabala)"))

    # 1. Statutory Cadastral Area Capacity Check
    if t_area > p_area * 1.01:
        findings.append({
            "rule_code": "RULE_AREA_EXCEEDS_CAPACITY",
            "category": "CONFIRMED_INCONSISTENCY",
            "severity": "CRITICAL",
            "evidence_source": "REGISTRY_RECORD",
            "reason": f"Transferred area ({t_area:.2f} dec) exceeds recorded cadastral parcel capacity ({p_area:.2f} dec)."
        })

    # 2. Chain of Title Continuity & Prior Deed Reference
    seller_id = txn["seller_ids"][0] if txn.get("seller_ids") else ""
    prev_ref = str(txn.get("previous_deed_ref", "") or "")
    is_ancestral = prev_ref == "INHERITED_ANCESTRAL_CS_RECORD"

    if prev_ref and not is_ancestral:
        if "UNINDEXED" in prev_ref or "DAMAGED_VOLUME" in prev_ref:
            findings.append({
                "rule_code": "RULE_BROKEN_CHAIN_OF_TITLE",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "RELATIONAL_HISTORY",
                "reason": f"Historical deed reference '{prev_ref}' corresponds to unindexed or damaged archival volume records."
            })
        elif history_txns is not None:
            deed_found = any(h.get("deed_number") == prev_ref for h in history_txns)
            if not deed_found:
                findings.append({
                    "rule_code": "RULE_BROKEN_CHAIN_OF_TITLE",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "HIGH",
                    "evidence_source": "RELATIONAL_HISTORY",
                    "reason": f"Referenced prior conveyance '{prev_ref}' cannot be traced in registry indices."
                })
        else:
            findings.append({
                "rule_code": "RULE_BROKEN_CHAIN_OF_TITLE",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "RELATIONAL_HISTORY",
                "reason": f"Historical deed registry records unavailable to trace prior conveyance '{prev_ref}'."
            })

    # 3. Seller Titleholder Verification in Preceding Chain
    if not is_ancestral and history_txns:
        seller_found_in_chain = any(
            seller_id in h.get("buyer_ids", [])
            for h in history_txns
            if h.get("transaction_id") != txn.get("transaction_id")
        )
        if not seller_found_in_chain:
            findings.append({
                "rule_code": "RULE_SELLER_NOT_TITLEHOLDER",
                "category": "CONFIRMED_INCONSISTENCY",
                "severity": "HIGH",
                "evidence_source": "RELATIONAL_HISTORY",
                "reason": f"Seller '{seller_id}' does not appear as transferee in preceding chain of title."
            })

    # 4. Conflicting Double Disposition vs. Valid Partial Subdivision
    if history_txns and seller_id:
        # Determine seller's most recent title acquisition index in preceding chain
        acq_indices = [
            i for i, h in enumerate(history_txns)
            if seller_id in h.get("buyer_ids", [])
        ]
        last_acq_idx = max(acq_indices) if acq_indices else -1

        # Only sales occurring after most recent acquisition belong to current title tenure
        prior_sales = [
            h for i, h in enumerate(history_txns)
            if i > last_acq_idx
            and h.get("transaction_id") != txn.get("transaction_id")
            and seller_id in h.get("seller_ids", [])
        ]
        if prior_sales:
            competing_deed = prior_sales[0].get("deed_number", "UNKNOWN")
            # Calculate cumulative area disposed by this seller
            prior_area_sum = sum(
                float(h.get("transferred_area_decimal", p_area))
                for h in prior_sales
            )
            if (prior_area_sum + t_area) > max(0.01, p_area) * 1.05:
                findings.append({
                    "rule_code": "RULE_CONFLICTING_DOUBLE_DISPOSITION",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "CRITICAL",
                    "evidence_source": "RELATIONAL_HISTORY",
                    "reason": (
                        f"Prior deed '{competing_deed}' detected where seller '{seller_id}' already conveyed "
                        f"{prior_area_sum:.2f} dec; cumulative transfer ({prior_area_sum + t_area:.2f} dec) exceeds parcel capacity ({p_area:.2f} dec)."
                    )
                })
            else:
                findings.append({
                    "rule_code": "RULE_PARTIAL_SUBDIVISION_CAPACITY_CHECK",
                    "category": "REVIEW_REQUIRED",
                    "severity": "LOW",
                    "evidence_source": "RELATIONAL_HISTORY",
                    "reason": (
                        f"Seller '{seller_id}' executed prior partial transfer '{competing_deed}' ({prior_area_sum:.2f} dec), "
                        f"within total parcel capacity ({p_area:.2f} dec). Verify subdivision sketch."
                    )
                })

    # 5. Namzari Mutation Record Verification (APPROVED vs PENDING vs REJECTED/UNVERIFIED)
    mut_no = str(txn.get("mutation_case_no", "") or "")
    if mut_no:
        if mutations is not None:
            matching_muts = [m for m in mutations if m.get("mutation_case_no") == mut_no]
            if not matching_muts:
                findings.append({
                    "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "HIGH",
                    "evidence_source": "MUTATION_REGISTER",
                    "reason": f"Mutation record reference '{mut_no}' is unverified in Land Revenue mutation records."
                })
            elif any(m.get("status") == "REJECTED" for m in matching_muts):
                findings.append({
                    "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "HIGH",
                    "evidence_source": "MUTATION_REGISTER",
                    "reason": f"Mutation case '{mut_no}' was REJECTED by Assistant Commissioner (Land)."
                })
            elif any(m.get("status") == "PENDING" for m in matching_muts):
                findings.append({
                    "rule_code": "RULE_MUTATION_PENDING_REVIEW",
                    "category": "REVIEW_REQUIRED",
                    "severity": "MEDIUM",
                    "evidence_source": "MUTATION_REGISTER",
                    "reason": f"Mutation case '{mut_no}' is currently PENDING administrative approval."
                })
        else:
            findings.append({
                "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "MUTATION_REGISTER",
                "reason": f"Land Revenue mutation register unavailable to verify record '{mut_no}'."
            })
    else:
        findings.append({
            "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
            "category": "MISSING_EVIDENCE",
            "severity": "MEDIUM",
            "evidence_source": "MUTATION_REGISTER",
            "reason": "No mutation case cited in transaction record."
        })

    # 6. Heuristic Risk Indicators (Tax Arrears & Abnormal Consideration)
    if "execution_date" in txn and "tax_clearance_year" in txn:
        exec_yr = int(str(txn["execution_date"])[:4])
        tax_yr = int(txn["tax_clearance_year"])
        if (exec_yr - tax_yr) >= 2:
            findings.append({
                "rule_code": "RULE_TAX_ARREARS_INDICATOR",
                "category": "RISK_INDICATOR",
                "severity": "LOW",
                "evidence_source": "REGISTRY_RECORD",
                "reason": f"Land development tax clearance lags deed execution by {exec_yr - tax_yr} years."
            })

    if consideration > 0 and t_area > 0 and "Correction" not in deed_type and "Inheritance" not in deed_type:
        ppd = consideration / max(0.01, t_area)
        if ppd < 65000.0:
            findings.append({
                "rule_code": "RULE_BELOW_MARKET_CONSIDERATION_INDICATOR",
                "category": "RISK_INDICATOR",
                "severity": "LOW",
                "evidence_source": "REGISTRY_RECORD",
                "reason": f"Reported consideration ({ppd:,.0f} BDT/dec) is substantially below typical mouza valuation."
            })

    # 7. Document-Level OCR & Vision Checks (Only evaluated when include_document_evidence=True)
    if include_document_evidence:
        doc_ev = document_evidence or {}
        registered_dag = parcel.get("dag_plot_number")
        claimed_dag = doc_ev.get("doc_dag_plot_number", txn.get("claimed_dag_plot_number"))
        if claimed_dag is not None and registered_dag is not None and str(claimed_dag) != str(registered_dag):
            findings.append({
                "rule_code": "RULE_PLOT_MISMATCH_WITH_KHATIAN",
                "category": "CONFIRMED_INCONSISTENCY",
                "severity": "CRITICAL",
                "evidence_source": "OCR_DOCUMENT_EVIDENCE",
                "reason": f"Deed cites plot #{claimed_dag}, which conflicts with registered survey dag #{registered_dag}."
            })

        has_seal = doc_ev.get("cv_seal_present", txn.get("has_seal", True))
        if not has_seal:
            if "Inheritance" in deed_type:
                findings.append({
                    "rule_code": "RULE_MANDATORY_REGISTRAR_SEAL_ABSENT",
                    "category": "REVIEW_REQUIRED",
                    "severity": "MEDIUM",
                    "evidence_source": "VISION_PRESENCE_EVIDENCE",
                    "reason": "Family succession memorandum lacks Sub-Registry seal; verify whether formal registration applies."
                })
            else:
                findings.append({
                    "rule_code": "RULE_MANDATORY_REGISTRAR_SEAL_ABSENT",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "HIGH",
                    "evidence_source": "VISION_PRESENCE_EVIDENCE",
                    "reason": "Official Sub-Registry authentication seal is missing from deed."
                })

        has_visual_anomaly = doc_ev.get("cv_visual_anomaly_detected", txn.get("has_visual_anomaly", False))
        anom_score = float(doc_ev.get("cv_visual_anomaly_score", 0.85 if has_visual_anomaly else 0.0))
        if has_visual_anomaly:
            if anom_score < 0.60 and "Correction" in deed_type:
                findings.append({
                    "rule_code": "RULE_VISUAL_TAMPERING_DETECTED",
                    "category": "REVIEW_REQUIRED",
                    "severity": "MEDIUM",
                    "evidence_source": "VISION_PRESENCE_EVIDENCE",
                    "reason": f"Moderate visual stroke anomaly (score={anom_score:.2f}) on Correction Deed; verify registrar initials."
                })
            else:
                findings.append({
                    "rule_code": "RULE_VISUAL_TAMPERING_DETECTED",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "HIGH",
                    "evidence_source": "VISION_PRESENCE_EVIDENCE",
                    "reason": "Visual seam anomaly indicates suspected mechanical text alteration or splice."
                })

    confirmed_inconsistencies = [f for f in findings if f.get("category") == "CONFIRMED_INCONSISTENCY"]
    review_items = [f for f in findings if f.get("category") == "REVIEW_REQUIRED"]
    risk_indicators = [f for f in findings if f.get("category") == "RISK_INDICATOR"]

    # Flag as high-priority inconsistency if any CONFIRMED_INCONSISTENCY or >= 2 compounding RISK_INDICATORs
    is_risk = (len(confirmed_inconsistencies) > 0) or (len(risk_indicators) >= 2)

    if len(confirmed_inconsistencies) > 0:
        risk_score = min(1.0, 0.55 + 0.20 * len(confirmed_inconsistencies) + 0.08 * len(risk_indicators))
    elif len(risk_indicators) >= 2:
        risk_score = min(0.85, 0.52 + 0.12 * len(risk_indicators))
    elif len(review_items) > 0 or len(risk_indicators) == 1:
        risk_score = 0.30
    elif len(findings) > 0:
        risk_score = 0.20
    else:
        risk_score = 0.05

    return is_risk, round(float(risk_score), 4), findings
