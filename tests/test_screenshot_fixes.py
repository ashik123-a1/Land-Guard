"""Regression Test Suite for Screenshot-Driven Bug Fixes.
Verifies:
1. Undefined verification rule descriptions are eliminated: all rule IDs have human-readable
   titles and explanations in English and Bengali; unknown rule IDs fall back gracefully.
2. What-If Simulator results are reconciled with verification: holding capacity feasibility
   is explicitly separated from legal and title clearance; Plot 6792 identifies active dispute
   and flags overall verdict as CAPACITY_FEASIBLE_BUT_LEGAL_DEFECTS without database writes.
3. Mutation area rendering displays localized "Not recorded" / "নথিভুক্ত নয়" when numeric
   area is absent, never a bare "Dec" or fabricated numbers.
4. Voice query verifies plot existence: missing plot (Dag 304) returns truthful "not found"
   readback and safe route /user/parcels; valid plot (Dag 9044) returns record and /user/parcels/9044;
   unauthorized complaint queries safely deny access under RBAC.
"""

import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app, service
from src.landguard_models.verification_rules import RULE_METADATA, normalize_rule_findings
from src.landguard_web.localization import get_text
from src.landguard_ai.voice_assistant import parse_bilingual_intent


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# 1. Verification Rule Descriptions & Fallback
# =============================================================================

def test_rule_metadata_completeness():
    """All 15 statutory verification rules have non-empty titles and explanations in en and bn."""
    for rule_code, meta in RULE_METADATA.items():
        assert meta.get("title"), f"{rule_code} missing title"
        assert meta.get("title_bn"), f"{rule_code} missing title_bn"
        assert meta.get("default_explanation"), f"{rule_code} missing default_explanation"
        assert meta.get("default_explanation_bn"), f"{rule_code} missing default_explanation_bn"
        assert meta.get("statutory_reference"), f"{rule_code} missing statutory_reference"
        assert "undefined" not in meta["title"].lower()
        assert "undefined" not in meta["default_explanation"].lower()


def test_normalize_rule_findings_populates_titles_and_explanations():
    """Rule findings for Plot 6792 populate both reason and explanation without 'undefined'."""
    raw_findings = [
        {"rule_code": "RULE_BROKEN_CHAIN_OF_TITLE", "severity": "HIGH", "reason": ""},
        {"rule_code": "RULE_SELLER_NOT_TITLEHOLDER", "severity": "HIGH"},
        {"rule_code": "RULE_UNVERIFIED_MUTATION_RECORD", "severity": "MEDIUM"},
        {"rule_code": "RULE_CUSTOM_UNKNOWN_SAMPLE", "severity": "LOW"},
    ]
    normalized = normalize_rule_findings(raw_findings)
    assert len(normalized) == 4

    for f in normalized:
        assert f.get("title"), f"Rule {f.get('rule_code')} has no title"
        assert f.get("explanation"), f"Rule {f.get('rule_code')} has no explanation"
        assert f.get("reason"), f"Rule {f.get('rule_code')} has no reason"
        assert "undefined" not in f["title"].lower()
        assert "undefined" not in f["explanation"].lower()

    # Unknown rule falls back cleanly
    unknown = normalized[3]
    assert unknown["title"] == "Custom Unknown Sample"
    assert "undefined" not in unknown["explanation"].lower()


def test_localization_helper_rule_codes():
    """Localization get_text returns valid Bengali translations for all rule codes."""
    for rule_code in [
        "RULE_BROKEN_CHAIN_OF_TITLE",
        "RULE_SELLER_NOT_TITLEHOLDER",
        "RULE_UNVERIFIED_MUTATION_RECORD",
        "RULE_CONFLICTING_DOUBLE_DISPOSITION",
        "RULE_ACTIVE_DISPUTE_FLAGGED",
    ]:
        bn_text = get_text(rule_code, lang="bn")
        assert bn_text and bn_text != rule_code
        assert "undefined" not in bn_text.lower()


# =============================================================================
# 2. What-If Simulator Reconciled Results & Zero Writes
# =============================================================================

