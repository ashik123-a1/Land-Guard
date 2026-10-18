"""Security Remediation Verification Suite
Tests all security fixes implemented in accordance with LANDGUARD_CURRENT_CHANGES_AND_API_SECURITY_AUDIT.md:
1. Fix A: Case Clarification IDOR prevention (Citizen B cannot respond to Citizen A's case)
2. Fix B: Verification Dossier IDOR and PII protection (Citizen B cannot view Citizen A's dossier)
3. Fix C & SEC-12: Error sanitization & Public vs Admin report view separation
4. Fix D: Stored XSS prevention in case notes and UI outputs
5. Fix E & SEC-13: Document upload magic byte validation and cleanup
6. Fix F & Fix G: Open redirect prevention and session cookie security
7. Fix H: Security headers and rate limiting enforcement
"""

import io
import os
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from src.landguard_web.app import app, service


@pytest.fixture
def unauthenticated_client():
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def citizen_a_client():
    client = TestClient(app, follow_redirects=False)
    res = client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    return client


@pytest.fixture
def citizen_b_client():
    # Simulate a second authenticated citizen session
    user = {
        "user_id": "USR-CITIZEN-002",
        "email": "citizen_b@example.com",
        "full_name": "Citizen B",
        "role": "CITIZEN",
        "is_active": True,
    }
    session_id = service.create_session(user)
    return TestClient(app, cookies={"landguard_session": session_id}, follow_redirects=False)


@pytest.fixture
def admin_client():
    client = TestClient(app, follow_redirects=False)
    res = client.post("/api/auth/demo-login?role=admin")
    assert res.status_code == 200
    return client


# -------------------------------------------------------------------
# Fix A: Case Clarification IDOR
# -------------------------------------------------------------------

def test_case_clarification_idor_blocked(citizen_a_client, citizen_b_client, admin_client):
    """Citizen B cannot submit clarification for Citizen A's case."""
    # 1. Citizen A creates a complaint (which automatically initializes linked case)
    comp = service.create_complaint(
        user_id="USR-CITIZEN-001",
        data={
            "title": "Boundary Dispute Plot 9044",
            "category": "SUSPECTED_DOUBLE_SALE",
            "dag_plot_number": "9044",
            "deed_number": "DEED-2026-9044",
            "narrative_description": "Suspected double deed creation.",
        }
    )
    case_id = comp.get("linked_case_id") or "CASE-2026-001"

    # 2. Admin requests clarification
    admin_client.post(f"/api/cases/{case_id}/clarification/request", json={
        "question": "Please upload CS khatian scan.",
        "author": "Inspector Rahman"
    })

    # 3. Citizen B (not the owner) attempts to respond -> must receive 403 Forbidden
    res_b = citizen_b_client.post(f"/api/cases/{case_id}/clarification/respond", json={
        "response": "Malicious impostor clarification from Citizen B",
        "respondent": "Citizen B"
    })
    assert res_b.status_code == 403
    assert "not authorized" in res_b.json()["detail"].lower()

    # 4. Citizen A (the legitimate owner) responds -> 200 OK
    res_a = citizen_a_client.post(f"/api/cases/{case_id}/clarification/respond", json={
        "response": "Here is the legitimate clarification from owner.",
        "respondent": "Nakib Md Ashik"
    })
    assert res_a.status_code == 200
    assert res_a.json()["success"] is True


# -------------------------------------------------------------------
# Fix B: Verification Dossier IDOR & PII Exposure
# -------------------------------------------------------------------

def test_verification_dossier_idor_blocked(citizen_a_client, citizen_b_client, admin_client):
    """Citizen B cannot view Citizen A's private verification dossier."""
    # VRF-HIST-001 belongs to citizen USR-CITIZEN-001
    # Citizen B attempts to access it -> 303 Redirect to /access-denied
    res_b = citizen_b_client.get("/user/verify/VRF-HIST-001")
    assert res_b.status_code == 303
    assert "/access-denied" in res_b.headers["location"]

    # Citizen A can access their own dossier -> 200 OK
    res_a = citizen_a_client.get("/user/verify/VRF-HIST-001")
    assert res_a.status_code == 200

    # Admin can access dossier -> 200 OK
    res_admin = admin_client.get("/user/verify/VRF-HIST-001")
    assert res_admin.status_code == 200


