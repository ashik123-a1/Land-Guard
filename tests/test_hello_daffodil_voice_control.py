"""Comprehensive automated test suite for the LandGuard 'Hello Daffodil' Hands-Free Wake-Word
and Voice Navigation Control System.

Validates:
1. Wake-word detection and acoustic stripping for standalone and compound utterances ("Hello Daffodil open verification history").
2. Standalone activation intent (WAKE_WORD_ACTIVATION) in English and Bengali.
3. Bilingual wake-phrase support ("Hello Daffodil" & "হ্যালো ড্যাফোডিল").
4. Navigation Command Registry mapping to actual production routes:
   - Dashboard (/user/dashboard)
   - Verification History (/user/history)
   - Complaints / Grievance Queue (/user/complaints)
   - Notifications & Alerts (/user/notifications)
   - Cadastral Survey Registry (/user/parcels)
   - Verify Deed Portal (/user/verify)
   - Citizen Profile (/user/profile)
   - Settings & Preferences (/user/settings)
   - Back Navigation (javascript:window.history.back())
   - Stop / Standby Control (CONTROL_STOP)
5. Authoritative Cadastral Plot Query (e.g. Plot 9044 -> /user/parcels/9044).
6. Citizen Grievance Docket Status (e.g. CMP-2026-001 status).
7. Strict Safety Rule: Mutating actions (COMPLAINT_DRAFT) MUST require explicit confirmation (confirmation_required=True).
8. Administrative RBAC Guard: Citizen requests for Admin panels (/admin/...) trigger ACCESS_RESTRICTED.
9. API integration: POST /api/voice/parse-intent correctly processes wake-word compound queries.
10. Template Wiring: HTML template contains #handsFreeToggleBtn, #handsFreeDot, #handsFreeLabel, and 7 HUD states.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_ai.voice_assistant import (
    parse_bilingual_intent,
    strip_wake_word,
    to_en_digits,
    to_bn_digits,
)

client = TestClient(app, follow_redirects=False)


def test_wake_word_stripping_and_compound_utterance():
    """Verify that 'Hello Daffodil' is detected and cleanly stripped from compound commands."""
    # English compound query
    detected, cleaned = strip_wake_word("Hello Daffodil open verification history")
    assert detected is True
    assert cleaned.lower() == "open verification history"

    # English phonetic variations
    detected_hey, cleaned_hey = strip_wake_word("Hey Daffodil search plot 9044")
    assert detected_hey is True
    assert "9044" in cleaned_hey

    # Bengali compound query
    detected_bn, cleaned_bn = strip_wake_word("হ্যালো ড্যাফোডিল ভেরিফিকেশন ইতিহাস দেখাও")
    assert detected_bn is True
    assert "ভেরিফিকেশন ইতিহাস" in cleaned_bn


def test_standalone_wake_word_activation():
    """Standalone 'Hello Daffodil' triggers WAKE_WORD_ACTIVATION without navigation."""
    # English
    en_res = parse_bilingual_intent("Hello Daffodil")
    assert en_res["intent"] == "WAKE_WORD_ACTIVATION"
    assert en_res["entities"].get("wake_word_detected") is True
    assert en_res["confirmation_required"] is False
    assert en_res["suggested_action"]["action"] == "LISTEN"
    assert "listening" in en_res["spoken_response_en"].lower()

    # Bengali
    bn_res = parse_bilingual_intent("হ্যালো ড্যাফোডিল")
    assert bn_res["intent"] == "WAKE_WORD_ACTIVATION"
    assert bn_res["entities"].get("wake_word_detected") is True
    assert "সক্রিয়" in bn_res["spoken_response_bn"]


def test_compound_navigation_verification_history():
    """'Hello Daffodil open verification history' extracts wake word and navigates to /user/history."""
    res = parse_bilingual_intent("Hello Daffodil open verification history")
    assert res["intent"] == "NAVIGATE_HISTORY"
    assert res["entities"].get("wake_word_detected") is True
    assert res["confirmation_required"] is False
    assert res["suggested_action"]["action"] == "NAVIGATE"
    assert res["suggested_action"]["url"] == "/user/history"
    assert "Verification History" in res["spoken_response_en"]


def test_bengali_navigation_verification_history():
    """Bengali compound command navigates to verification history."""
    res = parse_bilingual_intent("হ্যালো ড্যাফোডিল যাচাই ইতিহাস দেখাও")
    assert res["intent"] == "NAVIGATE_HISTORY"
    assert res["entities"].get("wake_word_detected") is True
    assert res["suggested_action"]["url"] == "/user/history"


def test_navigation_registry_routes():
    """All supported production navigation routes are mapped accurately without mock paths."""
    route_expectations = [
        ("Hello Daffodil open dashboard", "NAVIGATE_DASHBOARD", "/user/dashboard"),
        ("Hello Daffodil show notifications", "NAVIGATE_NOTIFICATIONS", "/user/notifications"),
        ("Hello Daffodil open complaints", "NAVIGATE_COMPLAINTS", "/user/complaints"),
        ("Hello Daffodil open cadastral registry", "NAVIGATE_PARCELS", "/user/parcels"),
        ("Hello Daffodil verify deed", "NAVIGATE_VERIFY", "/user/verify"),
        ("Hello Daffodil my profile", "NAVIGATE_PROFILE", "/user/profile"),
        ("Hello Daffodil open settings", "NAVIGATE_SETTINGS", "/user/settings"),
    ]

    for utterance, expected_intent, expected_url in route_expectations:
        result = parse_bilingual_intent(utterance)
        assert result["intent"] == expected_intent, f"Failed for {utterance}"
        assert result["suggested_action"]["action"] == "NAVIGATE"
        assert result["suggested_action"]["url"] == expected_url
        assert result["confirmation_required"] is False


def test_back_and_stop_controls():
    """Voice assistant handles 'go back' and 'stop listening' safely."""
    # Go back
    back_res = parse_bilingual_intent("Hello Daffodil go back")
    assert back_res["intent"] == "NAVIGATE_BACK"
    assert back_res["suggested_action"]["action"] == "BACK"
    assert "history.back" in back_res["suggested_action"]["url"]

    # Stop
    stop_res = parse_bilingual_intent("Hello Daffodil stop listening")
    assert stop_res["intent"] == "CONTROL_STOP"
    assert stop_res["suggested_action"]["action"] == "STOP"


def test_authoritative_plot_query_9044():
    """'Hello Daffodil Search Plot 9044' extracts plot 9044 and navigates to /user/parcels/9044."""
    res = parse_bilingual_intent("Hello Daffodil search plot 9044")
    assert res["intent"] == "PLOT_QUERY"
    assert res["entities"]["dag_plot_number"] == "9044"
    assert res["entities"].get("wake_word_detected") is True
    assert res["suggested_action"]["action"] == "NAVIGATE"
    assert res["suggested_action"]["url"] == "/user/parcels/9044"


def test_complaint_status_query():
    """Status lookup for a specific complaint ID."""
    res = parse_bilingual_intent("Hello Daffodil check status of complaint CMP-2026-001")
    assert res["intent"] == "COMPLAINT_STATUS"
    assert res["entities"]["complaint_id"] == "CMP-2026-001"
    assert res["confirmation_required"] is False
    assert "/user/complaints/CMP-2026-001" in res["suggested_action"]["url"]


def test_mutating_actions_require_confirmation_safety():
    """Mutating complaint drafting with wake word MUST enforce confirmation_required=True."""
    res = parse_bilingual_intent("Hello Daffodil I want to file a land fraud dispute complaint on plot 9044")
    assert res["intent"] == "COMPLAINT_DRAFT"
    assert res["entities"]["dag_plot_number"] == "9044"
    assert res["confirmation_required"] is True
    assert res["suggested_action"]["action"] == "DRAFT_COMPLAINT"
    assert "confirm" in res["spoken_response_en"].lower()


def test_citizen_admin_rbac_guard():
    """Non-admin citizens requesting admin dockets receive ACCESS_RESTRICTED."""
    # Citizen user context
    citizen_user = {"username": "citizen", "role": "CITIZEN"}
    res = parse_bilingual_intent("Hello Daffodil open admin cases", current_user=citizen_user)
    assert res["intent"] == "ACCESS_RESTRICTED"
    assert "restricted" in res["spoken_response_en"].lower()
    assert res["suggested_action"]["url"] == "/user/dashboard"

    # Admin user context
    admin_user = {"username": "admin", "role": "ADMIN"}
    admin_res = parse_bilingual_intent("Hello Daffodil open admin cases", current_user=admin_user)
    # Admin is not blocked by RBAC
    assert admin_res["intent"] != "ACCESS_RESTRICTED"


def test_voice_api_parse_intent_with_wake_word():
    """REST API endpoint POST /api/voice/parse-intent correctly processes wake-word compound query."""
    resp = client.post(
        "/api/voice/parse-intent",
        json={"text": "Hello Daffodil open verification history", "language": "auto"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "NAVIGATE_HISTORY"
    assert data["entities"].get("wake_word_detected") is True
    assert data["suggested_action"]["url"] == "/user/history"


def test_voice_template_hands_free_ui_wiring():
    """Verify that user/voice.html contains the Hands-Free wake-word UI elements and 7 states."""
    from pathlib import Path
    template_path = Path("src/landguard_web/templates/user/voice.html")
    assert template_path.exists(), "voice.html template must exist"
    content = template_path.read_text(encoding="utf-8")

    # Hands-Free toggle button & telemetry indicators
    assert 'id="handsFreeToggleBtn"' in content
    assert 'id="handsFreeDot"' in content
    assert 'id="handsFreeLabel"' in content
    assert 'toggleHandsFreeMode()' in content

    # 7 distinct HUD visual states
    assert "HANDS_FREE_DISABLED" in content
    assert "WAKE_WORD_STANDBY" in content
    assert "WAKE_WORD_DETECTED" in content
    assert "LISTENING" in content
    assert "ANALYZING" in content or "PROCESSING" in content
    assert "SPEAKING" in content
    assert "PERMISSION_REQUIRED" in content or "ERROR" in content

    # Audio cue & auto-navigation
    assert "activate" in content
    assert "auto-nav-countdown" in content
    assert "cancelAutoNav" in content

    # Stop Daffodil interception & persistent session controls
    assert "STOP_DAFFODIL_REGEX" in content
    assert "handleStopDaffodil" in content
    assert "processSpotterTranscript" in content
    assert "simulateSpeechInput" in content
    assert "isSessionActivated" in content


def test_stop_daffodil_intent_english_and_bengali():
    """Verify that 'Stop Daffodil' and 'স্টপ ড্যাফোডিল' trigger CONTROL_STOP_DAFFODIL with hands_free_deactivate=True."""
    # English
    en_res = parse_bilingual_intent("Stop Daffodil")
    assert en_res["intent"] == "CONTROL_STOP_DAFFODIL"
    assert en_res["entities"].get("hands_free_deactivate") is True
    assert en_res["suggested_action"]["action"] == "DEACTIVATE_HANDS_FREE"
    assert "deactivated" in en_res["spoken_response_en"].lower()

    # Bengali
    bn_res = parse_bilingual_intent("স্টপ ড্যাফোডিল")
    assert bn_res["intent"] == "CONTROL_STOP_DAFFODIL"
    assert bn_res["entities"].get("hands_free_deactivate") is True
    assert bn_res["suggested_action"]["action"] == "DEACTIVATE_HANDS_FREE"


def test_multi_consecutive_commands_sequence():
    """Verify backend intent parsing across consecutive commands in an active hands-free session."""
    # 1. Wake word activation
    step1 = parse_bilingual_intent("Hello Daffodil")
    assert step1["intent"] == "WAKE_WORD_ACTIVATION"

    # 2. Command 1 (English navigation)
    step2 = parse_bilingual_intent("open verification history")
    assert step2["intent"] == "NAVIGATE_HISTORY"
    assert step2["suggested_action"]["url"] == "/user/history"

    # 3. Command 2 (Plot search)
    step3 = parse_bilingual_intent("Search plot 9044")
    assert step3["intent"] == "PLOT_QUERY"
    assert step3["entities"]["dag_plot_number"] == "9044"

    # 4. Command 3 (Bengali plot query)
    step4 = parse_bilingual_intent("দাগ ৯০৪৪ এর তথ্য দিন")
    assert step4["intent"] == "PLOT_QUERY"
    assert step4["entities"]["dag_plot_number"] == "9044"

    # 5. Stop command
    step5 = parse_bilingual_intent("Stop Daffodil")
    assert step5["intent"] == "CONTROL_STOP_DAFFODIL"
    assert step5["entities"].get("hands_free_deactivate") is True


def test_bengali_phonetic_wake_word_variations():
    """Verify that colloquial Bengali and Banglish transcriptions of 'Hello Daffodil' activate properly."""
    variations = [
        "hellow deffodil",
        "hello defodil",
        "hello, daffodil",
        "হ্যালো ডেফোডিল",
        "হ্যালো ডাফোডিল",
        "হেলো ডেফোডিল",
        "হেলো ড্যাফোডিল",
    ]
    for utterance in variations:
        detected, cleaned = strip_wake_word(utterance)
        assert detected is True, f"Failed strip_wake_word for {utterance}"
        assert cleaned == "", f"Cleaned was not empty for {utterance}: {cleaned}"

        res = parse_bilingual_intent(utterance)
        assert res["intent"] == "WAKE_WORD_ACTIVATION", f"Failed intent for {utterance}: {res['intent']}"
        assert res["entities"].get("wake_word_detected") is True
        assert res["suggested_action"]["action"] == "LISTEN"

    # Compound navigation with Bengali phonetic transcription
    compound_res = parse_bilingual_intent("হ্যালো ডেফোডিল ড্যাশবোর্ড দেখাও")
    assert compound_res["intent"] == "NAVIGATE_DASHBOARD"
    assert compound_res["suggested_action"]["url"] == "/user/dashboard"

    # Stop Daffodil Bengali phonetic variations
    stop_res = parse_bilingual_intent("স্টপ ডেফোডিল")
    assert stop_res["intent"] == "CONTROL_STOP_DAFFODIL"
    assert stop_res["entities"].get("hands_free_deactivate") is True


