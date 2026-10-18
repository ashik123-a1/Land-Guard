# LandGuard Operational Audit & Comprehensive API Security Assessment

**Project:** `F:\land gurd main project\`  
**Date:** October 18, 2026  
**Auditor Mode:** Autonomous Defensive Cybersecurity & Static Application Security Testing (SAST)  
**Execution Policy:** Strict Read-Only Audit — Zero Code Modifications, Zero Database Mutations  
**Target Output:** `LANDGUARD_CURRENT_CHANGES_AND_API_SECURITY_AUDIT.md` (Sole Permitted Artifact)

---

## Executive Summary

This report delivers a rigorous, static and behavioral security audit of the LandGuard codebase (`F:\land gurd main project\`). The audit evaluated the complete web stack, including FastAPI route declarations, middleware pipelines, authentication and session stores, domain services, SQLite operational persistence, Jinja2 template rendering, computer vision/OCR pipelines, ML risk inference, and the automated test suite.

The assessment identified **13 distinct security findings**, categorized across **Critical**, **High**, **Medium**, **Low**, and **Informational** severity levels. Notably, while LandGuard implements commendable defensive measures in certain areas (such as PBKDF2-HMAC-SHA256 password hashing and parameterized SQL queries across SQLite and PostgreSQL repositories), critical authorization gaps (IDOR), unauthenticated access to confidential citizen verification dossiers, stored cross-site scripting (XSS) vectors, and unauthenticated compute exhaustion risks exist that require immediate architectural hardening.

---

## Part 1: Summary of Recent Changes & System Effects

Prior to the security assessment, substantial localization, cadastral expansion, and UI stability changes were integrated across the application. The table below outlines these modifications and their functional effects:

| Module / Area | Files Modified | Core Changes Implemented | Functional & System Effect |
| :--- | :--- | :--- | :--- |
| **Bilingual Localization** | `src/landguard_web/localization.py`, `src/landguard_web/templates/**/*.html` | Established unified bilingual translation catalog (`en` and `bn`). Replaced hardcoded UI strings with `_('...')` helpers. | Allows seamless runtime switching between Bengali and English across Public, Citizen, Admin, and Investigator portals without session disruption. |
| **Verification & PDF Reports** | `src/landguard_reports/pdf_generator.py`, `src/landguard_web/routers/reports.py` | Added bilingual dossier support to ReportLab binary PDF generator and web certificate viewer. | Citizens and registrars can download official statutory verification dossiers and printable certificates rendered in Bengali or English. |
| **Voice Assistant** | `src/landguard_ai/voice_assistant.py`, `src/landguard_web/routers/voice.py` | Implemented "Hello Daffodil" wake-word normalization, phonetic Bengali numeral conversion, and Edge-TTS neural speech synthesis (`bn-BD-NabanitaNeural`). | Enables hands-free, spoken grievance lookups and cadastral searches for both English and Bangladeshi Bengali speakers. |
| **Cadastral Management** | `src/landguard_web/routers/parcels.py`, `src/landguard_data/repositories/parcels.py` | Added Admin Cadastral Parcel Registration endpoint (`POST /admin/parcels`) with strict duplicate prevention across Mouza and Upazila. | Prevents double-indexing of cadastral land parcels; enforces 409 Conflict if a dag plot already exists in the same mouza/upazila. |
| **Session & Language Persistence** | `src/landguard_web/dependencies.py`, `src/landguard_web/routers/auth.py` | Added cookie-based (`landguard_lang`) and user-profile-based language persistence. | Preserves citizen/staff language preference across internal navigation, form submissions, and repeated logins. |

---

## Part 2: Vulnerability Classification Matrix

| Finding ID | Severity | Category | Vulnerability Title | Primary Location |
| :--- | :---: | :--- | :--- | :--- |
| **SEC-01** | **HIGH** | Broken Access Control / IDOR | Case Clarification Response Unauthorized State Mutation & Note Injection | `src/landguard_web/routers/cases.py#L161-L185` |
| **SEC-02** | **HIGH** | Broken Access Control / IDOR | Citizen Verification Dossier Detail Lack of Ownership Verification | `src/landguard_web/routers/verifications.py#L44-L61` |
| **SEC-03** | **HIGH** | Information Disclosure / PII | Public Verification Endpoints Exposing Unmasked Dossiers & Citizen PII | `src/landguard_web/routers/reports.py#L124-L174` |
| **SEC-04** | **HIGH** | Cross-Site Scripting (XSS) | Stored XSS via Case Notes & Dynamic Template String Injections | `src/landguard_web/templates/index.html#L1877-L1883` |
| **SEC-05** | **HIGH** | Denial of Service (DoS) | Unauthenticated Compute & Resource Exhaustion on OCR & Verification APIs | `src/landguard_web/routers/verifications.py#L119-L145` |
| **SEC-06** | **HIGH** | Open Redirection | Unvalidated `redirect` Parameter in Authentication Flow | `src/landguard_web/routers/auth.py#L34-L48`, `L90-L95` |
| **SEC-07** | **MEDIUM** | Cross-Site Request Forgery | Missing CSRF Defense-in-Depth on Mutating State Endpoints | Global Web Router Architecture |
| **SEC-08** | **MEDIUM** | Security Misconfiguration | Session Cookies Missing `Secure` Flag & Absence of Global Security Headers | `src/landguard_web/routers/auth.py#L95-L101`, `app.py` |
| **SEC-09** | **MEDIUM** | Cryptographic Weakness | Hardcoded Secret Key Fallback & Plaintext Password Compatibility | `src/landguard_web/security.py#L42-L44`, `L49` |
| **SEC-10** | **MEDIUM** | Resource Exhaustion | Unbounded Neural Text-To-Speech (TTS) Proxy Abuse | `src/landguard_web/routers/voice.py#L52-L89` |
| **SEC-11** | **LOW** | Privilege Escalation Risk | One-Click Demo Login Privilege Escalation in Non-Production Mode | `src/landguard_web/routers/auth.py#L105-L138` |
| **SEC-12** | **LOW** | Information Disclosure | Unhandled Internal Stack Trace Leakage in Report Error Handler | `src/landguard_web/routers/reports.py#L52-L57` |
| **SEC-13** | **LOW** | Storage Exhaustion | Orphaned File Ingestion & SQLite Records on Document Validation Rejection | `src/landguard_services/document_service.py#L51-L99` |

