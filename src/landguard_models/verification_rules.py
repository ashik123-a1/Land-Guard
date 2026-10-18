"""Deterministic verification engine providing statutory checks, explainable findings,
and strict four-category evidence distinction:
- CONFIRMED_INCONSISTENCY: a specific, verifiable contradiction in available evidence
- MISSING_EVIDENCE: required information is absent
- REVIEW_REQUIRED: evidence is ambiguous or conflicting (e.g., pending mutation, clerical correction mark)
- RISK_INDICATOR: heuristic suggests elevated risk (e.g., multi-year tax arrears, fire-sale price)
"""

from typing import Dict, Any, List, Tuple, Optional


RULE_METADATA: Dict[str, Dict[str, str]] = {
    "RULE_AREA_NOT_ASSESSED": {
        "title": "Holding Capacity Not Assessed",
        "title_bn": "জমির পরিমাণ অনুপস্থিত — ধারণক্ষমতা অপরীক্ষিত",
        "statutory_reference": "Land Reform Ordinance 1984 s.4 / SAT Act 1950",
        "default_explanation": "Transferred area was not specified or could not be detected; cadastral holding capacity check was not assessed.",
        "default_explanation_bn": "হস্তান্তরিত জমির পরিমাণ উল্লেখ না থাকায় ধারণক্ষমতা পরীক্ষা করা সম্ভব হয়নি।",
    },
    "RULE_AREA_EXCEEDS_CAPACITY": {
        "title": "Holding Capacity Exceeded",
        "title_bn": "খতিয়ানভুক্ত জোতের সর্বোচ্চ সীমা অতিক্রম",
        "statutory_reference": "Land Reform Ordinance 1984 s.4 / SAT Act 1950",
        "default_explanation": "Total transferred area exceeds the recorded cadastral parcel holding capacity.",
        "default_explanation_bn": "হস্তান্তরিত জমির পরিমাণ রেকর্ডভুক্ত ক্যাডাস্ট্রাল দাগের সর্বোচ্চ ধারণক্ষমতা অতিক্রম করেছে।",
    },
    "RULE_BROKEN_CHAIN_OF_TITLE": {
        "title": "Broken Chain of Title",
        "title_bn": "মালিকানা হস্তান্তরের ধারাক্রম বিচ্ছিন্ন",
        "statutory_reference": "Transfer of Property Act 1882 s.54; Registration Act 1908 s.17",
        "default_explanation": "Referenced prior conveyance or title succession cannot be traced in registry indices.",
        "default_explanation_bn": "রেজিস্ট্রি ইনডেক্সে পূর্ববর্তী দলিলের ধারাবাহিকতা বা মালিকানার প্রমাণ মেলেনি।",
    },
    "RULE_SELLER_NOT_TITLEHOLDER": {
        "title": "Seller Not Recorded Titleholder",
        "title_bn": "বিক্রেতা রেকর্ডভুক্ত বৈধ মালিক নন",
        "statutory_reference": "Registration Act 1908 s.21 / SAT Act 1950 s.143",
        "default_explanation": "Vendor cited in deed schedule does not match the active titleholder or mutated owner on record.",
        "default_explanation_bn": "দলিলে উল্লিখিত বিক্রেতা রেকর্ডভুক্ত খতিয়ান বা নামজারি অনুযায়ী বৈধ মালিক হিসেবে নিবন্ধিত নন।",
    },
    "RULE_CONFLICTING_DOUBLE_DISPOSITION": {
        "title": "Conflicting Double Sale Disposition",
        "title_bn": "স্বার্থপরিপন্থী দ্বৈত বিক্রয় বা পূর্ববর্তী হস্তান্তর",
        "statutory_reference": "Registration Act 1908 s.47 / Transfer of Property Act 1882 s.53A",
        "default_explanation": "Vendor previously conveyed the holding under registered deed; subsequent transfer creates double disposition.",
        "default_explanation_bn": "বিক্রেতা ইতিপূর্বে উক্ত জমি নিবন্ধিত দলিলের মাধ্যমে হস্তান্তর করেছেন; পুনঃহস্তান্তর দ্বৈত বিক্রির সৃষ্টি করে।",
    },
    "RULE_PARTIAL_SUBDIVISION_CAPACITY_CHECK": {
        "title": "Partial Subdivision Holding Check",
        "title_bn": "আংশিক জোত খণ্ডায়ন ও ধারণক্ষমতা যাচাই",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.117",
        "default_explanation": "Prior partial disposition detected within parcel capacity; boundary subdivision sketch review required.",
        "default_explanation_bn": "দাগের ধারণক্ষমতার মধ্যে পূর্ববর্তী আংশিক হস্তান্তর বিদ্যমান; সীমানা পৃথকীকরণ নকশা যাচাই আবশ্যক।",
    },
    "RULE_UNVERIFIED_MUTATION_RECORD": {
        "title": "Unverified Mutation Record",
        "title_bn": "অযাচাইকৃত নামজারি রেকর্ড",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.143",
        "default_explanation": "Mutation case reference is unverified, rejected, or missing in Land Revenue records.",
        "default_explanation_bn": "ভূমি রাজস্ব রেকর্ডে উল্লিখিত নামজারি কেসটি অযাচাইকৃত, প্রত্যাখ্যাত বা অনুপস্থিত।",
    },
    "RULE_MUTATION_PENDING_REVIEW": {
        "title": "Mutation Pending Approval",
        "title_bn": "নামজারি কেস অনুমোদনাধীন",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.143",
        "default_explanation": "Mutation proceeding is currently pending administrative approval by Assistant Commissioner (Land).",
        "default_explanation_bn": "সহকারী কমিশনার (ভূমি) কার্যালয়ে নামজারি আবেদনটি বর্তমানে অনুমোদন প্রক্রিয়ায় অনিষ্পন্ন।",
    },
    "RULE_TAX_ARREARS_INDICATOR": {
        "title": "Land Development Tax Arrears",
        "title_bn": "ভূমি উন্নয়ন কর বকেয়া",
        "statutory_reference": "Land Development Tax Ordinance 1976",
        "default_explanation": "Land development tax clearance lags deed execution by two or more years.",
        "default_explanation_bn": "ভূমি উন্নয়ন কর (খাজনা) পরিশোধের দাখিলা দলিল সম্পাদনকালের তুলনায় ২ বা ততোধিক বছর বকেয়া।",
    },
    "RULE_BELOW_MARKET_CONSIDERATION_INDICATOR": {
        "title": "Below-Market Consideration Valuation",
        "title_bn": "মৌজা মূল্যের তুলনায় অস্বাভাবিক কম মূল্য",
        "statutory_reference": "Stamp Act 1899 s.27",
        "default_explanation": "Declared deed consideration is substantially below the government minimum mouza valuation rate.",
        "default_explanation_bn": "দলিলে উল্লিখিত বিক্রয়মূল্য সরকারি সর্বনিম্ন মৌজা রেট চার্টের চেয়ে উল্লেখযোগ্যভাবে কম।",
    },
    "RULE_PLOT_MISMATCH_WITH_KHATIAN": {
        "title": "Plot Number Mismatch With Survey Record",
        "title_bn": "জরিপ রেকর্ডের সাথে দাগ নম্বরের অসঙ্গতি",
        "statutory_reference": "Registration Act 1908 s.21",
        "default_explanation": "Plot cited in physical deed schedule conflicts with registered cadastral survey ledger.",
        "default_explanation_bn": "দলিলে উল্লিখিত দাগ নম্বরটি সরকারি জরিপ খতিয়ানের দাগের সাথে গরমিল প্রদর্শন করছে।",
    },
    "RULE_MANDATORY_REGISTRAR_SEAL_ABSENT": {
        "title": "Official Registrar Seal Absent",
        "title_bn": "সাব-রেজিস্ট্রি অফিসের অফিসিয়াল সিল অনুপস্থিত",
        "statutory_reference": "Registration Act 1908 s.52 / s.60",
        "default_explanation": "Mandatory official Sub-Registry authentication seal is missing or not detected on deed.",
        "default_explanation_bn": "দলিলে সাব-রেজিস্ট্রারের বাধ্যতামূলক আনুষ্ঠানিক প্রমাণীকরণ সিল অনুপস্থিত।",
    },
    "RULE_VISUAL_TAMPERING_DETECTED": {
        "title": "Physical Deed Alteration or Tampering",
        "title_bn": "দলিলে ঘষামাজা বা শারীরিক কারচুপির আলামত",
        "statutory_reference": "Penal Code 1860 s.463 / s.471",
        "default_explanation": "Visual inspection detected seam anomalies, paste-over alterations, or stroke irregularities.",
        "default_explanation_bn": "কম্পিউটার ভিশন স্ক্যানে জোড়াতালি, ঘষামাজা বা টেক্সট পরিবর্তনের আলামত পরিলক্ষিত হয়েছে।",
    },
    "RULE_PLOT_NOT_FOUND_IN_REGISTRY": {
        "title": "Plot Not Found in Registry Index",
        "title_bn": "রেজিস্ট্রি ইনডেক্সে দাগ নম্বর পাওয়া যায়নি",
        "statutory_reference": "Cadastral Survey Records Index",
        "default_explanation": "Dag plot number was not found in the verified cadastral survey records.",
        "default_explanation_bn": "যাচাইকৃত সরকারি ক্যাডাস্ট্রাল জরিপ ইনডেক্সে উক্ত দাগ নম্বরটি পাওয়া যায়নি।",
    },
    "RULE_ACTIVE_DISPUTE_FLAGGED": {
        "title": "Active Legal Dispute Recorded on Parcel",
        "title_bn": "উক্ত দাগে সক্রিয় বিরোধ বা অভিযোগ নথিভুক্ত",
        "statutory_reference": "Registration Act 1908 / LandTech Audit P3",
        "default_explanation": "Active land dispute or fraud grievance is currently under investigation for this parcel.",
        "default_explanation_bn": "উক্ত দাগের বিষয়ে কর্তৃপক্ষের নিকট আনুষ্ঠানিক বিরোধ বা প্রতারণার অভিযোগ তদন্তাধীন রয়েছে।",
    },
    "ML_ELEVATED_RISK_SCORE": {
        "title": "Elevated Statistical Risk Score",
        "title_bn": "পরিসংখ্যানগত উচ্চ ঝুঁকি স্কোর",
        "statutory_reference": "LandGuard Supervised XGBoost Model",
        "default_explanation": "Multi-feature risk model indicates elevated anomaly risk requiring human administrative review.",
        "default_explanation_bn": "মাল্টি-ফিচার পরিসংখ্যান মডেল উচ্চ ঝুঁকি নির্দেশ করছে যা প্রশাসনিক পর্যালোচনাযোগ্য।",
    },
}