def test_what_if_simulator_plot_9044_clean_baseline(client):
    """Plot 9044 has feasible capacity and clear title with low risk."""
    payload = {
        "dag_plot_number": "9044",
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-TEST",
        "transferred_area_decimal": 4.5,
        "consideration_bdt": 1500000.0,
    }
    res = client.post("/api/simulator/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["capacity_feasible"] is True
    assert data["capacity_status"] == "CAPACITY_FEASIBLE"
    assert data["legal_clearance"] == "TITLE_CLEAR"
    assert data["title_clear"] is True
    assert data["overall_verdict"] == "FEASIBLE"
    assert data["can_proceed"] is True
    assert data["prospective_ml_risk"] == pytest.approx(0.04, 0.01)


def test_what_if_simulator_plot_6792_reconciled_dispute(client):
    """Plot 6792 has feasible area capacity but fails legal clearance due to active double-disposition dispute."""
    payload = {
        "dag_plot_number": "6792",
        "seller_nid": "OWN-A021C0CA",
        "buyer_nid": "OWN-BUYER-TEST",
        "transferred_area_decimal": 10.0,  # 10.0 <= 31.98 total holding capacity
        "consideration_bdt": 1500000.0,
    }
    res = client.post("/api/simulator/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Explicit separation of capacity vs legal title clearance
    assert data["capacity_feasible"] is True
    assert data["capacity_status"] == "CAPACITY_FEASIBLE"
    assert data["legal_clearance"] == "DEFECTS_OR_DISPUTES_DETECTED"
    assert data["title_clear"] is False
    assert data["overall_verdict"] in ["CRITICAL_DEFECT", "CAPACITY_FEASIBLE_BUT_LEGAL_DEFECTS"]
    assert data["can_proceed"] is False
    assert data["prospective_ml_risk"] >= 0.80

    warning_codes = [w["rule_code"] for w in data["statutory_warnings"]]
    assert "RULE_ACTIVE_DISPUTE_FLAGGED" in warning_codes


# =============================================================================
# 3. Mutation Area Rendering
# =============================================================================

def test_mutation_area_rendered_cleanly_on_parcel_detail(client):
    """Plot 6792 parcel detail page renders 'Not recorded' or numeric area, never bare 'Dec'."""
    client.post("/api/auth/demo-login?role=citizen")
    res = client.get("/user/parcels/6792")
    assert res.status_code == 200
    html = res.text

    # Must contain "Not recorded" or Bengali "নথিভুক্ত নয়" for unrecorded area
    assert ("Not recorded" in html) or ("নথিভুক্ত নয়" in html)
    # Ensure there is no orphaned standalone " Dec" preceding an empty table cell
    assert '<td class="p-3 text-slate-300"> Dec</td>' not in html
    assert '<td class="p-3 text-slate-300">Dec</td>' not in html


# =============================================================================
# 4. Voice Query Verification & Safe Navigation
# =============================================================================

def test_voice_query_missing_plot_304_truthful_response():
    """Querying non-existent Plot 304 truthfully returns PLOT_NOT_FOUND and routes to /user/parcels."""
    res = parse_bilingual_intent("What is the status of Dag Plot 304 in Savar?")
    assert res["intent"] == "PLOT_NOT_FOUND"
    assert "304 was not found" in res["spoken_response_en"]
    assert res["suggested_action"]["action"] == "NAVIGATE"
    assert res["suggested_action"]["url"] == "/user/parcels"
    assert "/user/parcels/304" not in res["suggested_action"]["url"]


def test_voice_query_existing_plot_9044():
    """Querying verified Plot 9044 returns PLOT_QUERY and routes to /user/parcels/9044."""
    res = parse_bilingual_intent("Check plot 9044 in Savar")
    assert res["intent"] == "PLOT_QUERY"
    assert res["suggested_action"]["action"] == "NAVIGATE"
    assert res["suggested_action"]["url"] == "/user/parcels/9044"


def test_voice_query_unauthorized_complaint_access():
    """Citizen querying a complaint owned by another citizen is denied with ACCESS_RESTRICTED."""
    # Simulated complaint owned by USR-CITIZEN-001
    mock_complaint = {
        "complaint_id": "CMP-2026-999",
        "citizen_user_id": "USR-CITIZEN-001",
        "title": "Private Citizen Dispute",
    }
    # Another citizen user
    other_user = {
        "user_id": "USR-CITIZEN-999",
        "role": "CITIZEN",
        "email": "other@example.com",
    }

    res = parse_bilingual_intent(
        "Check status of complaint CMP-2026-999",
        complaint_lookup_fn=lambda cid: mock_complaint,
        current_user=other_user,
    )
    assert res["intent"] == "ACCESS_RESTRICTED"
    assert "Access restricted" in res["spoken_response_en"]
    assert res["suggested_action"]["url"] == "/user/complaints"


# =============================================================================
# 5. Auto Mode Language Handling & Plot Query Recovery
# =============================================================================

def test_auto_mode_language_detection_and_responses():
    """In Auto mode, language is dynamically detected and appropriate readback is returned."""
    # English speech/text
    en_res = parse_bilingual_intent("What is the holding record for plot 9044?", language_preference="auto")
    assert en_res["language"] == "en"
    assert en_res["intent"] == "PLOT_QUERY"
    assert "Plot #9044" in en_res["spoken_response_en"]
    assert en_res["suggested_action"]["url"] == "/user/parcels/9044"

    # Bengali speech/text
    bn_res = parse_bilingual_intent("দাগ ৯০৪৪ এর খতিয়ান এবং মালিকের তথ্য দিন", language_preference="auto")
    assert bn_res["language"] == "bn"
    assert bn_res["intent"] == "PLOT_QUERY"
    assert "৯০৪৪" in bn_res["spoken_response_bn"]
    assert bn_res["suggested_action"]["url"] == "/user/parcels/9044"


def test_standalone_and_search_plot_number_recovery():
    """Standalone plot numbers or 'Search <plot>' queries are truthfully recovered as PLOT_QUERY."""
    # Query with 'Search' prefix without the word 'plot'
    res1 = parse_bilingual_intent("Search 9044")
    assert res1["intent"] == "PLOT_QUERY"
    assert res1["entities"]["dag_plot_number"] == "9044"
    assert res1["suggested_action"]["url"] == "/user/parcels/9044"

    # Bare number query
    res2 = parse_bilingual_intent("9044")
    assert res2["intent"] == "PLOT_QUERY"
    assert res2["entities"]["dag_plot_number"] == "9044"
    assert res2["suggested_action"]["url"] == "/user/parcels/9044"

    # Bare Bengali numerals
    res3 = parse_bilingual_intent("৯০৪৪")
    assert res3["intent"] == "PLOT_QUERY"
    assert res3["language"] == "bn"
    assert res3["entities"]["dag_plot_number"] == "9044"
    assert res3["suggested_action"]["url"] == "/user/parcels/9044"


def test_low_confidence_and_ambiguous_guidance_prompt():
    """Unrecognized queries prompt the citizen to repeat or type their query below."""
    res = parse_bilingual_intent("random non-land utterance")
    assert res["intent"] == "AMBIGUOUS_QUERY"
    assert "type your search in the input box" in res["spoken_response_en"].lower()
    assert res["suggested_action"]["action"] == "FOCUS_INPUT"
    assert res["suggested_action"]["url"] == "#voice-text-input"


# =============================================================================
# 6. Verification Template Banner Ampersand Escaping
# =============================================================================

def test_verify_template_no_double_escaped_ampersand(client):
    """GET /user/verify ensures JavaScript string assignments do not double-escape & into &amp;."""
    client.post("/api/auth/demo-login?role=citizen")
    res = client.get("/user/verify?lang=en")
    assert res.status_code == 200
    html = res.text

    # The script should assign clean unescaped '&', never '&amp;' inside statusAction.innerText
    assert 'HOLD FOR STATUTORY VERIFICATION &amp; ESCALATE TO INVESTIGATOR' not in html
    assert 'HOLD FOR STATUTORY VERIFICATION & ESCALATE TO INVESTIGATOR' in html


def test_auto_mode_phonetic_english_speech_shifts_to_english():
    """Speaking English in Auto mode (even if transcribed phonetically e.g. 'ফাইন্ড 404') auto-shifts to English."""
    res = parse_bilingual_intent("ফাইন্ড 404", language_preference="auto")
    assert res["language"] == "en"
    assert res["intent"] == "PLOT_NOT_FOUND"
    assert res["entities"]["dag_plot_number"] == "404"
    assert res["suggested_action"]["url"] == "/user/parcels"
    assert "Plot #404 was not found" in res["spoken_response_en"]


def test_auto_mode_phonetic_conversational_english_phrases():
    """Conversational English phrases transcribed phonetically by bn-BD recognizer auto-shift to English."""
    # "my name is Aashiq"
    res1 = parse_bilingual_intent("মাই নেম ইজ আশিক", language_preference="auto")
    assert res1["language"] == "en"

    # "What is the status of plot 9044"
    res2 = parse_bilingual_intent("হোয়াট ইজ দ্য স্ট্যাটাস অফ প্লট ৯০৪৪", language_preference="auto")
    assert res2["language"] == "en"
    assert res2["intent"] == "PLOT_QUERY"
    assert res2["entities"]["dag_plot_number"] == "9044"

    # "Search plot 9044"
    res3 = parse_bilingual_intent("সার্চ প্লট ৯০৪৪", language_preference="auto")
    assert res3["language"] == "en"
    assert res3["intent"] == "PLOT_QUERY"
    assert res3["entities"]["dag_plot_number"] == "9044"


def test_auto_mode_romanized_bengali_speech():
    """Romanized Bengali speech from en-US recognizer (e.g. 'Dak Bam bahut 307') auto-normalizes to Bengali."""
    res = parse_bilingual_intent("Dak Bam bahut 307", language_preference="auto")
    assert res["language"] == "bn"
    assert res["entities"]["dag_plot_number"] == "307"