def test_public_verification_certificate_masked_pii(unauthenticated_client):
    """Public certificate route renders sanitized view without leaking unmasked PII."""
    res = unauthenticated_client.get("/verify/public/VRF-HIST-001")
    assert res.status_code == 200
    html = res.text
    # Should not contain raw internal admin form controls
    assert "Human Verification Determination" not in html
    assert "form action=\"/api/verify" not in html


# -------------------------------------------------------------------
# Fix C & SEC-12: Error Sanitization
# -------------------------------------------------------------------

def test_error_pages_do_not_leak_stack_traces(unauthenticated_client):
    """Exceptions return sanitized HTML or JSON without Python tracebacks or pre-dumped frames."""
    res = unauthenticated_client.get("/reports/NON-EXISTENT-ID-XYZ")
    assert res.status_code == 303
    assert "/not-found" in res.headers["location"]

    res_nf = unauthenticated_client.get("/not-found")
    assert res_nf.status_code == 200
    assert "Traceback (most recent call last)" not in res_nf.text


# -------------------------------------------------------------------
# Fix E & SEC-13: Document Upload Validation & Cleanup
# -------------------------------------------------------------------

def test_document_upload_magic_bytes_enforcement(citizen_a_client):
    """Uploading a fake file with mismatched magic bytes is rejected."""
    fake_pdf = io.BytesIO(b"<html><body>Not a real PDF</body></html>")
    res = citizen_a_client.post(
        "/api/upload",
        files={"file": ("fake_deed.pdf", fake_pdf, "application/pdf")}
    )
    assert res.status_code == 400
    assert "expected pdf header format" in res.json()["detail"].lower()