def normalize_rule_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensures every finding has complete, human-readable title, explanation, reason, and statutory reference."""
    for f in findings:
        code = f.get("rule_code", "RULE_CHECK")
        meta = RULE_METADATA.get(code, {})
        if not f.get("title"):
            f["title"] = meta.get("title") or code.replace("RULE_", "").replace("_", " ").title()
        if not f.get("explanation"):
            f["explanation"] = f.get("reason") or meta.get("default_explanation") or "Statutory condition flagged for review."
        if not f.get("reason"):
            f["reason"] = f["explanation"]
        if not f.get("statutory_reference"):
            f["statutory_reference"] = meta.get("statutory_reference") or "Registration Act 1908 / SAT Act 1950"
        if not f.get("title_bn"):
            f["title_bn"] = meta.get("title_bn") or f["title"]
        if not f.get("explanation_bn"):
            f["explanation_bn"] = meta.get("default_explanation_bn") or f["explanation"]
    return findings


def evaluate_verification_rules(
    txn: Dict[str, Any],
    parcel: Dict[str, Any],
    history_txns: Optional[List[Dict[str, Any]]] = None,
    mutations: Optional[List[Dict[str, Any]]] = None,
    khatian_records: Optional[List[Dict[str, Any]]] = None,
    document_evidence: Optional[Dict[str, Any]] = None,
    include_document_evidence: bool = True,
    cadastral_found: bool = True,
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
    has_area_specified = txn.get("has_transferred_area_specified", True)
    if not cadastral_found:
        plot_no = txn.get("dag_plot_number") or parcel.get("dag_plot_number", "UNKNOWN")
        findings.append({
            "rule_code": "RULE_PLOT_NOT_FOUND_IN_REGISTRY",
            "category": "MISSING_EVIDENCE",
            "severity": "HIGH",
            "evidence_source": "CADASTRAL_SURVEY",
            "reason": f"Dag plot number '{plot_no}' was not found in the verified cadastral registry index.",
        })
    elif not has_area_specified or t_area <= 0.0:
        findings.append({
            "rule_code": "RULE_AREA_NOT_ASSESSED",
            "category": "MISSING_EVIDENCE",
            "severity": "LOW",
            "evidence_source": "DEED_RECORD",
            "reason": "Transferred area was not specified or could not be detected; cadastral holding capacity check was not assessed.",
        })
    elif t_area > p_area * 1.01:
        findings.append({
            "rule_code": "RULE_AREA_EXCEEDS_CAPACITY",
            "category": "CONFIRMED_INCONSISTENCY",
            "severity": "CRITICAL",
            "evidence_source": "REGISTRY_RECORD",
            "reason": f"Transferred area ({t_area:.2f} dec) exceeds recorded cadastral parcel capacity ({p_area:.2f} dec)."
        })

    # Branch rule evaluation by statutory document type
    doc_type = str(txn.get("document_type") or "SALE_DEED").upper()

    if doc_type == "MUTATION_RECORD":
        mut_case = str(txn.get("mutation_case_no", "") or "").strip()
        if not mut_case:
            findings.append({
                "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "MUTATION_REGISTER",
                "reason": "Mutation case number was not provided or could not be detected in order text.",
            })
        elif not cadastral_found:
            findings.append({
                "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "MUTATION_REGISTER",
                "reason": f"Cadastral parcel is unindexed; mutation case '{mut_case}' cannot be cross-referenced in revenue records.",
            })
        elif mutations:
            matching_mut = next((m for m in mutations if m.get("mutation_case_no", "").strip().lower() == mut_case.lower()), None)
            if matching_mut:
                status = str(matching_mut.get("status", "APPROVED")).upper()
                if status == "PENDING":
                    findings.append({
                        "rule_code": "RULE_MUTATION_PENDING_REVIEW",
                        "category": "REVIEW_REQUIRED",
                        "severity": "MEDIUM",
                        "evidence_source": "MUTATION_REGISTER",
                        "reason": f"Mutation case '{mut_case}' is currently pending administrative approval by Assistant Commissioner (Land).",
                    })
                elif status in ("REJECTED", "DISMISSED"):
                    findings.append({
                        "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                        "category": "CONFIRMED_INCONSISTENCY",
                        "severity": "HIGH",
                        "evidence_source": "MUTATION_REGISTER",
                        "reason": f"Mutation case '{mut_case}' was formally rejected by land revenue authorities.",
                    })
            else:
                findings.append({
                    "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "HIGH",
                    "evidence_source": "MUTATION_REGISTER",
                    "reason": f"Mutation case '{mut_case}' was not found in the verified land revenue mutation register for Plot #{parcel.get('dag_plot_number')}.",
                })
        else:
            findings.append({
                "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                "category": "CONFIRMED_INCONSISTENCY",
                "severity": "HIGH",
                "evidence_source": "MUTATION_REGISTER",
                "reason": f"No mutation records registered for Plot #{parcel.get('dag_plot_number')}; case '{mut_case}' is unverified.",
            })

        if include_document_evidence and document_evidence:
            if document_evidence.get("cv_visual_anomaly_detected"):
                findings.append({
                    "rule_code": "RULE_VISUAL_TAMPERING_DETECTED",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "CRITICAL",
                    "evidence_source": "VISION_ALTERATION_EVIDENCE",
                    "reason": f"Visual anomaly detector flagged physical alteration (score: {document_evidence.get('cv_visual_anomaly_score', 0):.2f}).",
                })

        findings = normalize_rule_findings(findings)
        is_risk = any(f["category"] in ("CONFIRMED_INCONSISTENCY", "REVIEW_REQUIRED") for f in findings)
        confidence = 0.95 if is_risk else 0.05
        return is_risk, confidence, findings

    elif doc_type == "KHATIAN_PORCHA":
        khatian_no = str(txn.get("khatian_number") or "").strip()
        reg_khatian = str(parcel.get("khatian_number") or "").strip()
        if khatian_no and reg_khatian and khatian_no.lower() != reg_khatian.lower():
            findings.append({
                "rule_code": "RULE_PLOT_MISMATCH_WITH_KHATIAN",
                "category": "CONFIRMED_INCONSISTENCY",
                "severity": "HIGH",
                "evidence_source": "CADASTRAL_SURVEY",
                "reason": f"Cited Khatian #{khatian_no} conflicts with registered survey ledger Khatian #{reg_khatian} for this plot.",
            })
        if include_document_evidence and document_evidence:
            if document_evidence.get("cv_visual_anomaly_detected"):
                findings.append({
                    "rule_code": "RULE_VISUAL_TAMPERING_DETECTED",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "CRITICAL",
                    "evidence_source": "VISION_ALTERATION_EVIDENCE",
                    "reason": "Visual inspection detected alteration or patch seam on Khatian sheet.",
                })
        findings = normalize_rule_findings(findings)
        is_risk = any(f["category"] in ("CONFIRMED_INCONSISTENCY", "REVIEW_REQUIRED") for f in findings)
        confidence = 0.95 if is_risk else 0.05
        return is_risk, confidence, findings

    elif doc_type == "TAX_RECEIPT":
        if include_document_evidence and document_evidence:
            if document_evidence.get("cv_visual_anomaly_detected"):
                findings.append({
                    "rule_code": "RULE_VISUAL_TAMPERING_DETECTED",
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "CRITICAL",
                    "evidence_source": "VISION_ALTERATION_EVIDENCE",
                    "reason": "Visual anomaly detector flagged physical alteration on tax receipt.",
                })
        findings = normalize_rule_findings(findings)
        is_risk = any(f["category"] in ("CONFIRMED_INCONSISTENCY", "REVIEW_REQUIRED") for f in findings)
        confidence = 0.95 if is_risk else 0.05
        return is_risk, confidence, findings

    # Default / SALE_DEED: Full deed statutory chain-of-title rules
    # 2. Chain of Title Continuity & Prior Deed Reference
    seller_id = txn["seller_ids"][0] if txn.get("seller_ids") else ""
    prev_ref = str(txn.get("previous_deed_ref", "") or "")
    is_ancestral = prev_ref == "INHERITED_ANCESTRAL_CS_RECORD"

    if prev_ref and not is_ancestral:
        if not cadastral_found:
            findings.append({
                "rule_code": "RULE_BROKEN_CHAIN_OF_TITLE",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "RELATIONAL_HISTORY",
                "reason": f"Historical deed registry records unavailable to trace prior conveyance '{prev_ref}' for unindexed parcel."
            })
        elif "UNINDEXED" in prev_ref or "DAMAGED_VOLUME" in prev_ref:
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
    if not seller_id:
        findings.append({
            "rule_code": "RULE_SELLER_NOT_TITLEHOLDER",
            "category": "MISSING_EVIDENCE",
            "severity": "MEDIUM",
            "evidence_source": "DEED_RECORD",
            "reason": "Vendor identifier was not provided; preceding titleholder chain cannot be verified.",
        })
    elif not cadastral_found:
        findings.append({
            "rule_code": "RULE_SELLER_NOT_TITLEHOLDER",
            "category": "MISSING_EVIDENCE",
            "severity": "MEDIUM",
            "evidence_source": "RELATIONAL_HISTORY",
            "reason": "Cadastral parcel is not indexed in registry; seller ownership tenure cannot be verified against chain of title.",
        })
    elif not is_ancestral and history_txns:
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
        if not cadastral_found:
            findings.append({
                "rule_code": "RULE_UNVERIFIED_MUTATION_RECORD",
                "category": "MISSING_EVIDENCE",
                "severity": "MEDIUM",
                "evidence_source": "MUTATION_REGISTER",
                "reason": f"Land Revenue mutation register unavailable to verify record '{mut_no}' for unindexed parcel."
            })
        elif mutations is not None:
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
        # No mutation case cited on deed (optional for sale deed)
        # Check if verified land revenue mutation register has an approved mutation for the vendor
        seller_id = txn["seller_ids"][0] if txn.get("seller_ids") else ""
        has_approved_seller_mutation = (
            bool(mutations) and bool(seller_id) and any(
                (m.get("new_owner_id") == seller_id or m.get("applicant_id") == seller_id or m.get("applicant_name") == seller_id)
                and m.get("status", "APPROVED") == "APPROVED"
                for m in mutations
            )
        )
        if not has_approved_seller_mutation:
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
        if cadastral_found and claimed_dag is not None and registered_dag is not None and str(claimed_dag) != str(registered_dag):
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

    findings = normalize_rule_findings(findings)
    return is_risk, round(float(risk_score), 4), findings
