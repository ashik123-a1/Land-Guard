"""Automated Test Suite for LandGuard Bilingual Localization Engine
Validates:
1. get_text() translation lookups, formatting, and safe fallback (never returns empty or crash).
2. Language resolution precedence (query param > cookie > user profile > default 'en').
3. POST /api/user/preferences updates user record in SQLite and sets landguard_lang cookie.
4. Citizen Portal pages render localized Bengali and English interfaces based on preference.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_web.localization import get_text, get_preferred_language, TRANSLATIONS
from src.landguard_web.service import service

client = TestClient(app, follow_redirects=False)


def test_get_text_translations_and_safe_fallback():
    """Verify standard translation dictionary lookup and safe fallback behavior."""
    # 1. English lookup
    assert get_text("Dashboard", lang="en") == "Dashboard"
    assert get_text("Verify Deed", lang="en") == "Verify Deed"

    # 2. Bengali lookup
    assert get_text("Dashboard", lang="bn") == "ড্যাশবোর্ড"
    assert get_text("Verify Deed", lang="bn") == "দলিল যাচাই"
    assert get_text("Citizen Portal", lang="bn") == "নাগরিক পোর্টাল"

    # 3. Missing translation in target language falls back safely to English
    assert get_text("Unregistered Random Key 123", lang="bn") == "Unregistered Random Key 123"

    # 4. Empty string handles cleanly
    assert get_text("", lang="bn") == ""


def test_language_resolution_precedence():
    """Verifies strict resolution hierarchy: query param > cookie > profile > default."""
    from starlette.datastructures import Headers, QueryParams
    from unittest.mock import MagicMock

    # Case 1: Query param ?lang=bn takes absolute top precedence
    req1 = MagicMock()
    req1.query_params = {"lang": "bn"}
    req1.cookies = {"landguard_lang": "en"}
    user1 = {"preferred_language": "en"}
    assert get_preferred_language(req1, user=user1) == "bn"

    # Case 2: Cookie takes precedence when query param is absent
    req2 = MagicMock()
    req2.query_params = {}
    req2.cookies = {"landguard_lang": "bn"}
    user2 = {"preferred_language": "en"}
    assert get_preferred_language(req2, user=user2) == "bn"

    # Case 3: User profile in DB takes precedence when cookie & param are absent
    req3 = MagicMock()
    req3.query_params = {}
    req3.cookies = {}
    user3 = {"preferred_language": "bn"}
    assert get_preferred_language(req3, user=user3) == "bn"

    # Case 4: Default fallback is 'bn'
    req4 = MagicMock()
    req4.query_params = {}
    req4.cookies = {}
    user4 = None
    assert get_preferred_language(req4, user=user4) == "bn"


def test_save_preferences_api_and_persistence():
    """POST /api/user/preferences persists preferred_language to SQLite and sets cookie."""
    auth_client = TestClient(app, follow_redirects=False)
    login_res = auth_client.post("/api/auth/demo-login?role=citizen")
    assert login_res.status_code == 200

    # 1. Switch to Bengali
    res = auth_client.post("/api/user/preferences", json={"preferred_language": "bn"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["preferred_language"] == "bn"
    assert "landguard_lang=bn" in res.headers.get("set-cookie", "")

    # Verify SQLite record updated
    user = service.get_user_profile("USR-CITIZEN-001")
    assert user is not None
    assert user.get("preferred_language") == "bn"

    # 2. Switch back to English
    res_en = auth_client.post("/api/user/preferences", json={"preferred_language": "en"})
    assert res_en.status_code == 200
    assert res_en.json()["preferred_language"] == "en"
    user_en = service.get_user_profile("USR-CITIZEN-001")
    assert user_en.get("preferred_language") == "en"


def test_citizen_portal_renders_bengali_ui():
    """Citizen portal routes render translated Bengali strings when preferred_language='bn' or ?lang=bn."""
    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")

    # Access dashboard with ?lang=bn
    res_bn = auth_client.get("/user/dashboard?lang=bn")
    assert res_bn.status_code == 200
    html_bn = res_bn.text

    # Verify Bengali UI elements are rendered
    assert "ড্যাশবোর্ড" in html_bn
    assert "নাগরিক পোর্টাল" in html_bn
    assert "দলিল যাচাই" in html_bn
    assert "ল্যান্ডগার্ড" in html_bn
    assert 'lang="bn"' in html_bn

    # Access dashboard with ?lang=en
    res_en = auth_client.get("/user/dashboard?lang=en")
    assert res_en.status_code == 200
    html_en = res_en.text
    assert "Dashboard" in html_en
    assert "Citizen Portal" in html_en
    assert 'lang="en"' in html_en


def test_status_badge_normalization_and_fallback():
    """Verify enum status normalizations (underscores, case, spacing) and Bengali translations."""
    # Standard uppercase enum with underscore
    assert get_text("UNDER_REVIEW", "bn") == "তদন্তাধীন"
    # Lowercase with underscore
    assert get_text("under_review", "bn") == "তদন্তাধীন"
    # Spaced version
    assert get_text("UNDER REVIEW", "bn") == "তদন্তাধীন"
    assert get_text("under review", "bn") == "তদন্তাধীন"

    # Other statuses
    assert get_text("CLEAR_TITLE", "bn") == "নিষ্কণ্টক স্বত্ব"
    assert get_text("CRITICAL", "bn") == "জরুরি / গুরুতর"
    assert get_text("CONFIRMED_INCONSISTENCY", "bn") == "নিশ্চিত অসঙ্গতি"
    assert get_text("TAMPERING_DETECTED", "bn") == "টেম্পারিং শনাক্ত হয়েছে"

    # Fallback to original string when unknown
    assert get_text("TOTALLY_UNKNOWN_STATUS_99", "bn") == "TOTALLY_UNKNOWN_STATUS_99"


def test_all_citizen_portal_pages_render_bengali_ui():
    """Verify that every citizen portal page renders localized Bengali text with ?lang=bn."""
    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")

    # 1. New Complaint Page (/user/complaints/new)
    res_comp_new = auth_client.get("/user/complaints/new?lang=bn")
    assert res_comp_new.status_code == 200
    html_new = res_comp_new.text
    assert "অভিযোগ দাখিল" in html_new
    assert "ক্যাডারস্ট্রাল দাগ নম্বর" in html_new
    assert "বিস্তারিত বিবরণ ও তথ্যাবলি" in html_new
    assert 'lang="bn"' in html_new

    # 2. Notifications Center (/user/notifications)
    res_notif = auth_client.get("/user/notifications?lang=bn")
    assert res_notif.status_code == 200
    html_notif = res_notif.text
    assert "বিজ্ঞপ্তি ও সতর্কবার্তা" in html_notif
    assert 'lang="bn"' in html_notif

    # 3. Digital Profile Page (/user/profile)
    res_prof = auth_client.get("/user/profile?lang=bn")
    assert res_prof.status_code == 200
    html_prof = res_prof.text
    assert "ডিজিটাল নাগরিক প্রোফাইল" in html_prof
    assert "অফিসিয়াল রেজিস্ট্রি তথ্য" in html_prof
    assert 'lang="bn"' in html_prof

    # 4. Interactive Verification Stepper (/user/verify)
    res_verify = auth_client.get("/user/verify?lang=bn")
    assert res_verify.status_code == 200
    html_verify = res_verify.text
    assert "স্বত্ব যাচাই" in html_verify
    assert "১. গ্রহণ" in html_verify
    assert "বাছাইকৃত বেঞ্চমার্ক সিনারিও দ্রুত নির্বাচন" in html_verify
    assert "সংবিধিবদ্ধ যাচাই পরিচালনা করুন" in html_verify
    assert 'lang="bn"' in html_verify

    # 5. Complaints List Page (/user/complaints)
    res_complaints = auth_client.get("/user/complaints?lang=bn")
    assert res_complaints.status_code == 200
    html_complaints = res_complaints.text
    assert "অভিযোগ ট্র্যাকিং" in html_complaints or "নাগরিক পোর্টাল" in html_complaints
    assert 'lang="bn"' in html_complaints

    # 6. Verification History Page (/user/history)
    res_hist = auth_client.get("/user/history?lang=bn")
    assert res_hist.status_code == 200
    assert 'lang="bn"' in res_hist.text

    # 7. Cadastral Parcels Page (/user/parcels)
    res_parcels = auth_client.get("/user/parcels?lang=bn")
    assert res_parcels.status_code == 200
    assert 'lang="bn"' in res_parcels.text

    # 8. User Settings Page (/user/settings)
    res_settings = auth_client.get("/user/settings?lang=bn")
    assert res_settings.status_code == 200
    assert 'lang="bn"' in res_settings.text


def test_complaint_detail_and_verify_detail_bengali_rendering():
    """Verify that detail view templates render localized Bengali labels and section headers."""
    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")

    # Create a fresh complaint to guarantee existing detail page
    create_res = auth_client.post(
        "/api/complaints",
        json={
            "title": "Bengali Localization Verification Case",
            "category": "SUSPECTED_DOUBLE_SALE",
            "dag_plot_number": "9044",
            "deed_number": "DEED-LOC-TEST",
            "narrative_description": "Testing Bengali localization on detail view.",
        },
    )
    assert create_res.status_code == 200
    comp_id = create_res.json()["complaint_id"]

    res_detail = auth_client.get(f"/user/complaints/{comp_id}?lang=bn")
    assert res_detail.status_code == 200
    html_detail = res_detail.text
    assert "কেস ট্র্যাকিং" in html_detail
    assert "নাগরিকের বিস্তারিত অভিযোগ" in html_detail
    assert "কেস নিষ্পত্তির সময়রেখা" in html_detail
    assert 'lang="bn"' in html_detail

    # Run a quick verification to get a verification ID
    ver_res = auth_client.post(
        "/api/verify",
        json={
            "confirmed_fields": {
                "deed_number": "DEED-LOC-001",
                "dag_plot_number": "9044",
                "transferred_area_decimal": 10.5,
                "execution_date": "2022-01-01",
                "seller_nid": "OWN-11CE5DD2",
                "buyer_nid": "OWN-CE177B4E",
                "previous_deed_ref": "DEED-2001-35323",
                "mutation_case_no": "MUT-2022-1001/Savar",
                "consideration_bdt": 1250000.0,
            }
        },
    )
    assert ver_res.status_code == 200
    ver_id = ver_res.json()["verification_id"]

    res_ver_detail = auth_client.get(f"/user/verify/{ver_id}?lang=bn")
    assert res_ver_detail.status_code == 200
    html_ver_detail = res_ver_detail.text
    assert "দলিল সংক্রান্ত তথ্যাবলি" in html_ver_detail
    assert "যাচাইয়ের ইতিহাসে ফিরে যান" in html_ver_detail
    assert 'lang="bn"' in html_ver_detail


def test_public_pages_render_bengali_ui():
    """Verify that public landing and login pages render localized Bengali text with ?lang=bn."""
    # Landing page
    res_land_bn = client.get("/?lang=bn")
    assert res_land_bn.status_code == 200
    assert 'lang="bn"' in res_land_bn.text
    assert "ল্যান্ডগার্ড" in res_land_bn.text
    assert "লগইন" in res_land_bn.text

    # Login page
    res_login_bn = client.get("/login?lang=bn")
    assert res_login_bn.status_code == 200
    assert 'lang="bn"' in res_login_bn.text
    assert "সাইন ইন" in res_login_bn.text or "লগইন" in res_login_bn.text


def test_admin_portal_renders_bengali_ui():
    """Verify that admin portal pages render localized Bengali text with ?lang=bn."""
    admin_client = TestClient(app, follow_redirects=False)
    admin_client.post("/api/auth/demo-login?role=admin")

    # 1. Dashboard
    res_dash = admin_client.get("/admin/dashboard?lang=bn")
    assert res_dash.status_code == 200
    assert 'lang="bn"' in res_dash.text
    assert "অপারেশন" in res_dash.text or "ল্যান্ডগার্ড" in res_dash.text

    # 2. Cases
    res_cases = admin_client.get("/admin/cases?lang=bn")
    assert res_cases.status_code == 200
    assert 'lang="bn"' in res_cases.text
    assert "তদন্ত কেস ডকেট" in res_cases.text

    # 3. Verifications
    res_ver = admin_client.get("/admin/verifications?lang=bn")
    assert res_ver.status_code == 200
    assert 'lang="bn"' in res_ver.text
    assert "সংবিধিবদ্ধ যাচাইকরণ" in res_ver.text

    # 4. Reports
    res_rep = admin_client.get("/admin/reports?lang=bn")
    assert res_rep.status_code == 200
    assert 'lang="bn"' in res_rep.text
    assert "সংবিধিবদ্ধ" in res_rep.text or "অডিট" in res_rep.text

    # 5. Users
    res_users = admin_client.get("/admin/users?lang=bn")
    assert res_users.status_code == 200
    assert 'lang="bn"' in res_users.text
    assert "ব্যবহারকারী ডিরেক্টরি" in res_users.text

    # 6. Audit
    res_audit = admin_client.get("/admin/audit?lang=bn")
    assert res_audit.status_code == 200
    assert 'lang="bn"' in res_audit.text
    assert "নিরাপত্তা ও কার্যক্রম অডিট ট্রেইল" in res_audit.text


def test_report_html_views_bengali_rendering():
    """Verify that HTML report viewers render authentic Bengali text with ?lang=bn."""
    admin_client = TestClient(app, follow_redirects=False)
    admin_client.post("/api/auth/demo-login?role=admin")

    # Access HTML formatted report for VRF-HIST-001 with ?lang=bn
    res_report = admin_client.get("/reports/VRF-HIST-001?lang=bn")
    assert res_report.status_code == 200
    assert 'lang="bn"' in res_report.text
    assert "সংবিধিবদ্ধ" in res_report.text
    assert "দলিল" in res_report.text

    # Access public verification certificate for VRF-HIST-001 with ?lang=bn
    res_cert = client.get("/verify/public/VRF-HIST-001?lang=bn")
    assert res_cert.status_code == 200
    assert 'lang="bn"' in res_cert.text
    assert "ল্যান্ডগার্ড" in res_cert.text
    assert "যাচাইকরণ" in res_cert.text


def test_bengali_pdf_generation_and_api_endpoint():
    """Verify authentic Bengali and English PDF generation service and HTTP endpoints."""
    import pymupdf  # PyMuPDF
    from src.landguard_reports.pdf_generator import generate_verification_pdf

    record = service.get_verification_record("VRF-HIST-001")
    assert record is not None

    # 1. Direct PDF Generation (Bengali)
    pdf_bytes_bn = generate_verification_pdf(record, lang="bn")
    assert pdf_bytes_bn is not None
    assert pdf_bytes_bn.startswith(b"%PDF-")
    assert len(pdf_bytes_bn) > 10000

    # Extract text using PyMuPDF to verify Bengali glyphs
    doc_bn = pymupdf.open(stream=pdf_bytes_bn, filetype="pdf")
    full_text_bn = "".join(page.get_text() for page in doc_bn)
    assert any(w in full_text_bn for w in ["বাংলাদেশ", "ল্যান্ডগার্ড", "যাচাইকরণ", "সংবিধিবদ্ধ"])
    assert "সাক্ষ্য আইন" in full_text_bn
    assert "বেঞ্চমার্ক" in full_text_bn

    # 2. Direct PDF Generation (English)
    pdf_bytes_en = generate_verification_pdf(record, lang="en")
    assert pdf_bytes_en is not None
    assert pdf_bytes_en.startswith(b"%PDF-")
    assert len(pdf_bytes_en) > 10000

    doc_en = pymupdf.open(stream=pdf_bytes_en, filetype="pdf")
    full_text_en = "".join(page.get_text() for page in doc_en)
    assert "LANDGUARD" in full_text_en

    # 3. HTTP API Endpoint with ?lang=bn
    admin_client = TestClient(app, follow_redirects=False)
    admin_client.post("/api/auth/demo-login?role=admin")

    res_api_bn = admin_client.get("/api/reports/pdf/VRF-HIST-001?lang=bn")
    assert res_api_bn.status_code == 200
    assert res_api_bn.headers["content-type"] == "application/pdf"
    assert "VRF-HIST-001_bn.pdf" in res_api_bn.headers.get("content-disposition", "")
    assert res_api_bn.content.startswith(b"%PDF-")

    # 4. HTTP API Endpoint with ?lang=en
    res_api_en = admin_client.get("/api/reports/pdf/VRF-HIST-001?lang=en")
    assert res_api_en.status_code == 200
    assert res_api_en.headers["content-type"] == "application/pdf"
    assert "VRF-HIST-001" in res_api_en.headers.get("content-disposition", "")
    assert res_api_en.content.startswith(b"%PDF-")


def test_all_statutory_rules_metadata_in_bengali_dictionary():
    """Verify that all 16 statutory rules in RULE_METADATA have complete Bengali and English entries."""
    from src.landguard_models.verification_rules import RULE_METADATA
    from src.landguard_web.localization import TRANSLATIONS

    bn_dict = TRANSLATIONS.get("bn", {})
    en_dict = TRANSLATIONS.get("en", {})
    for code, meta in RULE_METADATA.items():
        title = meta.get("title")
        expl = meta.get("default_explanation")

        assert title in en_dict, f"Title {title} missing in en_dict"
        assert title in bn_dict or code in bn_dict, f"Title {title} missing in bn_dict"
        assert expl in en_dict, f"Explanation for {code} missing in en_dict"
        assert expl in bn_dict, f"Explanation for {code} missing in bn_dict"



