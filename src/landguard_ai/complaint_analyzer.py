"""AI Complaint Analysis Engine
Extracts claims, suggests categories, detects potential duplicate complaints,
and evaluates claim-to-registry evidence matching into:
- SUPPORTED_BY_AVAILABLE_RECORDS
- CONTRADICTED_BY_AVAILABLE_RECORDS
- UNVERIFIED

Note: All generated outputs are preliminary investigative aids and must not
automatically create official legal findings without authorized human review.
"""

import re
from typing import Dict, Any, List, Optional
from src.landguard_ai.voice_assistant import to_en_digits, extract_entities


PRELIMINARY_DISCLAIMER = (
    "PRELIMINARY AI SUGGESTION — This analysis is automatically generated as an "
    "investigative aid and does not constitute an official legal or administrative finding. "
    "Final determination must be recorded by an authorized registrar or investigating officer."
)


def extract_complaint_claims(narrative: str, title: str = "") -> List[Dict[str, Any]]:
    """Extracts structured discrete legal allegations and claims from complaint text."""
    combined = f"{title}. {narrative}"
    normalized = to_en_digits(combined)
    claims = []

    # Claim: Double Sale / Multiple Conveyances
    if re.search(r"(double\s*sell|দ্বৈত\s*বিক্রি|conveyed\s*twice|sold\s*twice|multiple\s*buyers|একই\s*জমি\s*দুই\s*বার)", normalized, re.IGNORECASE):
        claims.append({
            "claim_type": "DOUBLE_SELLING_ALLEGATION",
            "description": "Allegation that parcel or plot share was conveyed multiple times to distinct purchasers.",
            "statutory_context": "Transfer of Property Act 1882 s.54; Registration Act 1908 s.47",
        })

    # Claim: Non-Titleholder / Imposter Seller
    if re.search(r"(not\s*the\s*owner|মালিক\s*নয়|imposter|জাল\s*মালিক|fake\s*seller|without\s*title|ওয়ারিশ\s*নয়|no\s*title)", normalized, re.IGNORECASE):
        claims.append({
            "claim_type": "NON_TITLEHOLDER_TRANSFER_ALLEGATION",
            "description": "Allegation that vendor lacked legitimate recorded ownership or inherited title.",
            "statutory_context": "State Acquisition and Tenancy Act 1950 s.143; Evidence Act 1872",
        })

    # Claim: Area / Boundary Exceedance
    if re.search(r"(excess\s*area|বেশি\s*জমি|area\s*exceed|capacity|সীমানা\s*লঙ্ঘন|over\s*conveyance|exaggerated)", normalized, re.IGNORECASE):
        claims.append({
            "claim_type": "AREA_EXCEEDANCE_ALLEGATION",
            "description": "Allegation that transferred area exceeds vendor entitlement or holding capacity.",
            "statutory_context": "Land Reform Ordinance 1984; SAT Act 1950",
        })

    # Claim: Document Tampering / Forgery
    if re.search(r"(forged|জাল\s*দলিল|tampered|fake\s*seal|fake\s*stamp|কাটাছেঁড়া|paste-over|whiteout|সিগনেচার\s*নকল)", normalized, re.IGNORECASE):
        claims.append({
            "claim_type": "DOCUMENT_FORGERY_ALLEGATION",
            "description": "Allegation of physical or typographical alteration on deed schedule or official seal.",
            "statutory_context": "Penal Code 1860 ss.463-471; Registration Act 1908",
        })

    # Claim: Mutation Record Mismatch
    if re.search(r"(mutation|নামজারি|খারিজ|khatian\s*mismatch|unregistered\s*mutation|ভুয়া\s*খতিয়ান)", normalized, re.IGNORECASE):
        claims.append({
            "claim_type": "MUTATION_RECORD_ALLEGATION",
            "description": "Allegation of fabricated, pending, or inconsistent Namzari mutation record.",
            "statutory_context": "State Acquisition and Tenancy Act 1950 s.143",
        })

    if not claims:
        claims.append({
            "claim_type": "GENERAL_LAND_DISPUTE_ALLEGATION",
            "description": "General claim of property grievance or administrative irregularity.",
            "statutory_context": "Civil Procedure & Land Registry Regulations",
        })

    return claims