---

## Part 3: Detailed Security Findings

### SEC-01: Case Clarification Response Unauthorized State Mutation & Note Injection (IDOR)
- **Severity:** **HIGH** (CVSS: 8.1 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:H`)
- **Vulnerability Category:** Insecure Direct Object Reference (IDOR) / Broken Object Level Authorization
- **Location:**
  - `src/landguard_web/routers/cases.py#L161-L185`
  - `src/landguard_services/case_service.py#L221-L260`
- **Description:**
  The endpoint `POST /api/cases/{case_id}/clarification/respond` allows citizens to provide supplementary evidence or clarifications requested by land investigators. The route enforces authentication via `require_citizen_access(request)`. However, neither the route handler nor `case_service.respond_case_clarification()` verifies that the authenticated user (`user["user_id"]`) is the actual citizen who filed the underlying complaint or is associated with the case.
- **Evidence:**
  ```python
  # src/landguard_web/routers/cases.py:161-174
  @router.post("/api/cases/{case_id}/clarification/respond")
  async def respond_case_clarification_endpoint(case_id: str, req: ClarificationResponseRequest, request: Request):
      user = require_citizen_access(request)  # Only checks if user.role == 'CITIZEN'
      ...
      updated = service.respond_case_clarification(
          case_id=case_id,
          response_text=req.response_text,
          user_id=user["user_id"],
      )
  ```
  In `CaseService.respond_case_clarification`:
  ```python
  # src/landguard_services/case_service.py:221-235
  target = self.get_case(case_id)
  if not target:
      return None
  # No check comparing target["citizen_user_id"] with user_id!
  ```
- **Impact:**
  Any authenticated citizen can manipulate any administrative investigation case in the LandGuard docket. An attacker can inject unauthorized text into the official investigator case notes, force a case status from `AWAITING_INFORMATION` back to `UNDER_REVIEW`, and trigger automated notifications to government investigators.
- **Defensive Remediation:**
  Assert ownership before proceeding:
  ```python
  if user.get("role") == "CITIZEN":
      linked_complaint = service.get_complaint(target.get("complaint_id"))
      if not linked_complaint or linked_complaint.get("citizen_user_id") != user["user_id"]:
          raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to respond to this case.")
  ```

---

### SEC-02: Citizen Verification Dossier Detail Lack of Ownership Verification (IDOR)
- **Severity:** **HIGH** (CVSS: 7.5 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`)
- **Vulnerability Category:** Insecure Direct Object Reference (IDOR) / PII Exposure
- **Location:**
  - `src/landguard_web/routers/verifications.py#L44-L61`
- **Description:**
  The route `GET /user/verify/{verification_id}` provides the citizen-facing verification result workspace. It enforces citizen authentication via `require_citizen_access(request)`. However, once authenticated, any citizen can pass any `verification_id` parameter (e.g., `VRF-2024-001`, `VRF-HIST-001`) and inspect the full, unmasked verification dossier of other citizens.
- **Evidence:**
  ```python
  # src/landguard_web/routers/verifications.py:44-54
  @router.get("/user/verify/{verification_id}", response_class=HTMLResponse)
  async def citizen_verification_detail(request: Request, verification_id: str):
      user = require_citizen_access(request)
      pref_lang = get_preferred_language(request, user)
      rec = service.get_verification_record(verification_id)
      if not rec:
          return RedirectResponse(url="/not-found", status_code=status.HTTP_303_SEE_OTHER)

      # Missing: rec.get("user_id") == user["user_id"] verification
      return templates.TemplateResponse(
          request=request,
          name="user/verification_detail.html",
          context={"request": request, "record": rec, "current_user": user, "current_lang": pref_lang},
      )
  ```
- **Impact:**
  Complete exposure of sensitive citizen land records to other authenticated users, including unmasked National Identity Numbers (NIDs), private land transfer values, seller and buyer legal identities, and rule violation flags.
- **Defensive Remediation:**
  Validate that the record belongs to the requesting citizen:
  ```python
  if user.get("role") == "CITIZEN" and rec.get("user_id") and rec.get("user_id") != user["user_id"]:
      return RedirectResponse(url="/access-denied", status_code=status.HTTP_303_SEE_OTHER)
  ```

---

### SEC-03: Public Verification Endpoints Exposing Unmasked Dossiers & Citizen PII
- **Severity:** **HIGH** (CVSS: 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`)
- **Vulnerability Category:** Sensitive Data Exposure / Missing Authentication
- **Location:**
  - `src/landguard_web/routers/reports.py#L59-L72`, `L124-L131`, `L133-L146`, `L148-L174`
  - `src/landguard_services/report_service.py#L25-L55`, `L104-L168`
- **Description:**
  LandGuard implements a privacy-preserving public verification function (`get_sanitized_public_verification`) that masks National ID numbers and strips internal data. However, multiple other endpoints intended for reports, printing, and PDFs bypass this privacy filter and are exposed without authentication.
- **Evidence:**
  ```python
  # src/landguard_web/routers/reports.py:124-130
  @router.get("/api/reports/{verification_id}")
  async def get_verification_report(verification_id: str):
      # No authentication dependency at all!
      rep = service.generate_report(verification_id)
      if not rep:
          raise HTTPException(status_code=404, detail=f"Verification '{verification_id}' not found.")
      return rep  # Contains rep["verification"] which has raw unmasked NIDs and PII!
  ```
  Similarly, `GET /api/reports/html/{verification_id}`, `GET /reports/{verification_id}/print`, and `GET /api/reports/pdf/{verification_id}` all generate unmasked administrative evidence dossiers and are publicly callable without session authentication.
- **Impact:**
  Anyone on the public internet can enumerate verification IDs (or scan the QR code on a document) and call `/api/reports/{id}` or `/api/reports/pdf/{id}` to harvest full unmasked citizen NIDs, owner identities, and internal fraud risk calculations.
- **Defensive Remediation:**
  1. Restrict `/api/reports/{verification_id}`, `/api/reports/html/{verification_id}`, and `/api/reports/pdf/{verification_id}` to authenticated users (`require_api_authenticated_user`).
  2. For anonymous public lookups via QR code or portal, strictly serve the sanitized dictionary produced by `get_sanitized_public_verification(verification_id)`.

---

### SEC-04: Stored Cross-Site Scripting (XSS) via Case Notes & Template Injections
- **Severity:** **HIGH** (CVSS: 8.0 - `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:U/C:H/I:H/A:N`)
- **Vulnerability Category:** Stored Cross-Site Scripting (CWE-79)
- **Location:**
  - `src/landguard_web/templates/index.html#L1877-L1883`
  - `src/landguard_web/templates/user/verify.html#L2564-L2569`
  - `src/landguard_web/templates/user/complaint_detail.html#L245-L255`
- **Description:**
  Case notes, AI claim extracts, and cadastral metadata are inserted into client-side DOM elements via `.innerHTML = ...` using unescaped JavaScript template literals. In `index.html`, case notes submitted by users are directly assigned to `div.innerHTML`.
- **Evidence:**
  ```javascript
  // src/landguard_web/templates/index.html:1877-1883
  div.innerHTML = `
    <div style="display: flex; justify-content: space-between; color: #60a5fa; font-weight: 600; margin-bottom: 2px;">
      <span>${n.author}</span>
      <small style="color: var(--text-muted);">${time}</small>
    </div>
    <div style="color: #cbd5e1;">${n.note}</div>
  `;
  notesBox.appendChild(div);
  ```
- **Impact:**
  When a citizen submits a clarification note containing malicious HTML/JavaScript (`<img src=x onerror=...>`), the payload executes in the browser of any investigator or administrator viewing the case. This allows session theft, cookie exfiltration, and administrative impersonation.
- **Defensive Remediation:**
  Use safe DOM property assignments (`.textContent` or `innerText`) instead of `.innerHTML`, or implement an HTML sanitizer (e.g. DOMPurify) before injecting dynamic user-supplied strings:
  ```javascript
  const noteContent = document.createElement('div');
  noteContent.style.color = '#cbd5e1';
  noteContent.textContent = n.note; // Completely immune to XSS
  div.appendChild(noteContent);
  ```

---

### SEC-05: Unauthenticated Compute & Resource Exhaustion on OCR & Verification APIs
- **Severity:** **HIGH** (CVSS: 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H`)
- **Vulnerability Category:** Denial of Service / Uncontrolled Resource Consumption (CWE-400)
- **Location:**
  - `src/landguard_web/routers/verifications.py#L119-L145`
  - `src/landguard_web/routers/documents.py#L18-L37`
- **Description:**
  Both `POST /api/verify` (the algorithmic verification pipeline) and `POST /api/upload` (document OCR and computer vision tampering detector) are publicly accessible without authentication. If no user is logged in, they silently default to `USR-CITIZEN-001`. There is no rate limiting (e.g., token bucket or IP throttling) configured on either endpoint.
- **Evidence:**
  ```python
  # src/landguard_web/routers/documents.py:27-28
  user = get_current_user(request)
  uid = user["user_id"] if user else "USR-CITIZEN-001"
  result = service.process_document_upload(contents, filename, uploaded_by=uid)
  ```
  `process_document_upload` executes PyMuPDF rendering, Pillow conversions, Tesseract OCR, image seam anomaly detection, seal pattern matching, and signature template detection.
- **Impact:**
  An external attacker can flood `/api/upload` or `/api/verify` with automated concurrent requests, saturating CPU cores, consuming disk bandwidth, filling server storage, and preventing legitimate citizens and registrars from using the application.
- **Defensive Remediation:**
  1. Require authentication for document uploads and verification runs (`require_api_authenticated_user`).
  2. Implement an application-level rate limiter (e.g., `slowapi` or Redis-backed rate limiter) restricting anonymous or citizen requests to a reasonable threshold (e.g., 5 requests per minute).

---

### SEC-06: Unvalidated `redirect` Parameter in Authentication Flow (Open Redirect)
- **Severity:** **HIGH** (CVSS: 7.4 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N`)
- **Vulnerability Category:** Open Redirection (CWE-601)
- **Location:**
  - `src/landguard_web/routers/auth.py#L34-L48`, `L90-L95`
- **Description:**
  The login page and login API endpoint accept an arbitrary `redirect` query parameter. Upon successful credential verification, the API directly returns this parameter in `{"redirect_url": redirect}` or performs an HTTP 303 redirect without validating whether the target URL is a safe, internal relative path.
- **Evidence:**
  ```python
  # src/landguard_web/routers/auth.py:90-95
  redirect_url = redirect or (
      "/admin/dashboard" if user["role"] in ["ADMIN", "INVESTIGATOR"] else "/user/dashboard"
  )
  response = JSONResponse(
      status_code=200,
      content={"success": True, "user": user, "redirect_url": redirect_url},
  )
  ```
- **Impact:**
  An attacker can construct links such as:  
  `https://landguard.gov.bd/login?redirect=https://evil-spoofed-portal.com`  
  When a citizen or government officer authenticates, the client-side JavaScript immediately navigates them to the attacker's website, enabling credential harvesting and spear-phishing attacks.
- **Defensive Remediation:**
  Validate the redirect target against an allowlist or strictly ensure it begins with a single `/` and not `//` or a URI scheme:
  ```python
  def safe_redirect_url(url: Optional[str], default: str) -> str:
      if not url:
          return default
      clean = url.strip()
      if clean.startswith("/") and not clean.startswith("//") and "\\" not in clean:
          return clean
      return default
  ```

---

### SEC-07: Missing CSRF Defense-in-Depth on Mutating State Endpoints
- **Severity:** **MEDIUM** (CVSS: 5.4 - `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:N/I:L/A:L`)
- **Vulnerability Category:** Cross-Site Request Forgery (CSRF / CWE-352)
- **Location:**
  - Global FastAPI application stack (`src/landguard_web/routers/*.py`)
- **Description:**
  LandGuard relies exclusively on the session cookie (`landguard_session`) for authenticating API requests. While the cookie is configured with `samesite="lax"`, the application does not implement Anti-CSRF tokens, double-submit cookie patterns, or custom header validation (`X-Requested-With` or CSRF token header) on state-changing endpoints (e.g. `POST /api/complaints`, `PATCH /api/cases/{case_id}`, `DELETE /api/documents/{document_id}`).
- **Impact:**
  While modern browsers restrict cross-site POST requests under `SameSite=Lax`, certain older browser configurations, top-level navigations, or subdomain takeovers on the same parent domain can permit unauthorized state-changing operations.
- **Defensive Remediation:**
  Implement CSRF middleware (e.g., `starlette-csrf` or custom synchronizer token pattern) requiring a cryptographically secure token on all mutating HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`).

---

### SEC-08: Session Cookies Missing `Secure` Flag & Absence of Global Security Headers
- **Severity:** **MEDIUM** (CVSS: 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N`)
- **Vulnerability Category:** Security Misconfiguration (CWE-16) / Insecure Cookie
- **Location:**
  - `src/landguard_web/routers/auth.py#L95-L101`, `L130-L136`
  - `src/landguard_web/app.py`
- **Description:**
  1. The authentication session cookie (`landguard_session`) and language cookie (`landguard_lang`) are set with `httponly=True` and `samesite="lax"`, but omit `secure=True`.
  2. The application lacks standard HTTP security headers across all responses.
- **Evidence:**
  ```python
  # src/landguard_web/routers/auth.py:95-101
  response.set_cookie(
      key="landguard_session",
      value=session["session_token"],
      httponly=True,
      max_age=86400 * 7,
      samesite="lax",
      # secure=True is absent!
  )
  ```
- **Impact:**
  - Session cookies will be transmitted over plaintext HTTP connections if a user visits the domain without HTTPS, risking session hijacking via Man-in-the-Middle (MitM) attacks.
  - Without headers such as `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Strict-Transport-Security`, the application remains vulnerable to clickjacking, MIME sniffing attacks, and cross-site scripting exploitation.
- **Defensive Remediation:**
  1. Enforce `secure=True` on cookies whenever running in production.
  2. Add security header middleware in `src/landguard_web/app.py`:
  ```python
  @app.middleware("http")
  async def add_security_headers(request: Request, call_next):
      response = await call_next(request)
      response.headers["X-Frame-Options"] = "DENY"
      response.headers["X-Content-Type-Options"] = "nosniff"
      response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
      response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
      return response
  ```

---

### SEC-09: Hardcoded Secret Key Fallback & Plaintext Password Compatibility
- **Severity:** **MEDIUM** (CVSS: 5.5 - `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`)
- **Vulnerability Category:** Cryptographic Weakness (CWE-798 / CWE-256)
- **Location:**
  - `src/landguard_web/security.py#L42-L44`, `L49`
- **Description:**
  1. `SECRET_KEY` falls back to a static, publicly visible string: `"landguard-secure-dev-session-secret-key-change-in-prod-2026"`.
  2. In `verify_password()`, if the stored hash does not conform to the PBKDF2 format (`pbkdf2_sha256$...`), the system falls back to constant-time plaintext matching:
     `return hmac.compare_digest(plain_password, stored_hash)`.
- **Evidence:**
  ```python
  # src/landguard_web/security.py:42-49
  SECRET_KEY = os.getenv("SECRET_KEY", "landguard-secure-dev-session-secret-key-change-in-prod-2026")

  def verify_password(plain_password: str, stored_hash: str) -> bool:
      if not stored_hash.startswith("pbkdf2_sha256$"):
          # Legacy plaintext fallback for mock/demo compatibility
          return hmac.compare_digest(plain_password, stored_hash)
  ```
- **Impact:**
  - If deployed in production without an explicitly configured `SECRET_KEY`, session tokens or cryptographic signatures could be forged.
  - The plaintext fallback permits unhashed passwords to exist in the database, violating statutory data protection standards.
- **Defensive Remediation:**
  1. Fail fast on application startup in production if `SECRET_KEY` is not set or matches the known default.
  2. Remove the plaintext password fallback and enforce automatic password migration upon login.

---

### SEC-10: Unbounded Neural Text-To-Speech (TTS) Proxy Abuse
- **Severity:** **MEDIUM** (CVSS: 5.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L`)
- **Vulnerability Category:** Uncontrolled Resource Consumption / Third-Party Proxy Abuse
- **Location:**
  - `src/landguard_web/routers/voice.py#L52-L89`
  - `src/landguard_services/voice_service.py#L55-L76`
- **Description:**
  The endpoint `GET /api/voice/tts` takes a query parameter `text: str = Query(..., min_length=1)`. It does not require authentication, lacks rate limiting, and does not enforce a `max_length` constraint. It forwards the arbitrary text to Microsoft's neural TTS service via `edge_tts.Communicate(cleaned_text, voice)`.
- **Impact:**
  Malicious actors can send arbitrary, arbitrarily large text strings (e.g. hundreds of kilobytes of text), utilizing LandGuard as an open, free proxy for third-party neural speech synthesis, consuming server CPU, and exhausting server sockets.
- **Defensive Remediation:**
  Enforce a strict string length limit (e.g. `max_length=300`) and apply rate limiting:
  ```python
  @router.get("/api/voice/tts")
  async def voice_text_to_speech(
      request: Request,
      text: str = Query(..., min_length=1, max_length=300),
      lang: Optional[str] = Query(None),
  ): ...
  ```

---

### SEC-11: One-Click Demo Login Privilege Escalation in Non-Production Mode
- **Severity:** **LOW** (CVSS: 3.8 - `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N`)
- **Vulnerability Category:** Authentication Bypass / Debug Feature Left Active
- **Location:**
  - `src/landguard_web/routers/auth.py#L105-L138`
- **Description:**
  The application provides `POST /api/auth/demo-login?role=admin`, which creates an active administrative session with zero credential verification. While `check_production_security()` blocks this when `ENVIRONMENT == "production"`, any deployment where `ENVIRONMENT` is left unset, misspelled, or set to `staging`/`uat` exposes instant root administrator access.
- **Impact:**
  Immediate compromise of all administrative capabilities if deployed in any non-production configuration exposed to the internet.
- **Defensive Remediation:**
  Require an explicit secret bypass flag (e.g. `ENABLE_DEMO_LOGIN=true`) rather than relying on the absence of `ENVIRONMENT=production`.

---

### SEC-12: Unhandled Internal Stack Trace Leakage in Report Error Handler
- **Severity:** **LOW** (CVSS: 3.7 - `CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N`)
- **Vulnerability Category:** Information Exposure Through Environmental Variables (CWE-209)
- **Location:**
  - `src/landguard_web/routers/reports.py#L52-L57`
- **Description:**
  In `view_formatted_report()`, an unhandled exception triggers:
  ```python
  except Exception as e:
      import traceback
      tb = traceback.format_exc()
      return HTMLResponse(content=f"<pre style='color:red'>{tb}</pre>", status_code=500)
  ```
- **Impact:**
  Reveals internal filesystem paths (`F:\land gurd main project\...`), Python environment details, and execution line numbers to unauthenticated external users.
- **Defensive Remediation:**
  Return a generic 500 error page to the client and log the traceback solely to server logs.

---

### SEC-13: Orphaned File Storage on Rejection in Document Upload
- **Severity:** **LOW** (CVSS: 3.3 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L`)
- **Vulnerability Category:** Resource Leakage / Incomplete Cleanup
- **Location:**
  - `src/landguard_services/document_service.py#L51-L99`
- **Description:**
  When a file is uploaded to `POST /api/upload`, the file bytes are written to disk (`data/uploads/deeds/`) and cached as a PNG, and a record is created in SQLite *before* `validate_land_document_plausibility()` runs. If the document is subsequently determined to be a non-land record (e.g. a restaurant menu or receipt), `ValueError` is raised, but the written files are never removed from the disk.
- **Impact:**
  Attackers can flood the endpoint with invalid documents, causing steady disk space consumption that cannot be cleaned via normal application workflows.
- **Defensive Remediation:**
  Perform plausibility and integrity validation in memory, or clean up disk files within a `finally` or `except` block upon rejection.

---

## Part 4: Test Suite Security Assessment

An evaluation of the automated test suite (`tests/`) revealed significant strengths alongside key security blind spots:

### Strengths of Existing Test Suite
1. **PBKDF2 Password Hashing Verification:** `tests/test_security_authorization.py` correctly tests hashing formatting, verification, and incorrect password rejection.
2. **Anonymous Case & Complaint Access:** Asserts that unauthenticated requests to `/api/cases` and `/api/complaints` receive HTTP 401 Unauthorized.
3. **Role-Based Portal Separation:** `tests/test_auth_and_portals.py` validates that citizens attempting to view `/admin/dashboard` are redirected to `/access-denied`.
4. **Complaint IDOR Protection:** Asserts that Citizen A cannot retrieve or expedite Citizen B's complaint via `/api/complaints/{id}`.
5. **Cadastral Conflict Enforcement:** `tests/test_admin_add_parcel.py` confirms that attempting to add duplicate parcels in the same mouza/upazila returns HTTP 409 Conflict.

### Critical Gaps & Weak Assertions
1. **Untested Case Clarification IDOR:** There are zero tests checking whether Citizen A can submit clarification responses to Citizen B's case via `POST /api/cases/{case_id}/clarification/respond`.
2. **Untested Verification Dossier IDOR:** No tests check whether Citizen A can view Citizen B's verification dossier at `GET /user/verify/{verification_id}`.
3. **Untested Public Report Data Leakage:** The tests assert that `/api/reports/{id}` returns 200 OK, but never test whether anonymous users can access it or verify that citizen NIDs are masked.
4. **Untested Stored XSS:** No tests attempt to inject HTML/JavaScript strings into complaint narratives or case notes to verify output sanitization.
5. **Untested Compute Exhaustion & Rate Limiting:** No automated tests evaluate concurrent load, oversized audio strings to `/api/voice/tts`, or file upload floods.

---

## Part 5: Verification Limitations & Unverified Surface Area

In accordance with strict read-only auditing principles, the following components could not be verified through live non-mutating inspection:
1. **External Third-Party Services:** Microsoft Edge Neural TTS service reliability, latency, and upstream rate limits were not tested against heavy load.
2. **Production Reverse Proxy / TLS Termination:** Web server configurations outside the repository (such as Nginx, Cloudflare, or Caddy) could not be inspected. TLS configurations, HSTS headers, and upstream rate limiting may or may not exist at the edge.
3. **PostgreSQL Standby Database:** The Neon Serverless PostgreSQL backend was inspected via static repository code only. Live connection pools, remote role permissions, and SSL connection configurations were not tested against a live Neon instance.
4. **Physical Disk Performance Under Load:** File upload disk I/O performance under multi-gigabyte stress testing was not evaluated to avoid mutating disk state.

---

## Part 6: Remediation Roadmap & Prioritized Hardening Checklist

### Priority 1: Immediate Critical Fixes (Within 24–48 Hours)
- [ ] **Fix IDOR on Case Clarification:** Add ownership validation in `src/landguard_web/routers/cases.py` ensuring the caller is the author of the linked complaint.
- [ ] **Fix IDOR on Verification Dossier:** Enforce `rec["user_id"] == user["user_id"]` in `src/landguard_web/routers/verifications.py`.
- [ ] **Protect Report APIs & Mask Public PII:** Require authentication on `/api/reports/{id}`, `/api/reports/html/{id}`, and `/api/reports/pdf/{id}`. Ensure public verification routes serve strictly sanitized records.
- [ ] **Remediate Stored XSS in Templates:** Replace `.innerHTML = ...` with `.textContent` or implement DOMPurify in `src/landguard_web/templates/index.html` and other template scripts.

### Priority 2: Defense-in-Depth & Configuration Hardening (Within 1 Week)
- [ ] **Enforce `Secure` Cookie Flag:** Add `secure=True` to session cookies in `src/landguard_web/routers/auth.py`.
- [ ] **Implement Global Security Headers:** Inject CSP, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy middleware in `src/landguard_web/app.py`.
- [ ] **Validate Redirect URLs:** Add an open redirect sanitizer to `src/landguard_web/routers/auth.py`.
- [ ] **Add Rate Limiting:** Integrate `slowapi` on `/api/upload`, `/api/verify`, and `/api/voice/tts`.
- [ ] **Cap TTS Input Length:** Restrict the `text` parameter in `/api/voice/tts` to a maximum of 300 characters.

### Priority 3: Architecture & Operational Cleanliness (Next Release)
- [ ] **Purge Plaintext Password Fallback:** Remove legacy plaintext comparison in `src/landguard_web/security.py` and enforce PBKDF2 across all records.
- [ ] **Clean Up Rejected Uploads:** Implement immediate disk cleanup when `validate_land_document_plausibility()` rejects an uploaded file.
- [ ] **Sanitize Error Handling:** Replace raw traceback HTML returns in `src/landguard_web/routers/reports.py` with generic user error pages.
- [ ] **Expand Security Test Coverage:** Add automated regression tests for IDOR, unauthenticated report endpoints, and XSS payload resistance.
