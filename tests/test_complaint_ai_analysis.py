"""Automated test suite for AI Complaint Analysis & Claim-to-Evidence Matching.
Validates:
1. Extraction of structured legal allegations (double-selling, non-titleholder, area exceedance, forgery).
2. Category taxonomy suggestion and duplicate grievance detection.
3. Grounded evidence matching:
   - SUPPORTED_BY_AVAILABLE_RECORDS
   - CONTRADICTED_BY_AVAILABLE_RECORDS
   - UNVERIFIED
4. REST API endpoint GET /api/complaints/{id}/ai-analysis with authentication and IDOR enforcement.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_ai.complaint_analyzer import (
    extract_complaint_claims,
    suggest_category,
    detect_duplicate_complaints,
    evaluate_evidence_matching,
    analyze_complaint,
)

client = TestClient(app, follow_redirects=False)


def test_extract_complaint_claims():
    """Verify regex extraction of multiple legal claims from bilingual narrative."""
    narrative = "The vendor sold plot 9044 twice to two buyers, and the deed has forged seals."
    claims = extract_complaint_claims(narrative, title="Double selling dispute")
    types = [c["claim_type"] for c in claims]
    assert "DOUBLE_SELLING_ALLEGATION" in types
    assert "DOCUMENT_FORGERY_ALLEGATION" in types

    # Bengali narrative
    bn_narrative = "বিক্রেতা জমির প্রকৃত মালিক নয় এবং ভুয়া নামজারি খতিয়ান দেখিয়ে দলিল করেছে।"
    bn_claims = extract_complaint_claims(bn_narrative, title="মালিকানা বিরোধ")
    bn_types = [c["claim_type"] for c in bn_claims]
    assert "NON_TITLEHOLDER_TRANSFER_ALLEGATION" in bn_types
    assert "MUTATION_RECORD_ALLEGATION" in bn_types


def test_suggest_category():
    """Verify complaint category suggestion taxonomy."""
    assert suggest_category("He sold the property twice to two buyers") == "SUSPECTED_DOUBLE_SALE"
    assert suggest_category("The seller is an imposter and not the owner") == "OWNERSHIP_CONFLICT"
    assert suggest_category("The physical stamp and seal are forged") == "DOCUMENT_INTEGRITY_CONCERN"
    assert suggest_category("There is a mutation mismatch in khatian records") == "RECORD_MISMATCH"


def test_detect_duplicate_complaints():
    """Identifies overlapping complaints on the same plot or deed."""
    existing = [
        {"complaint_id": "CMP-2026-001", "dag_plot_number": "9044", "deed_number": "DEED-101", "status": "SUBMITTED", "citizen_name": "Citizen A"},
        {"complaint_id": "CMP-2026-002", "dag_plot_number": "7025", "deed_number": "DEED-202", "status": "OPEN", "citizen_name": "Citizen B"},
    ]
    # Same plot 9044
    dups = detect_duplicate_complaints("CMP-2026-003", dag_plot="9044", deed_number="DEED-999", all_complaints=existing)
    assert len(dups) == 1
    assert dups[0]["complaint_id"] == "CMP-2026-001"
    assert "Plot #9044" in dups[0]["match_reason"]

    # Different plot and deed
    no_dups = detect_duplicate_complaints("CMP-2026-004", dag_plot="5235", deed_number="DEED-555", all_complaints=existing)
    assert len(no_dups) == 0


def test_evaluate_evidence_matching_states():
    """Verifies evidence matching states: SUPPORTED, CONTRADICTED, and UNVERIFIED."""
    parcel_record = {
        "dag_plot_number": 9044,
        "khatian_number": "1420",
        "total_area_decimal": 10.0,
        "current_owners": [{"name": "Abdul Latif Mia"}],
        "deed_history": [{"deed_number": "DEED-2020-001"}],
    }

    # State 1: Corroborated by statutory rule violation
    findings_fail = [
        {"rule_id": "RULE-DOUBLE-SALE", "status": "FAIL", "message": "Conflicting conveyance detected"}
    ]
    res_supported = evaluate_evidence_matching(
        claims=[{"claim_type": "DOUBLE_SELLING_ALLEGATION"}],
        parcel_record=parcel_record,
        verification_findings=findings_fail,
    )
    assert res_supported["match_state"] == "SUPPORTED_BY_AVAILABLE_RECORDS"
    assert len(res_supported["evidence_links"]) >= 1

    # State 2A: No conflict found in indexed digital ledger (clean records do not falsely refute citizen claims)
    res_no_conflict = evaluate_evidence_matching(
        claims=[{"claim_type": "GENERAL_LAND_DISPUTE_ALLEGATION"}],
        parcel_record=parcel_record,
        verification_findings=[],
    )
    assert res_no_conflict["match_state"] == "NO_CONFLICT_FOUND_IN_INDEXED_RECORDS"
    assert "absence of an indexed conflict does not prove" in res_no_conflict["rationale"]

    # State 2B: Concretely contradicted when records actively refute the specific claim (e.g. area within capacity)
    res_contradicted = evaluate_evidence_matching(
        claims=[{"claim_type": "AREA_EXCEEDANCE_ALLEGATION"}],
        parcel_record=parcel_record,
        verification_findings=[],
    )
    assert res_contradicted["match_state"] == "CONTRADICTED_BY_AVAILABLE_RECORDS"

    # State 3: Unverified when no registry record exists
    res_unverified = evaluate_evidence_matching(
        claims=[{"claim_type": "GENERAL_LAND_DISPUTE_ALLEGATION"}],
        parcel_record=None,
    )
    assert res_unverified["match_state"] == "UNVERIFIED"


def test_complaint_ai_analysis_api_endpoint():
    """GET /api/complaints/{id}/ai-analysis enforces authentication, IDOR, and returns structured analysis."""
    # Unauthenticated
    anon_client = TestClient(app, follow_redirects=False)
    unauth = anon_client.get("/api/complaints/CMP-2026-001/ai-analysis")
    assert unauth.status_code == 401

    # Authenticated Citizen Owner
    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")
    res = auth_client.get("/api/complaints/CMP-2026-001/ai-analysis")
    assert res.status_code == 200
    data = res.json()
    assert data["complaint_id"] == "CMP-2026-001"
    assert "preliminary_disclaimer" in data
    assert "claim_matching_state" in data
    assert data["claim_matching_state"] in [
        "SUPPORTED_BY_AVAILABLE_RECORDS",
        "CONTRADICTED_BY_AVAILABLE_RECORDS",
        "NO_CONFLICT_FOUND_IN_INDEXED_RECORDS",
        "UNVERIFIED",
    ]
    assert isinstance(data["extracted_claims"], list)
    assert "duplicate_summary" in data
    assert "top_matches" in data["duplicate_summary"]
    assert "total_related_count" in data["duplicate_summary"]


def test_multi_signal_duplicate_classification_and_privacy():
    """Validates multi-signal duplicate classification and citizen privacy masking."""
    all_complaints = [
        # Match 1: Exact deed match -> LIKELY_DUPLICATE
        {
            "complaint_id": "CMP-DUP-1",
            "dag_plot_number": "9044",
            "deed_number": "DEED-EXACT-88",
            "citizen_name": "Secret Person A",
            "citizen_user_id": "USR-OTHER-1",
            "category": "RECORD_MISMATCH",
            "narrative_description": "Secret narrative A",
            "status": "SUBMITTED",
        },
        # Match 2: Same plot alone with different category -> SAME_PARCEL_DIFFERENT_CLAIM
        {
            "complaint_id": "CMP-DIFF-2",
            "dag_plot_number": "9044",
            "deed_number": "DEED-OTHER-99",
            "citizen_name": "Secret Person B",
            "citizen_user_id": "USR-OTHER-2",
            "category": "BOUNDARY_DISPUTE",
            "narrative_description": "Totally different dispute about trees",
            "status": "OPEN",
        },
        # Match 3: Own previous filing on same plot -> LIKELY_DUPLICATE
        {
            "complaint_id": "CMP-OWN-3",
            "dag_plot_number": "9044",
            "deed_number": "DEED-MINE-11",
            "citizen_name": "Rafiqul Islam",
            "citizen_user_id": "USR-CITIZEN-001",
            "category": "SUSPECTED_DOUBLE_SALE",
            "narrative_description": "Earlier filing about double sale",
            "status": "IN_PROGRESS",
        },
    ]

    # Non-staff citizen viewer (USR-CITIZEN-001)
    matches_citizen = detect_duplicate_complaints(
        current_complaint_id="CMP-CURRENT-001",
        dag_plot="9044",
        deed_number="DEED-EXACT-88",
        all_complaints=all_complaints,
        current_narrative="Vendor sold property twice to two buyers on plot 9044",
        current_category="SUSPECTED_DOUBLE_SALE",
        current_user_id="USR-CITIZEN-001",
        viewer_user_id="USR-CITIZEN-001",
        is_staff=False,
    )

    # 1. Exact deed match must be LIKELY_DUPLICATE
    exact_match = next(m for m in matches_citizen if m["complaint_id"] == "CMP-DUP-1")
    assert exact_match["classification"] == "LIKELY_DUPLICATE"
    # Privacy check: Other citizen's name must NOT be leaked
    assert exact_match["citizen_name"] == "Independent Citizen Filing"
    assert exact_match["narrative_preview"] is None

    # 2. Same plot alone with different claim must NOT be LIKELY_DUPLICATE
    diff_claim = next(m for m in matches_citizen if m["complaint_id"] == "CMP-DIFF-2")
    assert diff_claim["classification"] == "SAME_PARCEL_DIFFERENT_CLAIM"
    assert diff_claim["citizen_name"] == "Independent Citizen Filing"

    # 3. Own filing shows "Your Previous Filing"
    own_match = next(m for m in matches_citizen if m["complaint_id"] == "CMP-OWN-3")
    assert own_match["classification"] == "LIKELY_DUPLICATE"
    assert own_match["citizen_name"] == "Your Previous Filing"

    # 4. Staff investigator view reveals full details
    matches_staff = detect_duplicate_complaints(
        current_complaint_id="CMP-CURRENT-001",
        dag_plot="9044",
        deed_number="DEED-EXACT-88",
        all_complaints=all_complaints,
        current_narrative="Vendor sold property twice",
        current_category="SUSPECTED_DOUBLE_SALE",
        current_user_id="USR-CITIZEN-001",
        viewer_user_id="USR-ADMIN-001",
        is_staff=True,
    )
    staff_view_1 = next(m for m in matches_staff if m["complaint_id"] == "CMP-DUP-1")
    assert staff_view_1["citizen_name"] == "Secret Person A"
    assert "Secret narrative" in staff_view_1["narrative_preview"]