def suggest_category(narrative: str, current_category: Optional[str] = None) -> str:
    """Classifies complaint into official category taxonomy."""
    text = narrative.lower()
    if any(k in text for k in ["double sale", "দ্বৈত বিক্রি", "conveyed twice", "second buyer", "two buyers"]):
        return "SUSPECTED_DOUBLE_SALE"
    if any(k in text for k in ["not the owner", "মালিক নয়", "fake seller", "imposter", "inheritance conflict"]):
        return "OWNERSHIP_CONFLICT"
    if any(k in text for k in ["forged", "জাল দলিল", "tampered", "fake seal", "fake signature", "cut and paste"]):
        return "DOCUMENT_INTEGRITY_CONCERN"
    if any(k in text for k in ["mutation", "নামজারি", "খারিজ", "mismatch", "wrong plot", "রেকর্ড গরমিল"]):
        return "RECORD_MISMATCH"
    return current_category or "OTHER"


def _tokenize_text(text: str) -> set:
    """Normalizes and tokenizes English and Bengali text into distinctive word tokens."""
    if not text:
        return set()
    norm = to_en_digits(str(text)).lower()
    tokens = re.findall(r"[\w\u0980-\u09FF]+", norm)
    stopwords = {
        "the", "a", "an", "is", "and", "or", "to", "in", "of", "for", "on", "with", "this", "that", "at", "by", "from",
        "plot", "deed", "dag", "land", "parcel", "citizen", "complaint", "dispute",
        "এবং", "ও", "বা", "এই", "সেই", "এর", "তে", "হতে", "থেকে", "করে", "করা", "হল", "হয়েছে", "আছে", "না", "জমির", "দাগ"
    }
    return {t for t in tokens if len(t) > 2 and t not in stopwords}


