"""Automated test suite for LandGuard Bilingual Voice Assistant and Intent Engine.
Validates:
1. Intent classification across PLOT_QUERY, VERIFICATION_STATUS, COMPLAINT_DRAFT, EXPEDITE_QUERY, and SYSTEM_HELP.
2. English and Bengali natural language transcript parsing with automatic digit normalization.
3. Strict safety rule: Mutating actions (COMPLAINT_DRAFT) require explicit confirmation readback.
4. Fast REST API endpoint POST /api/voice/parse-intent.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_ai.voice_assistant import (
    parse_bilingual_intent,
    to_en_digits,
    to_bn_digits,
    detect_language,
    normalize_romanized_bengali,
)

client = TestClient(app, follow_redirects=False)


def test_digit_normalization_and_language_detection():
    """Verify conversion between Bengali and Western Arabic numerals."""
    assert to_en_digits("প্লট ৯০৪৪ এবং ৭০২৫") == "প্লট 9044 এবং 7025"
    assert to_bn_digits("Plot 9044 and 7025") == "Plot ৯০৪৪ and ৭০২৫"

    assert detect_language("Check plot 9044") == "en"
    assert detect_language("প্লট ৯০৪৪ এর তথ্য দিন") == "bn"


def test_english_plot_query_intent():
    """English voice query for plot details extracts entities and generates navigation action."""
    res = parse_bilingual_intent("Can you check plot 9044 in Savar?")
    assert res["intent"] == "PLOT_QUERY"
    assert res["language"] == "en"
    assert res["entities"]["dag_plot_number"] == "9044"
    assert res["entities"]["location"] == "Savar"
    assert res["confirmation_required"] is False
    assert res["suggested_action"]["action"] == "NAVIGATE"
    assert "/user/parcels/9044" in res["suggested_action"]["url"]
    assert "Plot #9044" in res["spoken_response_en"]


def test_bengali_plot_query_intent():
    """Bengali voice query with Bengali numerals extracts normalized plot number and returns Bengali readback."""
    res = parse_bilingual_intent("প্লট ৯০৪৪ এর খতিয়ান এবং মালিকের তথ্য দিন")
    assert res["intent"] == "PLOT_QUERY"
    assert res["language"] == "bn"
    assert res["entities"]["dag_plot_number"] == "9044"
    assert res["confirmation_required"] is False
    assert "/user/parcels/9044" in res["suggested_action"]["url"]
    assert "৯০৪৪" in res["spoken_response_bn"]


def test_verification_status_intent_both_languages():
    """Queries mentioning verification IDs or deed status route to VERIFICATION_STATUS."""
    # English
    en_res = parse_bilingual_intent("What is the status of verification VRF-HIST-001?")
    assert en_res["intent"] == "VERIFICATION_STATUS"
    assert en_res["entities"]["verification_id"] == "VRF-HIST-001"
    assert "/verify/public/VRF-HIST-001" in en_res["suggested_action"]["url"]

    # Bengali
    bn_res = parse_bilingual_intent("আমার ভেরিফিকেশন VRF-HIST-002 এর ফলাফল কি?")
    assert bn_res["intent"] == "VERIFICATION_STATUS"
    assert bn_res["entities"]["verification_id"] == "VRF-HIST-002"
    assert "/verify/public/VRF-HIST-002" in bn_res["suggested_action"]["url"]


def test_complaint_draft_intent_requires_confirmation():
    """Complaint submission requests MUST flag confirmation_required=True for citizen readback safety."""
    # English
    en_res = parse_bilingual_intent("I want to file a fraud complaint about double selling on plot 9044")
    assert en_res["intent"] == "COMPLAINT_DRAFT"
    assert en_res["entities"]["dag_plot_number"] == "9044"
    assert en_res["confirmation_required"] is True
    assert en_res["suggested_action"]["action"] == "DRAFT_COMPLAINT"
    assert "confirm" in en_res["spoken_response_en"].lower()

    # Bengali
    bn_res = parse_bilingual_intent("দাগ ৯০৪৪ নিয়ে জালিয়াতি ও দ্বৈত বিক্রির অভিযোগ দায়ের করুন")
    assert bn_res["intent"] == "COMPLAINT_DRAFT"
    assert bn_res["entities"]["dag_plot_number"] == "9044"
    assert bn_res["confirmation_required"] is True
    assert bn_res["suggested_action"]["action"] == "DRAFT_COMPLAINT"
    assert "নিশ্চিত" in bn_res["spoken_response_bn"]


def test_expedite_and_help_intents():
    """Test general expedite inquiries and system help fallbacks."""
    exp_res = parse_bilingual_intent("How can I request an urgent expedited hearing?")
    assert exp_res["intent"] == "EXPEDITE_QUERY"
    assert exp_res["confirmation_required"] is False

    help_res = parse_bilingual_intent("How do I use LandGuard to protect my land?")
    assert help_res["intent"] == "SYSTEM_HELP"
    assert help_res["confirmation_required"] is False

    empty_res = parse_bilingual_intent("")
    assert empty_res["intent"] == "EMPTY_QUERY"


def test_voice_intent_api_endpoint():
    """POST /api/voice/parse-intent endpoint returns valid structured intent response."""
    # English call
    payload_en = {"text": "check plot 7025 in Paba", "language": "auto"}
    res_en = client.post("/api/voice/parse-intent", json=payload_en)
    assert res_en.status_code == 200
    data_en = res_en.json()
    assert data_en["intent"] == "PLOT_QUERY"
    assert data_en["entities"]["dag_plot_number"] == "7025"
    assert data_en["entities"]["location"] == "Paba"

    # Bengali call
    payload_bn = {"text": "প্লট ৭০২৫ এর বিরোধ সংক্রান্ত অভিযোগ করতে চাই", "language": "auto"}
    res_bn = client.post("/api/voice/parse-intent", json=payload_bn)
    assert res_bn.status_code == 200
    data_bn = res_bn.json()
    assert data_bn["intent"] == "COMPLAINT_DRAFT"
    assert data_bn["entities"]["dag_plot_number"] == "7025"
    assert data_bn["confirmation_required"] is True


def test_citizen_voice_page_access():
    """GET /user/voice requires citizen login; returns 200 with voice console when authenticated."""
    fresh_anon_client = TestClient(app, follow_redirects=False)
    unauth_res = fresh_anon_client.get("/user/voice")
    assert unauth_res.status_code == 303
    assert "/login" in unauth_res.headers["location"]

    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")
    auth_res = auth_client.get("/user/voice")
    assert auth_res.status_code == 200
    assert "LandGuard Voice Assistant" in auth_res.text
    assert "দ্বিভাষিক ভূমি সেবা ভয়েস সহকারী" in auth_res.text


def test_complaint_status_voice_intent():
    """Voice inquiry with complaint ID or status keywords maps to COMPLAINT_STATUS with navigation action."""
    # Bengali inquiry
    bn_res = parse_bilingual_intent("আমার অভিযোগ CMP-2026-001 এর অবস্থা কি?")
    assert bn_res["intent"] == "COMPLAINT_STATUS"
    assert bn_res["entities"]["complaint_id"] == "CMP-2026-001"
    assert "/user/complaints/CMP-2026-001" in bn_res["suggested_action"]["url"]
    assert "CMP-2026-001" in bn_res["spoken_response_bn"]

    # English inquiry
    en_res = parse_bilingual_intent("Check the status of complaint CMP-2026-002")
    assert en_res["intent"] == "COMPLAINT_STATUS"
    assert en_res["entities"]["complaint_id"] == "CMP-2026-002"
    assert "/user/complaints/CMP-2026-002" in en_res["suggested_action"]["url"]
    assert "CMP-2026-002" in en_res["spoken_response_en"]


def test_bengali_suffix_plot_query_intent():
    """Bengali queries where numeral precedes the word 'দাগ' (suffix form) correctly extract normalized plot number."""
    # Suffix form 1: '৯০৪৪ দাগ'
    res1 = parse_bilingual_intent("৯০৪৪ দাগের খতিয়ান ও রেকর্ড দেখতে চাই")
    assert res1["intent"] == "PLOT_QUERY"
    assert res1["entities"]["dag_plot_number"] == "9044"
    assert "/user/parcels/9044" in res1["suggested_action"]["url"]
    assert "৯০৪৪" in res1["spoken_response_bn"]

    # Suffix form 2: '৭০২৫ নং দাগ'
    res2 = parse_bilingual_intent("৭০২৫ নং দাগের জমির তথ্য দিন")
    assert res2["intent"] == "PLOT_QUERY"
    assert res2["entities"]["dag_plot_number"] == "7025"
    assert "/user/parcels/7025" in res2["suggested_action"]["url"]


def test_missing_plot_query_requires_plot_number():
    """Queries mentioning plots without specifying a plot number route to NEED_PLOT_NUMBER without inventing a fake plot."""
    res = parse_bilingual_intent("দাগের তথ্য চাই")
    assert res["intent"] == "NEED_PLOT_NUMBER"
    assert "dag_plot_number" not in res["entities"]
    assert res["suggested_action"]["action"] == "PROMPT_PLOT"
    assert "/user/parcels" in res["suggested_action"]["url"]
    assert "নম্বর" in res["spoken_response_bn"]


def test_missing_complaint_details_guidance():
    """Grievance requests without plot/deed route to COMPLAINT_DRAFT_MISSING_DETAILS without inventing a fake plot."""
    res = parse_bilingual_intent("আমি একটি জালিয়াতির অভিযোগ করতে চাই")
    assert res["intent"] == "COMPLAINT_DRAFT_MISSING_DETAILS"
    assert "dag_plot_number" not in res["entities"]
    assert res["confirmation_required"] is False
    assert "/user/complaints/new" in res["suggested_action"]["url"]


def test_ambiguous_non_land_query():
    """Unrecognized natural language queries outside the land domain route to AMBIGUOUS_QUERY."""
    res = parse_bilingual_intent("আজকের আবহাওয়া কেমন থাকবে?")
    assert res["intent"] == "AMBIGUOUS_QUERY"
    assert res["confidence"] < 0.50
    assert "বোঝা যায়নি" in res["spoken_response_bn"]


def test_voice_service_synthesize_speech():
    """VoiceService synthesizes MP3 audio bytes using neural female voices."""
    import asyncio
    from src.landguard_services.voice_service import VoiceService, BANGLA_FEMALE_VOICE, ENGLISH_FEMALE_VOICE
    assert BANGLA_FEMALE_VOICE == "bn-BD-NabanitaNeural"
    assert ENGLISH_FEMALE_VOICE == "en-US-AriaNeural"

    vs = VoiceService()
    # Test Bengali speech synthesis
    bn_audio = asyncio.run(vs.synthesize_speech("হ্যালো ল্যান্ডগার্ড", lang="bn"))
    assert isinstance(bn_audio, bytes)
    assert len(bn_audio) > 1000

    # Test English speech synthesis
    en_audio = asyncio.run(vs.synthesize_speech("Hello LandGuard", lang="en"))
    assert isinstance(en_audio, bytes)
    assert len(en_audio) > 1000

    # Test empty text raises ValueError
    with pytest.raises(ValueError):
        asyncio.run(vs.synthesize_speech("   ", lang="bn"))


def test_voice_tts_api_endpoint():
    """GET /api/voice/tts streams MP3 audio for both Bengali and English."""
    # Bengali female neural audio (Nabanita)
    bn_res = client.get("/api/voice/tts?text=হ্যালো&lang=bn")
    assert bn_res.status_code == 200
    assert bn_res.headers["content-type"] == "audio/mpeg"
    assert len(bn_res.content) > 1000

    # English female neural audio (Aria)
    en_res = client.get("/api/voice/tts?text=Hello&lang=en")
    assert en_res.status_code == 200
    assert en_res.headers["content-type"] == "audio/mpeg"
    assert len(en_res.content) > 1000

    # Empty text query validation
    bad_res = client.get("/api/voice/tts?text=%20&lang=bn")
    assert bad_res.status_code in [400, 422]


def test_romanized_bengali_normalization_and_auto_detection():
    """Verify Romanized Bengali speech phonetics are accurately normalized and classified as Bengali."""
    # "Aman Naam Aashiq" -> "আমার নাম আশিক"
    norm1 = normalize_romanized_bengali("Aman Naam Aashiq")
    assert norm1 == "আমার নাম আশিক"
    assert detect_language("Aman Naam Aashiq") == "bn"

    # "Amar plot 9044" -> "আমার প্লট ৯০৪৪"
    norm2 = normalize_romanized_bengali("Amar plot 9044")
    assert norm2 == "আমার প্লট ৯০৪৪"
    assert detect_language("Amar plot 9044") == "bn"

    # "Dag 9044 er totho din" -> "দাগ ৯০৪৪ এর তথ্য দিন"
    norm3 = normalize_romanized_bengali("Dag 9044 er totho din")
    assert norm3 == "দাগ ৯০৪৪ এর তথ্য দিন"
    assert detect_language("Dag 9044 er totho din") == "bn"

    # "Dak Bam bahut 307" -> "দাগ ৩০৭"
    norm4 = normalize_romanized_bengali("Dak Bam bahut 307")
    assert norm4 == "দাগ ৩০৭"
    assert detect_language("Dak Bam bahut 307") == "bn"

    # Genuine English queries must NOT be converted
    assert normalize_romanized_bengali("Search plot 9044") == "Search plot 9044"
    assert detect_language("Search plot 9044") == "en"

    assert normalize_romanized_bengali("What is the status of plot 9044") == "What is the status of plot 9044"
    assert detect_language("What is the status of plot 9044") == "en"


def test_greeting_and_citizen_intro_intents():
    """Verify greeting and citizen introduction intents in both English and Bengali."""
    # Bengali introduction with Romanized speech input
    bn_res = parse_bilingual_intent("Aman Naam Aashiq", language_preference="auto")
    assert bn_res["intent"] == "GREETING"
    assert bn_res["language"] == "bn"
    assert bn_res["entities"].get("citizen_name") == "আশিক"
    assert "স্বাগতম" in bn_res["spoken_response_bn"]

    # Bengali native script introduction
    bn_res2 = parse_bilingual_intent("আমার নাম আশিক", language_preference="auto")
    assert bn_res2["intent"] == "GREETING"
    assert bn_res2["language"] == "bn"
    assert bn_res2["entities"].get("citizen_name") == "আশিক"

    # English greeting
    en_res = parse_bilingual_intent("Hello, my name is Ashik", language_preference="auto")
    assert en_res["intent"] == "GREETING"
    assert en_res["language"] == "en"
    assert en_res["entities"].get("citizen_name") == "Ashik"
    assert "Hello" in en_res["spoken_response_en"]


def test_deed_query_not_found_bengali_and_english():
    """Queries for non-existent deed numbers report not found instead of ambiguous error."""
    # Bengali query with Bangla numerals
    bn_res = parse_bilingual_intent("দলিল নম্বর 404")
    assert bn_res["intent"] == "DEED_NOT_FOUND"
    assert bn_res["language"] == "bn"
    assert bn_res["entities"]["deed_number"] == "404"
    assert "দলিল নম্বর ৪০৪ খুঁজে পাওয়া যায়নি।" in bn_res["spoken_response_bn"]
    assert bn_res["suggested_action"]["url"] == "/user/verify"

    # Bengali variations
    bn_res_short = parse_bilingual_intent("দলিল 404")
    assert bn_res_short["intent"] == "DEED_NOT_FOUND"
    assert bn_res_short["entities"]["deed_number"] == "404"

    bn_res_suffix = parse_bilingual_intent("404 নম্বর দলিল")
    assert bn_res_suffix["intent"] == "DEED_NOT_FOUND"
    assert bn_res_suffix["entities"]["deed_number"] == "404"

    # English query
    en_res = parse_bilingual_intent("deed number 404")
    assert en_res["intent"] == "DEED_NOT_FOUND"
    assert en_res["language"] == "en"
    assert en_res["entities"]["deed_number"] == "404"
    assert "Deed number 404 was not found in registered records." in en_res["spoken_response_en"]


def test_deed_query_existing_status():
    """Queries for an existing deed number return DEED_STATUS with report link."""
    res = parse_bilingual_intent("দলিল DEED-2005-23539")
    assert res["intent"] == "DEED_STATUS"
    assert res["entities"]["deed_number"] == "DEED-2005-23539"
    assert "DEED-2005-23539" in res["spoken_response_en"] or "DEED-২০০৫-২৩৫৩৯" in res["spoken_response_bn"]
    assert res["suggested_action"]["url"].startswith("/reports/") or "/user/verify" in res["suggested_action"]["url"]