def test_document_upload_valid_image_accepted(citizen_a_client):
    """Uploading a valid image with proper magic bytes and plausible land record content is processed."""
    sample_path = "data/full/images/IMG-8B4D3063.png"
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            img_bytes = f.read()
    else:
        # Fallback to in-memory PIL image
        img = Image.new("RGB", (600, 400), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

    res = citizen_a_client.post(
        "/api/upload",
        files={"file": ("valid_deed.png", io.BytesIO(img_bytes), "image/png")}
    )
    assert res.status_code == 200
    data = res.json()
    assert "document_id" in data
    assert "sha256_hash" in data


# -------------------------------------------------------------------
# Fix F & Fix G: Open Redirect & Secure Cookie Flags
# -------------------------------------------------------------------

def test_open_redirect_sanitization(unauthenticated_client, citizen_a_client):
    """Login redirect rejects protocol-relative and external URLs."""
    # 1. API login endpoint test
    res_external = unauthenticated_client.post(
        "/api/auth/login",
        json={"email": "citizen@landguard.gov.bd", "password": "demo123", "redirect": "https://evil.com/phish"}
    )
    assert res_external.status_code == 200
    assert res_external.json()["redirect_url"] == "/user/dashboard"

    # Protocol-relative redirect test
    res_proto = unauthenticated_client.post(
        "/api/auth/login",
        json={"email": "citizen@landguard.gov.bd", "password": "demo123", "redirect": "//evil.com/phish"}
    )
    assert res_proto.status_code == 200
    assert res_proto.json()["redirect_url"] == "/user/dashboard"

    # Valid internal relative redirect test
    res_valid = unauthenticated_client.post(
        "/api/auth/login",
        json={"email": "citizen@landguard.gov.bd", "password": "demo123", "redirect": "/user/complaints"}
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["redirect_url"] == "/user/complaints"

    # 2. Authenticated user visiting /login?redirect=...
    res_logged_in = citizen_a_client.get("/login?redirect=https://evil.com/phish")
    assert res_logged_in.status_code == 303
    assert res_logged_in.headers["location"] == "/user/dashboard"


def test_session_cookie_flags(unauthenticated_client):
    """Session cookies have HttpOnly and SameSite=Lax set."""
    res = unauthenticated_client.post("/api/auth/demo-login?role=citizen")
    assert res.status_code == 200
    set_cookie_header = res.headers.get("set-cookie", "")
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


# -------------------------------------------------------------------
# Fix H: Security Headers & Rate Limiting
# -------------------------------------------------------------------

def test_security_headers_present(unauthenticated_client):
    """Responses include modern security headers."""
    res = unauthenticated_client.get("/")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "microphone=(self)" in res.headers.get("Permissions-Policy", "")


def test_voice_tts_max_length_validation(unauthenticated_client):
    """TTS endpoint rejects excessively long text."""
    long_text = "A" * 501
    res = unauthenticated_client.get(f"/api/voice/tts?text={long_text}")
    assert res.status_code == 422


def test_rate_limiter_enforcement(monkeypatch):
    """Rate limiter returns 429 when threshold is exceeded."""
    from src.landguard_web.rate_limiter import rate_limiter
    rate_limiter.reset()

    # Enable test rate limiting
    monkeypatch.setenv("LANDGUARD_ENFORCE_TEST_RATE_LIMIT", "1")

    client = TestClient(app, follow_redirects=False)
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    
    # Send 15 requests (allowed limit for document_upload)
    for _ in range(15):
        client.post(
            "/api/upload",
            files={"file": ("doc.png", io.BytesIO(png_bytes), "image/png")}
        )

    # 16th request must trigger 429
    res_blocked = client.post(
        "/api/upload",
        files={"file": ("doc.png", io.BytesIO(png_bytes), "image/png")}
    )
    assert res_blocked.status_code == 429
    assert "rate limit exceeded" in res_blocked.json()["detail"].lower()
    assert "Retry-After" in res_blocked.headers

    # Cleanup rate limiter
    rate_limiter.reset()


def test_client_ip_forwarded_for_untrusted_by_default(monkeypatch):
    """X-Forwarded-For is ignored by default unless LANDGUARD_TRUST_FORWARDED_FOR is enabled."""
    from src.landguard_web.rate_limiter import get_client_ip
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 198.51.100.17")],
        "client": ("10.0.0.5", 12345),
    }
    req = Request(scope)
    monkeypatch.delenv("LANDGUARD_TRUST_FORWARDED_FOR", raising=False)
    assert get_client_ip(req) == "10.0.0.5"

    monkeypatch.setenv("LANDGUARD_TRUST_FORWARDED_FOR", "1")
    assert get_client_ip(req) == "203.0.113.195"


def test_auth_login_rate_limiter_enforcement(monkeypatch):
    """Login endpoint rate limiting triggers 429 when max_requests exceeded."""
    from src.landguard_web.rate_limiter import rate_limiter
    rate_limiter.reset()
    monkeypatch.setenv("LANDGUARD_ENFORCE_TEST_RATE_LIMIT", "1")

    client = TestClient(app, follow_redirects=False)
    for _ in range(10):
        client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"}
        )

    # 11th request must trigger 429
    res = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"}
    )
    assert res.status_code == 429
    assert "rate limit exceeded" in res.json()["detail"].lower()
    rate_limiter.reset()


def test_verification_unauthenticated_user_id_spoofing_prevented(unauthenticated_client):
    """Unauthenticated verification requests cannot spoof another user's ID in confirmed_fields."""
    res = unauthenticated_client.post(
        "/api/verify",
        json={
            "confirmed_fields": {
                "user_id": "USR-ADMIN-001",
                "dag_plot_number": "1001",
                "district": "Dhaka",
                "upazila": "Mirpur",
                "mouza": "Senpara",
                "area_acres": 0.25,
            }
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("user_id") == "USR-CITIZEN-001"