def _calculate_jaccard(tokens1: set, tokens2: set) -> float:
    """Calculates Jaccard lexical overlap similarity."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


def detect_duplicate_complaints(
    current_complaint_id: str,
    dag_plot: str,
    deed_number: str,
    all_complaints: List[Dict[str, Any]],
    current_narrative: str = "",
    current_category: str = "",
    current_user_id: Optional[str] = None,
    viewer_user_id: Optional[str] = None,
    is_staff: bool = False,
) -> List[Dict[str, Any]]:
    """Identifies and classifies overlapping complaints referencing the same plot or deed.
    
    Multi-Signal Matching Classification:
    - LIKELY_DUPLICATE: Identical deed match, or same complainant on same plot with category/text overlap,
      or same plot + same category + high text overlap (>= 50%).
    - POSSIBLY_RELATED: Same plot + same category (different complainant), or moderate text overlap (>= 25%).
    - SAME_PARCEL_DIFFERENT_CLAIM: Same plot alone without deed match or category overlap.
    
    *Privacy Guarantee*: When viewed by non-staff (citizens), private citizen personal data (name, phone,
    NID, detailed narrative) is strictly masked as 'Independent Citizen Filing' or 'Your Previous Filing'.
    """
    matches = []
    norm_plot = to_en_digits(str(dag_plot or "")).strip()
    norm_deed = str(deed_number or "").strip()
    has_valid_plot = bool(norm_plot and norm_plot not in ["N/A", "NONE", "0", ""])
    has_valid_deed = bool(norm_deed and norm_deed.upper() not in ["N/A", "NONE", "0", ""])

    curr_tokens = _tokenize_text(current_narrative)
    curr_cat = (current_category or "").strip().upper()

    for comp in all_complaints:
        cid = comp.get("complaint_id")
        if not cid or cid == current_complaint_id:
            continue

        c_plot = to_en_digits(str(comp.get("dag_plot_number", ""))).strip()
        c_deed = str(comp.get("deed_number", "")).strip()
        c_user = comp.get("citizen_user_id") or comp.get("user_id")
        c_cat = (comp.get("category") or "OTHER").strip().upper()
        c_narrative = str(comp.get("narrative_description") or comp.get("description") or comp.get("title") or "")
        c_tokens = _tokenize_text(c_narrative)

        plot_match = has_valid_plot and (norm_plot == c_plot)
        deed_match = has_valid_deed and (c_deed and c_deed.upper() not in ["N/A", "NONE", ""]) and (norm_deed.lower() == c_deed.lower())

        if not (plot_match or deed_match):
            continue

        same_complainant = bool(current_user_id and c_user and current_user_id == c_user)
        same_category = bool(curr_cat and c_cat and curr_cat == c_cat and curr_cat != "OTHER")
        lex_sim = _calculate_jaccard(curr_tokens, c_tokens)

        # Multi-signal classification
        if deed_match:
            classification = "LIKELY_DUPLICATE"
            relationship_label = "Likely Duplicate"
            match_reason = f"Identical Deed Reference #{norm_deed} on Plot #{norm_plot or c_plot}"
            score = 0.95
        elif same_complainant and plot_match and (same_category or lex_sim >= 0.30):
            classification = "LIKELY_DUPLICATE"
            relationship_label = "Likely Duplicate"
            match_reason = f"Prior filing by same complainant on Plot #{norm_plot}"
            score = 0.90
        elif plot_match and same_category and lex_sim >= 0.50:
            classification = "LIKELY_DUPLICATE"
            relationship_label = "Likely Duplicate"
            match_reason = f"High narrative overlap ({int(lex_sim*100)}%) and same category on Plot #{norm_plot}"
            score = 0.85
        elif plot_match and (same_category or lex_sim >= 0.25):
            classification = "POSSIBLY_RELATED"
            relationship_label = "Related Parcel Filing"
            detail = f"Same category ({c_cat})" if same_category else f"Related claim context ({int(lex_sim*100)}% text match)"
            match_reason = f"{detail} on Plot #{norm_plot}"
            score = 0.55 + round(lex_sim * 0.2, 2)
        elif plot_match:
            classification = "SAME_PARCEL_DIFFERENT_CLAIM"
            relationship_label = "Same Parcel, Different Claim"
            match_reason = f"Other filing on Plot #{norm_plot} (Category: {c_cat})"
            score = 0.25
        else:
            continue

        # Citizen Privacy Protection
        is_own_filing = bool(
            (viewer_user_id and c_user and viewer_user_id == c_user) or
            (current_user_id and c_user and current_user_id == c_user)
        )
        if is_staff:
            complainant_display = comp.get("citizen_name") or f"Citizen ({c_user or 'User'})"
            safe_narrative = (c_narrative[:120] + "...") if len(c_narrative) > 120 else c_narrative
            display_deed = c_deed or "N/A"
        else:
            complainant_display = "Your Previous Filing" if is_own_filing else "Independent Citizen Filing"
            safe_narrative = None
            display_deed = c_deed if deed_match else "CONFIDENTIAL"

        matches.append({
            "complaint_id": cid,
            "classification": classification,
            "relationship_label": relationship_label,
            "match_reason": match_reason,
            "match_score": round(score, 2),
            "lexical_similarity": round(lex_sim, 2),
            "category": c_cat,
            "status": comp.get("status", "SUBMITTED"),
            "created_at": comp.get("created_at"),
            "dag_plot_number": c_plot,
            "deed_number": display_deed,
            "citizen_name": complainant_display,
            "complainant_display": complainant_display,
            "narrative_preview": safe_narrative,
            "is_own_filing": is_own_filing,
        })

    # Sort: LIKELY_DUPLICATE -> POSSIBLY_RELATED -> SAME_PARCEL_DIFFERENT_CLAIM, then by score desc
    rank_map = {"LIKELY_DUPLICATE": 1, "POSSIBLY_RELATED": 2, "SAME_PARCEL_DIFFERENT_CLAIM": 3}
    matches.sort(
        key=lambda m: (rank_map.get(m["classification"], 9), -m["match_score"], m.get("created_at") or ""),
    )
    return matches


def build_duplicate_summary(matches: List[Dict[str, Any]], top_k: int = 5) -> Dict[str, Any]:
    """Generates structured summary KPIs and capped top matches for compact rendering."""
    likely_count = sum(1 for m in matches if m.get("classification") == "LIKELY_DUPLICATE")
    related_count = sum(1 for m in matches if m.get("classification") == "POSSIBLY_RELATED")
    diff_claim_count = sum(1 for m in matches if m.get("classification") == "SAME_PARCEL_DIFFERENT_CLAIM")
    total_count = len(matches)

    top_matches = matches[:top_k]
    remaining_matches = matches[top_k:]

    return {
        "total_related_count": total_count,
        "likely_duplicate_count": likely_count,
        "possibly_related_count": related_count,
        "same_parcel_different_claim_count": diff_claim_count,
        "has_likely_duplicates": likely_count > 0,
        "has_related_filings": total_count > 0,
        "top_matches": top_matches,
        "remaining_count": max(0, total_count - len(top_matches)),
        "all_matches": matches,
    }


def evaluate_evidence_matching(
    claims: List[Dict[str, Any]],
    parcel_record: Optional[Dict[str, Any]],
    verification_findings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Matches claims against cadastral registry records and statutory findings.

    Returns:
    - match_state: 'SUPPORTED_BY_AVAILABLE_RECORDS', 'CONTRADICTED_BY_AVAILABLE_RECORDS', or 'UNVERIFIED'
    - evidence_links: List of corroborating or contradictory record references
    - rationale: Narrative explanation of matching logic
    """
    if not parcel_record:
        return {
            "match_state": "UNVERIFIED",
            "evidence_links": [],
            "rationale": "No cadastral registry ledger found for the cited plot number in operational database. Field verification required.",
        }

    findings = verification_findings or []
    contradiction_rules = {"RULE-DOUBLE-SALE", "RULE-SELLER-OWNER", "RULE-AREA-CAPACITY", "RULE-MUTATION-RECORD", "RULE-CHAIN-OF-TITLE"}
    triggered_rules = {f.get("rule_id"): f for f in findings if f.get("status") in ["FAIL", "FAILED", "VIOLATION"]}

    evidence_links = []
    has_registry_corroboration = False
    has_contradiction = False

    # Check statutory findings
    for rule_id, finding in triggered_rules.items():
        if rule_id in contradiction_rules:
            has_registry_corroboration = True
            evidence_links.append({
                "source": "STATUTORY_VERIFICATION_ENGINE",
                "reference": rule_id,
                "detail": finding.get("message") or finding.get("statutory_finding"),
                "significance": "CORROBORATES_CITIZEN_GRIEVANCE",
            })

    # Check parcel capacity
    total_area = float(parcel_record.get("total_area_decimal", 0.0))
    recorded_txns = parcel_record.get("deed_history") or []
    if recorded_txns:
        evidence_links.append({
            "source": "CADASTRAL_REGISTRY_LEDGER",
            "reference": f"Dag #{parcel_record.get('dag_plot_number')}",
            "detail": f"Parcel has {len(recorded_txns)} recorded conveyance(s), total area: {total_area} decimals.",
            "significance": "RECORD_BASELINE",
        })

    # Check if specific claims are concretely contradicted
    claim_types = {c.get("claim_type") for c in claims}
    concrete_contradictions = []

    # 1. Area exceedance claimed, but parcel capacity mathematically contradicts it
    if "AREA_EXCEEDANCE_ALLEGATION" in claim_types and total_area > 0:
        cum_area = sum(float(t.get("transferred_area_decimal", 0)) for t in recorded_txns)
        if cum_area <= total_area and not any(f.get("rule_id") == "RULE-AREA-CAPACITY" for f in findings):
            concrete_contradictions.append({
                "source": "CADASTRAL_CAPACITY_LEDGER",
                "reference": f"Dag #{parcel_record.get('dag_plot_number')}",
                "detail": f"Registered ledger confirms cumulative transfers ({cum_area} dec) are strictly within total holding capacity ({total_area} dec).",
                "significance": "CONTRADICTS_AREA_EXCEEDANCE_CLAIM",
            })

    # 2. Non-titleholder claimed, but registered owner has verified mutation
    current_owners = parcel_record.get("current_owners") or []
    if "NON_TITLEHOLDER_TRANSFER_ALLEGATION" in claim_types and current_owners:
        # Check if verified mutation exists
        has_approved_mutation = any(
            t.get("mutation_case_no") and not any(f.get("rule_id") == "RULE-MUTATION-RECORD" for f in findings)
            for t in recorded_txns
        )
        if has_approved_mutation and not any(f.get("rule_id") == "RULE-SELLER-OWNER" for f in findings):
            concrete_contradictions.append({
                "source": "CADASTRAL_KHATIAN_SETTLEMENT",
                "reference": f"Khatian #{parcel_record.get('khatian_number', 'N/A')}",
                "detail": f"Active title is formally registered to {', '.join(o.get('name', 'N/A') for o in current_owners)} with verified Namzari mutation.",
                "significance": "CONTRADICTS_NON_TITLEHOLDER_CLAIM",
            })

    if has_registry_corroboration:
        state = "SUPPORTED_BY_AVAILABLE_RECORDS"
        rationale = (
            "Available cadastral ledgers and statutory verification rules corroborate the presence of "
            "title discrepancies or conflicting conveyances on this plot."
        )
    elif concrete_contradictions:
        state = "CONTRADICTED_BY_AVAILABLE_RECORDS"
        evidence_links.extend(concrete_contradictions)
        rationale = (
            "Specific factual allegations in the grievance are directly contradicted by documented cadastral records "
            "(e.g., recorded plot boundaries, verified khatian ownership, or registered conveyance history)."
        )
    elif current_owners and not triggered_rules:
        # Absence of detected conflict is NOT proof that citizen allegation is false
        state = "NO_CONFLICT_FOUND_IN_INDEXED_RECORDS"
        evidence_links.append({
            "source": "CADASTRAL_KHATIAN_SETTLEMENT",
            "reference": f"Khatian #{parcel_record.get('khatian_number', 'N/A')}",
            "detail": f"Active title is formally registered under: {', '.join(o.get('name', 'N/A') for o in current_owners)} with zero recorded adverse claims in indexed ledger.",
            "significance": "NO_ADVERSE_ENTRY_IN_DIGITAL_INDEX",
        })
        rationale = (
            f"No conflicting conveyances or adverse entries were found in the currently indexed digital cadastral ledger "
            f"for Dag #{parcel_record.get('dag_plot_number')}. However, absence of an indexed conflict does not prove an "
            f"allegation is false, as unindexed physical archives, pending sub-registry volumes, or off-record transactions "
            f"may limit ledger completeness. Official field and archive inspection is recommended."
        )
    else:
        state = "UNVERIFIED"
        rationale = (
            "Insufficient conclusive documentation in operational ledger to confirm or contradict the grievance. "
            "Physical Sub-Registry archival deed inspection is recommended."
        )

    return {
        "match_state": state,
        "evidence_links": evidence_links,
        "rationale": rationale,
    }


