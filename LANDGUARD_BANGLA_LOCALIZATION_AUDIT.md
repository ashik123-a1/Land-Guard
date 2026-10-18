# LANDGUARD — WEBSITE-WIDE BANGLA/ENGLISH LOCALIZATION AUDIT

**Project:** `F:\land gurd main project\`  
**Date:** October 17, 2026  
**Status:** AUDIT COMPLETED — BASELINE ESTABLISHED  
**Primary Language Files:** `src/landguard_web/localization.py`, `src/landguard_web/dependencies.py`, `src/landguard_reports/pdf_generator.py`  

---

## 1. Executive Summary

This comprehensive audit inventories every user-visible text element, template, route, dynamic component, verification result, and PDF report generation workflow in the LandGuard application.

### Key Baseline Findings:
1. **Asymmetric Localization:** While partial Bengali translations were previously introduced for portions of the Citizen Portal (`user/dashboard.html`, `user/verify.html`, `user/verify_detail.html`, `user/complaints.html`), the **entire Admin/Investigator Portal** (`admin/*.html`) and the **entire Public Surface** (`landing.html`, `login.html`) remained almost 100% hardcoded in English.
2. **Missing Language Selectors:** The language switcher pill (`EN | বাংলা`) was present only in `user/layout.html` (Citizen Portal). It was completely missing from `admin/layout.html`, `public/landing.html`, `public/login.html`, and both HTML report viewers (`verification_certificate.html` and `report_detail.html`).
3. **Report & PDF Localization Deficit:**
   - Both the HTML report certificate (`public/verification_certificate.html`) and the printable report (`admin/report_detail.html`) were hardcoded in English.
   - The binary PDF generation service (`src/landguard_reports/pdf_generator.py`) did not accept a language parameter, hardcoding English Helvetica labels.
   - Crucially, ReportLab's standard TTF rendering engine lacks HarfBuzz/OpenType complex text shaping for Bengali, causing vowels (e.g., `ি`, `ে`) to be misplaced after consonants and corrupting conjuncts (যুক্তাক্ষর).
4. **Dynamic JavaScript Text Strings:** Dynamic text generated in JavaScript (modal messages, error alerts, verification result rendering, OCR progress messages, floating voice widget) contained untranslated English strings or relied on hardcoded English fallbacks.

---

## 2. Detailed Route and Template Inventory

The table below catalogs every user-visible view in the application, its implementation path, current localization status, and specific gaps identified:

| Route / Surface | Template / Component File | Current Status | Identified Gaps & Required Actions |
| :--- | :--- | :--- | :--- |
| **GET /** | `templates/public/landing.html` | **Untranslated** (95% English) | Hero title, subtitle, CTA buttons, 4 metrics cards, 3-step process cards, 3 feature cards, and hackathon disclaimer are hardcoded English. Language switcher pill is missing. |
| **GET /login** | `templates/public/login.html` | **Untranslated** (98% English) | Form labels ("Email Address", "Password", "Remember session"), submit button, 3 quick demo role cards, error alert, and back links are hardcoded English. Language switcher pill missing. |
| **GET /access-denied** | `templates/public/access_denied.html` | **Untranslated** (100% English) | "Access Restricted", "Security Clearance Insufficient", return button hardcoded in English. |
| **GET /not-found** | `templates/public/not_found.html` | **Untranslated** (100% English) | "Record Not Found", "404 Dossier Not Found", search guidance hardcoded in English. |
| **GET /user/dashboard** | `templates/user/dashboard.html` | **Partially Translated** (80% Bengali) | Header & KPIs use `_()`, but Digital Identity Card (Upazila, Valid Thru, demo footer) and empty states contain hardcoded English. |
| **GET /user/verify** | `templates/user/verify.html` | **Partially Translated** (75% Bengali) | Static form labels use `_()`, but dynamic JS result renderer (`renderVerificationResults`), OCR progress steps, error toasts, and field validation messages have untranslated fallbacks. |
| **GET /user/verify/{id}** | `templates/user/verify_detail.html` | **Mostly Translated** (85% Bengali) | Status banner and rule cards use `_()`, but timestamp formatting, breadcrumb details, and action button titles require full coverage. |
| **GET /user/history** | `templates/user/history.html` | **Mostly Translated** (85% Bengali) | Filter tabs, table headers, and status badges use `_()`, but empty states and pagination labels need Bengali translations. |
| **GET /user/parcels** | `templates/user/parcels.html` | **Partially Translated** (70% Bengali) | Search bar and parcel cards have some `_()`, but land classification filters, JL numbers, and table headers need translation. |
| **GET /user/parcels/{id}** | `templates/user/parcel_detail.html` | **Partially Translated** (70% Bengali) | Cadastral graph nodes, mutation timeline, and what-if simulator controls contain untranslated English labels. |
| **GET /user/complaints** | `templates/user/complaints.html` | **Mostly Translated** (85% Bengali) | Header and status filter use `_()`, but table actions, empty state, and category labels need verification. |
| **GET /user/complaints/new** | `templates/user/complaint_new.html` | **Mostly Translated** (90% Bengali) | Category select, form inputs use `_()`; submission error messages and dynamic confirm dialog require Bengali. |
| **GET /user/complaints/{id}** | `templates/user/complaint_detail.html` | **Partially Translated** (75% Bengali) | Investigation timeline, clarification response form, and expedited status cards have untranslated text. |
| **GET /user/notifications** | `templates/user/notifications.html` | **Mostly Translated** (85% Bengali) | Filter tabs and notification titles use `_()`; audio settings label and "Mark all read" need translation. |
| **GET /user/profile** | `templates/user/profile.html` | **Partially Translated** (70% Bengali) | Digital ID particulars, NID verification status, and biometric indicator need Bengali dictionary keys. |
| **GET /user/settings** | `templates/user/settings.html` | **Mostly Translated** (85% Bengali) | Language preference radios, sound notification switches use `_()`; submit feedback needs translation. |
| **GET /user/voice** | `templates/user/voice.html` | **Mostly Translated** (90% Bengali) | Bilingual assistant already supports English and Bengali; command prompts and fallback notices need full catalog check. |
| **GET /admin/dashboard** | `templates/admin/dashboard.html` | **Untranslated** (98% English) | All 5 Bento KPI cards, Chart.js legends/tooltips, trend sparklines, table headers, quick search, and SLA metrics are in English. |
| **GET /admin/verifications** | `templates/admin/verifications.html` | **Untranslated** (95% English) | Table columns, queue status badges, filter buttons, and action buttons hardcoded English. |
| **GET /admin/verifications/{id}** | `templates/admin/verification_detail.html` | **Untranslated** (90% English) | Adjudication workspace, official registrar decision radio buttons, rule inspection tabs, CV signals in English. |
| **GET /admin/cases** | `templates/admin/cases.html` | **Untranslated** (95% English) | Case docket table, priority filters, investigator assignments, and status badges in English. |
| **GET /admin/cases/{id}** | `templates/admin/case_detail.html` | **Untranslated** (90% English) | Case timeline, case notes submission, SLA countdown, clarification request modal, re-assignment dropdowns in English. |
| **GET /admin/parcels** | `templates/admin/parcels.html` | **Untranslated** (95% English) | Registry management table, area filters, parcel status badges in English. |
| **GET /admin/reports** | `templates/admin/reports.html` | **Untranslated** (95% English) | Evidence dossiers list, SHA-256 certificate hashes, view/print buttons in English. |
| **GET /admin/analytics** | `templates/admin/analytics.html` | **Untranslated** (95% English) | Chart titles, axis labels, operational velocity metrics, export buttons in English. |
| **GET /admin/models** | `templates/admin/models.html` | **Untranslated** (95% English) | XGBoost feature importance table, SHAP values, confusion matrix, ROC-AUC labels in English. |
| **GET /admin/audit** | `templates/admin/audit.html` | **Untranslated** (95% English) | Immutable audit log table, event type filters, actor IDs, cryptographic hashes in English. |
| **GET /admin/users** | `templates/admin/users.html` | **Untranslated** (95% English) | Staff directory, role management, permission badges in English. |
| **GET /admin/settings** | `templates/admin/settings.html` | **Untranslated** (95% English) | SLA thresholds, rule weights, email notification toggles in English. |
| **GET /admin/system** | `templates/admin/system.html` | **Untranslated** (95% English) | System health KPIs, database pool status, uptime, disk usage in English. |
| **GET /reports/{id}** | `templates/public/verification_certificate.html` | **Untranslated** (98% English) | Public statutory verification report: title, statutory verdict, deed specs, rule findings, QR label, and synthetic disclaimer are all English. |
| **GET /verify/print/{id}** | `templates/admin/report_detail.html` | **Untranslated** (98% English) | Printable verification report paper sheet: header, certificate metadata, deed specs, statutory rules, SHA-256 block, signature line are all English. |
| **GET /reports/{id}/pdf** | `src/landguard_reports/pdf_generator.py` | **Untranslated** (100% English) | ReportLab generator produces exclusively English PDFs with Helvetica font. No `lang` argument supported. Fails Bengali conjunct shaping. |

---

## 3. Localization Infrastructure Audit

### 3.1 Language Resolution & Precedence
`src/landguard_web/localization.py` defines `get_preferred_language()`:
1. `request.query_params.get("lang")` (Explicit URL override: `?lang=bn` or `?lang=en`)
2. `request.cookies.get("landguard_lang")` (Persistent cookie with 1-year max age)
3. `user.get("preferred_language")` (Database profile preference from SQLite)
4. Fallback to `"en"`.

`app.py` features an HTTP middleware that reads `?lang=` from the query string and automatically writes the `landguard_lang` cookie.

### 3.2 Jinja2 Integration
`src/landguard_web/dependencies.py` wraps `templates.TemplateResponse` and registers:
- Global `_` and `t` functions pointing to `_jinja_translate`.
- Filter `_` and `t` for pipe syntax (`{{ "Clear Titles"|t }}`).
- Automatically injects `current_lang` into every template context.

### 3.3 Translation Catalogue (`src/landguard_web/localization.py`)
- Currently contains 841 lines with ~350 translation keys.
- **Identified Gap:** The dictionary is heavily slanted toward Citizen Portal terms. It lacks entries for Admin/Investigator operations, Bento dashboard KPIs, analytics charts, public landing sections, and complete report certificate text.

### 3.4 Bengali Typography & Complex Script PDF Shaping
- **HTML/Browser:** `base.html` only loads `Inter`, `JetBrains Mono`, and `Orbitron` from Google Fonts. Need to add `Noto Sans Bengali` and `Hind Siliguri` to ensure standard Bengali glyph rendering across all operating systems.
- **PDF Generation:** Standard ReportLab TTFont does not support OpenType GSUB/GPOS tables (HarfBuzz). Rendering Bengali text directly through ReportLab causes detached/misplaced vowels and unformed conjuncts. A headless Chromium / Chrome printing pipeline (`--headless=new --print-to-pdf`) provides 100% authentic Bengali glyph shaping, ligature formation, and font embedding.

---

## 4. Remediation Action Plan

1. **Phase 2:** Extend `src/landguard_web/localization.py` with complete translations for all admin, public, report, and rule terms. Add `Noto Sans Bengali` to `base.html` and define `.font-bangla`. Add accessible language switcher to `admin/layout.html`, `landing.html`, `login.html`, and report views.
2. **Phase 3:** Localize `public/landing.html`, `public/login.html`, `public/access_denied.html`, and `public/not_found.html`.
3. **Phase 4:** Close remaining Citizen Portal translation gaps (`user/dashboard.html`, `user/verify.html`, `user/verify_detail.html`, `user/parcels.html`, `user/complaints.html`).
4. **Phase 5:** Localize all Admin and Investigator views (`admin/layout.html`, `admin/dashboard.html`, `admin/cases.html`, `admin/case_detail.html`, `admin/verifications.html`, `admin/verification_detail.html`, `admin/reports.html`, `admin/analytics.html`, `admin/models.html`, `admin/audit.html`, `admin/users.html`, `admin/settings.html`, `admin/system.html`, `components/ui_components.html`).
5. **Phase 6:** Ensure verification results, rule names, severity badges, risk indicators, and computer vision findings display perfectly in both English and Bengali without altering data integrity.
6. **Phase 7:** Localize `public/verification_certificate.html` and `admin/report_detail.html`. Upgrade `src/landguard_reports/pdf_generator.py` and `src/landguard_web/routers/reports.py` to support `lang="bn"`, rendering authentic Bengali PDFs with perfect conjunct shaping and font embedding.
7. **Phase 9:** Run comprehensive unit and E2E verification suites covering catalogue resolution, role views, bilingual report rendering, and PDF inspection.
