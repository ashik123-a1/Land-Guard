# LandGuard — Duplicate Complaint Analysis Fix & Bangla UI Localization Report

**Date**: October 15, 2026  
**Environment**: `F:\land gurd main project`  
**Operational Database**: SQLite (`data/landguard_operational.db`) in WAL Mode (374 complaints preserved, zero deleted)  
**Test Suite Baseline**: 171 tests passed across 32 test suites (100% pass rate in ~30.60s)  

---

## 1. Executive Summary

This pass resolves the two targeted user-reported issues in the LandGuard Citizen Portal:
1. **Unbounded Duplicate Grievance Display (Part A)**: Plots with repeated or concurrent test filings (e.g. plot 9044 with 322 entries) rendered unmanageably long lists that exposed private citizen identities.
2. **Non-Functional Language Switching (Part B)**: The language selector in Citizen Portal Settings (`/user/settings`) was purely visual and failed to translate portal interfaces or persist preferences.

Both issues have been resolved end-to-end within the modular FastAPI + Jinja2 + SQLite architecture, with strict preservation of existing domain services, Edge TTS female voices (`bn-BD-NabanitaNeural` / `en-US-AriaNeural`), and operational data.

---

## 2. Part A — Duplicate Complaint Analysis & Display Fix

### 2.1 Root Cause Diagnosis
1. **Naive Single-Field Matching**:
   The previous `detect_duplicate_complaints()` implementation in [`src/landguard_ai/complaint_analyzer.py`](file:///F:/land%20gurd%20main%20project/src/landguard_ai/complaint_analyzer.py) unconditionally flagged any complaint as a duplicate if `norm_plot == c_plot`.
2. **Test Artifact Accumulation**:
   Concurrency and stress tests ([`tests/test_performance_and_concurrency.py`](file:///F:/land%20gurd%20main%20project/tests/test_performance_and_concurrency.py)) had legitimately populated 322 test records against plot 9044 in `data/landguard_operational.db`.
3. **Presentation & Privacy Defect**:
   [`src/landguard_web/templates/user/complaint_detail.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/complaint_detail.html) rendered every match as an unpaginated bullet point and exposed `Citizen: ${d.citizen_name}`, violating citizen confidentiality.

### 2.2 Multi-Signal Matching Architecture
[`detect_duplicate_complaints`](file:///F:/land%20gurd%20main%20project/src/landguard_ai/complaint_analyzer.py) now evaluates multi-signal criteria:
- **`LIKELY_DUPLICATE`**:
  - Exact deed number match (`norm_deed == c_deed` where deed is non-N/A), OR
  - Same complainant filing on the same parcel with category or lexical overlap ($\ge 0.30$), OR
  - Same parcel + identical category + high narrative Jaccard overlap ($\ge 0.50$).
- **`POSSIBLY_RELATED`**:
  - Same parcel + same category (distinct complainants), OR
  - Same parcel with moderate text overlap ($\ge 0.25$).
- **`SAME_PARCEL_DIFFERENT_CLAIM`**:
  - Same parcel alone with distinct categories and low narrative overlap.
  - **Rule**: *Identical Dag plot alone NEVER classifies as `LIKELY_DUPLICATE`.*
- **Self-Exclusion**:
  - The complaint being analyzed (`cid == current_complaint_id`) is strictly excluded.

### 2.3 Strict Citizen Privacy Protection
- **Citizen Viewer (`is_staff=False`)**:
  - If candidate was filed by the active user: Complainant displays `"Your Previous Filing"`.
  - If candidate was filed by another citizen: Complainant displays `"Independent Citizen Filing"`.
  - Narrative previews, phone numbers, and NIDs of third parties are scrubbed (`narrative_preview = None`).
  - Unrelated deed numbers are masked as `"CONFIDENTIAL"`.
- **Investigator / Admin Viewer (`is_staff=True`)**:
  - Full citizen name and truncated narrative preview are rendered for official case corroboration.

### 2.4 Compact UI & Expandable View
In [`user/complaint_detail.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/complaint_detail.html):
- **KPI Summary Header**: Shows counts for `Likely Duplicates`, `Related On Plot`, and `Different Claims`.
- **Top 5 Display**: At most 5 prioritized matches are shown initially with colored relationship badges.
- **Collapsible Accordion**: Remaining filings are placed in `<details class="mt-2">` with max height and scrollbar (`"View all N remaining related filings on this parcel"`).
- **Zero-State**: If 0 matches, renders a clean checkmark banner.
- **Refresh Control**: Quick-refresh button re-fetches analysis without reloading the whole page.

---

## 3. Part B — Functional Bangla UI Localization

### 3.1 Centralized Localization Engine
Created [`src/landguard_web/localization.py`](file:///F:/land%20gurd%20main%20project/src/landguard_web/localization.py):
- **Translation Dictionary**: Complete coverage for navigation, buttons, forms, status badges, and headings in English (`en`) and Bengali (`bn`).
- **Safe Fallback**: [`get_text(key, lang)`](file:///F:/land%20gurd%20main%20project/src/landguard_web/localization.py) checks the target language, falls back cleanly to English, and defaults to the key string if unregistered. Never renders empty strings or error tokens.

### 3.2 Resolution Precedence & Middleware
In [`src/landguard_web/localization.py`](file:///F:/land%20gurd%20main%20project/src/landguard_web/localization.py) and [`src/landguard_web/app.py`](file:///F:/land%20gurd%20main%20project/src/landguard_web/app.py):
1. **Query Parameter**: `?lang=bn` or `?lang=en` (takes top precedence and sets cookie).
2. **HTTP Cookie**: `landguard_lang` (1-year persistent cookie with `SameSite=Lax`).
3. **Database Profile**: `preferred_language` in SQLite `users` table for authenticated users.
4. **Default**: `'en'` (safe fallback).

### 3.3 Database Persistence & Settings API
- **SQLite Schema Migration**: Added column `preferred_language VARCHAR(10) DEFAULT 'en'` to table `users` in [`src/landguard_data/database.py`](file:///F:/land%20gurd%20main%20project/src/landguard_data/database.py) and verified existing data.
- **Repository & Service**:
  - Added [`UserRepository.update_user_preference()`](file:///F:/land%20gurd%20main%20project/src/landguard_data/repositories/users.py).
  - Added [`AuthService.update_user_preference()`](file:///F:/land%20gurd%20main%20project/src/landguard_services/auth_service.py) with session cache synchronization.
  - Exposed [`POST /api/user/preferences`](file:///F:/land%20gurd%20main%20project/src/landguard_web/routers/citizen.py) to save user preferences and set the response cookie.
- **Settings View**:
  [`src/landguard_web/templates/user/settings.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/settings.html) radio buttons dynamically check active language and trigger live persistence + immediate page reload upon selection.

### 3.4 Reusable Jinja2 Helper & Auto-Injection
In [`src/landguard_web/dependencies.py`](file:///F:/land%20gurd%20main%20project/src/landguard_web/dependencies.py):
- Registered Jinja globals and filters `{{ _('key') }}` and `{{ t('key') }}`.
- Wrapped `templates.TemplateResponse` to automatically inject `current_lang` into every rendered template context.
- Topbar language quick-toggle pill `[EN | বাংলা]` added to [`user/layout.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/layout.html) with active highlighting.
- Localized core citizen templates:
  - [`user/layout.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/layout.html) (sidebar nav, user greetings, header pill)
  - [`user/dashboard.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/dashboard.html) (identity card, KPIs, quick search, recent items)
  - [`user/complaints.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/complaints.html) (filters, headers, empty state)
  - [`user/complaint_detail.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/complaint_detail.html) (AI analysis card, duplicate summary)
  - [`user/history.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/history.html) (table headers, dossier actions)
  - [`user/parcels.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/parcels.html) (search bar, filter buttons)
  - [`user/verify.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/verify.html) (stepper headers)
  - [`user/settings.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/user/settings.html) (preference forms and active radio inputs)
  - [`base.html`](file:///F:/land%20gurd%20main%20project/src/landguard_web/templates/base.html) (`<html lang="{{ current_lang }}">`)

---

## 4. Verification and Automated Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: F:\land gurd main project
collected 171 items

32 test suites passed:
- tests/test_complaint_ai_analysis.py: 6 passed (multi-signal duplicate detection & privacy)
- tests/test_localization.py: 4 passed (get_text, precedence, SQLite persistence, Bangla UI)
- tests/test_voice_assistant.py: 15 passed (bilingual voice, female TTS Aria/Nabanita)
- tests/test_verification_dossier_detail.py: 14 passed
- tests/test_web_app.py: 14 passed
- tests/test_cadastral_graph_and_simulator.py: 6 passed
- tests/test_security_authorization.py: 7 passed
- tests/test_sqlite_persistence.py: 4 passed
- tests/test_sqlite_primary.py: 5 passed
- ... (all 32 suites)

============================ 171 passed in 30.60s =============================
```

### Git Status & Integrity
- No Git commits or branch resets were performed.
- `git diff --check` passed cleanly with zero whitespace or conflict warnings.
- Operational database `data/landguard_operational.db` retains all 374 complaint records intact.