def analyze_complaint(
    complaint: Dict[str, Any],
    parcel_record: Optional[Dict[str, Any]] = None,
    all_complaints: Optional[List[Dict[str, Any]]] = None,
    verification_findings: Optional[List[Dict[str, Any]]] = None,
    viewer_user_id: Optional[str] = None,
    is_staff: bool = False,
) -> Dict[str, Any]:
    """Comprehensive AI analysis of a citizen complaint."""
    narrative = complaint.get("narrative_description", "") or complaint.get("description", "")
    title = complaint.get("title", "")
    dag_plot = to_en_digits(str(complaint.get("dag_plot_number", ""))).strip()
    deed_number = str(complaint.get("deed_number", "")).strip()

    claims = extract_complaint_claims(narrative, title)
    suggested_cat = suggest_category(narrative, complaint.get("category"))
    duplicates = detect_duplicate_complaints(
        current_complaint_id=complaint.get("complaint_id", ""),
        dag_plot=dag_plot,
        deed_number=deed_number,
        all_complaints=all_complaints or [],
        current_narrative=f"{title}. {narrative}",
        current_category=complaint.get("category", ""),
        current_user_id=complaint.get("citizen_user_id") or complaint.get("user_id"),
        viewer_user_id=viewer_user_id or complaint.get("citizen_user_id"),
        is_staff=is_staff,
    )
    dup_summary = build_duplicate_summary(duplicates, top_k=5)
    matching = evaluate_evidence_matching(claims, parcel_record, verification_findings)

    return {
        "complaint_id": complaint.get("complaint_id"),
        "preliminary_disclaimer": PRELIMINARY_DISCLAIMER,
        "extracted_claims": claims,
        "suggested_category": suggested_cat,
        "current_category": complaint.get("category"),
        "category_matches_suggestion": suggested_cat == complaint.get("category"),
        "duplicate_candidates": dup_summary["top_matches"],
        "all_duplicate_candidates": duplicates,
        "duplicate_summary": dup_summary,
        "has_potential_duplicates": dup_summary["has_likely_duplicates"],
        "has_related_filings": dup_summary["has_related_filings"],
        "claim_matching_state": matching["match_state"],
        "evidence_links": matching["evidence_links"],
        "matching_rationale": matching["rationale"],
        "recommended_investigative_action": (
            "Prioritize cross-checking cited deed against Sub-Registry volumed registers."
            if matching["match_state"] == "SUPPORTED_BY_AVAILABLE_RECORDS"
            else "Issue clarification request to citizen for certified deed copy or documentary evidence."
        ),
    }
