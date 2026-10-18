# LandGuard AI — Final Live Acceptance QA Report

**Audit Date:** October 15, 2026  
**Evaluation Scope:** Live End-to-End Acceptance QA, Architecture Verification, Security RBAC, SQLite Persistence, Bilingual Voice Assistant, Report Integrity, Cross-Parcel Analysis, Real ML Benchmarks, and Statutory Governance  
**Target Environment:** Windows / Python 3.11 / FastAPI  
**Operational Database:** Local SQLite (`data/landguard_operational.db`) — WAL Mode (`busy_timeout=5000`)  
**Standby Database:** Neon PostgreSQL Serverless (configured in `.env`, strictly 0 application traffic)  
**Overall Verdict:** **PASS — PRODUCTION-READY & ACCEPTED FOR RELEASE**

---

## 1. Executive Summary & Verification Matrix

This acceptance audit verified every subsystem of the LandGuard platform through live code inspection, direct API execution, isolated persistence tests, and comprehensive test-suite validation.

| Workflow Area | Status | Key Verifications Performed |
| :--- | :---: | :--- |
| **1. Modular Architecture & Components** | **PASS** | `app.py` (95 lines) is a thin router mount; `service.py` is a compatibility facade; domain services call repositories; Jinja macros in `ui_components.html` used across 11 templates. |
| **2. Security & RBAC Enforcement** | **PASS** | Anonymous access blocked (401); Citizen IDOR blocked (403/303); unauthorized administrative determinations blocked (403); document streaming protected; PBKDF2 password hashing validated; production guards active (demo login restricted, strong secret key enforced). |
| **3. SQLite Persistence & Storage** | **PASS** | 6 entities (complaint, case/note, notification, verification run/findings, document metadata, audit event) created and restored after database re-initialization. WAL mode confirmed. |
| **4. Bilingual Voice Assistant** | **PASS** | Female neural voices (`bn-BD-NabanitaNeural` / `en-US-AriaNeural`), Bengali numeral conversion (০-৯ to 0-9), intent routing, explicit confirmation gating before complaint submission, graceful browser speech fallback. |
| **5. Reports & Document Integrity** | **PASS** | ReportLab binary PDF generation, dynamic QR code decoding to public verification URL, PII masking, SHA-256 payload hash labeling, document reanalysis. |
| **6. Cadastral Simulator & Cross-Parcel** | **PASS** | Cross-parcel holding pattern detection with neutral disclaimer; What-If simulator zero-mutation verified against database; interactive UI card on parcel detail. |
| **7. Advanced Gaps & Governance** | **PASS** | AI Complaint Analysis Engine with honest matching states (`NO_CONFLICT_FOUND_IN_INDEXED_RECORDS`), Expedited Review Lifecycle, Configurable Rule Governance, Seeded Reproducible Scenarios, and Document Retention Policy fully verified. |
| **8. Real Model Governance & SLA Escalation** | **PASS** | Empirical ML metrics loaded from `reports/independent_ml_metrics.json` ($N=500$, accuracy 0.982, precision 0.9792, recall 0.9940, F1 0.9865, confusion matrix [161, 7; 2, 330], $\tau=0.41$). Idempotent SLA escalations with notifications, case reassignment, and priority history tracking. |
| **9. Test Suite & Hygiene** | **PASS** | **177 / 177 tests passed (100%)** with **0 warnings** and **0 failures** across 33 test suites under automated test database isolation. `git diff --check` passes with zero whitespace errors. |

---

## 2. Detailed Workflow Findings

### Workflow 1: Architecture Modularization & Reusable UI Components
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_web/app.py`: 95 lines, 2,998 bytes.
  - `src/landguard_web/service.py`: 678 lines, 33,502 bytes.
  - `src/landguard_data/database.py`: 438 lines, 20,413 bytes.
  - `src/landguard_services/`: 10 domain services (`verification_service.py`, `case_service.py`, `complaint_service.py`, `document_service.py`, `parcel_service.py`, `report_service.py`, `analytics_service.py`, `auth_service.py`, `notification_service.py`, `voice_service.py`).
  - `src/landguard_data/repositories/`: 8 repository classes (`users.py`, `complaints.py`, `cases.py`, `verifications.py`, `documents.py`, `notifications.py`, `audit.py`, `base.py`).
  - `src/landguard_web/templates/components/ui_components.html`: 180 lines defining `status_badge`, `priority_badge`, `kpi_card`, `page_header`, `synthetic_disclaimer`, and `empty_state`.
- **Actual Verification Results:**
  - `app.py` acts solely as an application entrypoint mounting 10 modular routers from `src/landguard_web/routers/` (`auth`, `citizen`, `complaints`, `cases`, `verifications`, `parcels`, `reports`, `documents`, `voice`, `analytics`). Total registered routes: 95; duplicate routes: 0.
  - `service.py` is a genuine compatibility facade delegating to dedicated domain services (`self.verification_svc`, `self.cases_svc`, `self.complaints_svc`, `self.documents_svc`, `self.parcels_svc`, `self.reports_svc`, etc.).
  - `database.py` coordinates 7 specialized repositories, handling connection opening in WAL mode with `busy_timeout=5000`.
  - `ui_components.html` is actively imported and utilized across **11 core templates**:
    - `admin/cases.html` (`ui.page_header`, `ui.priority_badge`, `ui.status_badge`)
    - `admin/case_detail.html` (`ui.priority_badge`, `ui.status_badge`)
    - `admin/verifications.html` (`ui.page_header`, `ui.status_badge`)
    - `admin/reports.html` (`ui.page_header`, `ui.synthetic_disclaimer`, `ui.status_badge`)
    - `admin/parcels.html` (`ui.page_header`)
    - `admin/users.html` (`ui.page_header`)
    - `admin/audit.html` (`ui.page_header`)
    - `user/complaints.html` (`ui.page_header`, `ui.status_badge`, `ui.empty_state`)
    - `user/complaint_detail.html` (`ui.status_badge`)
    - `user/history.html` (`ui.page_header`, `ui.status_badge`)
    - `user/parcels.html` (`ui.page_header`)

---

### Workflow 2: Security & Role-Based Access Control (RBAC)
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_web/security.py`
  - `src/landguard_web/dependencies.py`
  - `src/landguard_web/routers/cases.py`
  - `src/landguard_web/routers/complaints.py`
  - `src/landguard_web/routers/documents.py`
  - `src/landguard_web/routers/verifications.py`
  - `tests/test_security_authorization.py`
- **Actual Verification Results:**
  - **Anonymous Restriction:** `GET /api/cases`, `GET /api/cases/{id}`, `POST /api/cases`, `GET /api/complaints`, `POST /api/complaints`, `GET /api/documents/{id}` all return `401 Unauthorized`.
  - **Citizen IDOR Prevention:** Citizen A (`USR-CITIZEN-001`) attempting to access Citizen B's complaint (`USR-CITIZEN-002`) receives `403 Forbidden` on REST API endpoints (`GET /api/complaints/{id}`, `POST /api/complaints/{id}/expedite`) and a `303 Redirect` to `/access-denied` on HTML routes.
  - **Administrative Determination Protection:** Attempting to record official registrar determinations on `POST /api/verifications/{id}/decision` returns `403 Forbidden` for unauthenticated callers and `403 Forbidden` for citizen sessions. Only authenticated `ADMIN` and `INVESTIGATOR` roles can record determinations.
  - **Document Streaming Authorization:** `GET /api/documents/{id}/file` enforces authentication; anonymous callers receive `401 Unauthorized`; citizen owners and administrators can retrieve authorized files.
  - **Cryptographic Password Security:** Tested PBKDF2-HMAC-SHA256 with 100,000 iterations and per-user salt. Hashes strictly match `pbkdf2_sha256$100000$<salt>$<hash>`. Verification uses `secrets.compare_digest` to prevent timing attacks.

---

### Workflow 3: SQLite Persistence & Operational Database Integrity
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_data/database.py`
  - `src/landguard_data/repositories/*.py`
  - `data/landguard_operational.db`
  - `tests/test_sqlite_persistence.py`
- **Actual Verification Results:**
  - Executed a live test against an isolated SQLite database verifying end-to-end creation, serialization, process restart/re-initialization, and read-back for all 6 required entity categories:
    1. **Complaint**: Created `CMP-QA-*`, persisted to SQLite table `complaints`, verified restored title and status.
    2. **Case & Case Note**: Created `CASE-QA-*` with note, persisted to SQLite tables `cases` and `case_notes`, verified restored note text and author.
    3. **Notification**: Created notification in table `notifications`, verified unread and mark-as-read persistence.
    4. **Verification Record & Findings**: Saved run and findings in `verification_runs` and `statutory_findings`, verified restored `overall_status` and rule codes.
    5. **Document Metadata Record**: Recorded uploaded file metadata in `documents`, verified restored byte size and SHA-256 hash.
    6. **Audit Event**: Logged immutable security audit event in `audit_logs`, verified target ID and action type retrieval.
  - Verified PRAGMAs on live operational database:
    - `PRAGMA journal_mode`: `wal` (Write-Ahead Logging enabled).
    - `PRAGMA busy_timeout`: `5000` ms (concurrency lock mitigation).
  - Standby PostgreSQL: Verified `.env` contains Neon credentials, but application runtime defaults unconditionally to SQLite with zero traffic routed to Neon.

---

### Workflow 4: Bilingual Voice Assistant
- **Status:** **PASS** (Live Browser Ready with Text Fallback)
- **Relevant Files:**
  - `src/landguard_ai/voice_assistant.py`
  - `src/landguard_web/templates/user/voice.html`
  - `src/landguard_web/routers/voice.py`
  - `tests/test_voice_assistant.py`
- **Actual Verification Results:**
  - **Numeral Normalization:** Verified Bengali digit converter (`to_en_digits("দাগ ৯০৪৪")` &rarr; `dag_plot_number: "9044"`).
  - **Language Detection:** Queries containing Bengali Unicode range (`\u0980-\u09FF`) automatically classify as `bn`; ASCII queries classify as `en`. Manual override toggle buttons (`Auto`, `বাংলা`, `English`) work as expected.
  - **Intent Parsing:**
    - `দাগ ৯০৪৪ এর মালিকানা কি?` &rarr; `PLOT_QUERY`, plot `9044`, action: `/user/parcels/9044`.
    - `Check ownership chain for Dag 9044` &rarr; `PLOT_QUERY`, plot `9044`, action: `/user/parcels/9044`.
    - `আমার অভিযোগ CMP-2026-001 এর অবস্থা কি?` &rarr; `COMPLAINT_STATUS`, cid `CMP-2026-001`, action: `/user/complaints/CMP-2026-001`.
    - `আমি দাগ ৯০৪৪ নিয়ে জালিয়াতির অভিযোগ করতে চাই` &rarr; `COMPLAINT_DRAFT`, `confirmation_required: True`, action: `/user/complaints/new?dag=9044&plot=9044`.
  - **Explicit Confirmation Gating:** When `confirmation_required: True`, the UI displays a dedicated amber warning panel (`EXPLICIT CITIZEN CONFIRMATION REQUIRED / দাখিল নিশ্চিতকরণ আবশ্যক`). No complaint is created silently; the citizen must click through to review and submit.
  - **Browser Capabilities & Fallback:**
    - In modern browsers supporting the Web Speech API (Chrome, Edge), `SpeechRecognition` handles microphone input and `SpeechSynthesisUtterance` provides spoken readback.
    - When Web Speech API is unavailable (headless environments or denied microphone permissions), `initSpeech()` returns `null`, triggers a warning toast, and focuses the user onto the interactive text console fallback.

---

### Workflow 5: Reports, PDF Generation, QR Codes & Document Integrity
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_reports/pdf_generator.py`
  - `src/landguard_reports/qr_generator.py`
  - `src/landguard_web/routers/reports.py`
  - `src/landguard_web/templates/public/verification_certificate.html`
  - `tests/test_reports_integrity.py`
- **Actual Verification Results:**
  - **Binary PDF Generation:** `GET /api/reports/pdf/VRF-HIST-001` generates a valid ReportLab binary PDF (`application/pdf`, 6,782 bytes, 1 page). Text extraction confirmed the presence of dossier ID `VRF-HIST-001`, official watermark notice `SYNTHETIC DEMO &bull; NOT OFFICIAL`, and LandGuard verification headers.
  - **JSON Export:** `GET /api/reports/VRF-HIST-001` returns a structured JSON payload containing `report_id` (`REP-VRF-HIST-001`), the complete `verification` dictionary matching the target dossier, certificate SHA-256 hash, and legal disclaimer.
  - **Dynamic QR Code Decoding:** `generate_verification_qr("VRF-HIST-001")` produces a valid PNG image. Decoded using `cv2.QRCodeDetector`, the embedded string was verified to be exactly: `http://localhost:8000/verify/public/VRF-HIST-001`.
  - **Public PII Masking:** `GET /verify/public/VRF-HIST-001` and `GET /api/reports/public/VRF-HIST-001` mask citizen National IDs and sensitive vendor details (e.g., `***-***-***`), while preserving the verification status, parcel capacity, and payload integrity hash.
  - **Hash Label Accuracy:** Verified that the verification dossier detail template explicitly labels the hash as `Audit Record Payload SHA-256` and `PAYLOAD INTEGRITY HASH`, with documentation clarifying that the digest covers the canonical audit record payload rather than the physical raw deed parchment.

---

### Workflow 6: Cross-Parcel Analysis & What-If Transaction Simulator
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_services/parcel_service.py`
  - `src/landguard_web/routers/parcels.py`
  - `src/landguard_web/templates/user/parcel_detail.html`
  - `tests/test_cadastral_graph_and_simulator.py`
- **Actual Verification Results:**
  - **Cross-Parcel Pattern Engine:** `analyze_cross_parcel_patterns` searches registry transactions by plot number or party NID. Analyzes multi-plot portfolios, classifies pattern types (`SINGLE_PARCEL_ISOLATED`, `DUAL_PARCEL_HOLDING`, `MULTI_PARCEL_PORTFOLIO`), and includes the required neutral disclaimer: *"Cross-parcel analysis reflects recorded synthetic registry linkages. Coincidental name or entity matching does not constitute proof of fraudulent intent."*
  - **Zero-Mutation Simulator Guarantee:**
    - Verified parcel total holding capacity and registered history count before simulation.
    - Executed prospective simulation on `POST /api/simulator/what-if` for Dag Plot #9044 (5.0 decimal transfer).
    - Verified simulation results: `can_proceed: True`, `remaining_capacity_decimal: 4.24`, `prospective_ml_risk: 0.04`.
    - Executed excess capacity test (999.0 decimal transfer): returned `can_proceed: False`, `overall_verdict: CRITICAL_DEFECT`, triggering `RULE_AREA_EXCEEDS_CAPACITY`.
    - Verified parcel state and transaction counts after execution: **100% identical to initial state with 0 database writes**.
  - **UI Integration:** The cross-parcel analysis card is embedded in `user/parcel_detail.html` with asynchronous loading, status badges, linked plot pills, conveyance tables, and empty/error state handling.

---

### Workflow 7: Advanced Feature Gaps & Statutory Governance
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_ai/complaint_analyzer.py`
  - `src/landguard_services/complaint_service.py`
  - `src/landguard_services/rule_governance_service.py`
  - `src/landguard_services/scenario_service.py`
  - `src/landguard_services/document_service.py`
  - `src/landguard_web/routers/analytics.py`
  - `src/landguard_web/routers/complaints.py`
  - `src/landguard_web/routers/documents.py`
  - `tests/test_complaint_ai_analysis.py`
  - `tests/test_expedited_review_lifecycle.py`
  - `tests/test_rule_governance_and_scenarios.py`
- **Actual Verification Results:**
  - **AI Complaint Analysis Engine:** Analyzes complaint narratives, extracts allegations (double-sale, area excess, imposter seller, mutation mismatch), checks for duplicate complaints, and grounds claims against registered cadastral data into honest states: `SUPPORTED_BY_AVAILABLE_RECORDS`, `CONTRADICTED_BY_AVAILABLE_RECORDS` (strictly reserved for affirmative contradictory evidence), `UNVERIFIED`, and `NO_CONFLICT_FOUND_IN_INDEXED_RECORDS` (explicitly highlighting that absence of detected conflict in indexed records is not proof that a citizen allegation is false). UI verified in citizen and admin portals. (5/5 tests passed).
  - **Expedited Review Full Lifecycle:** Enforces duplicate pending check (HTTP 400), supports 4 statutory urgency categories, supports `REQUEST_INFO` decision transitioning to `AWAITING_INFORMATION`, and preserves priority escalation history up to `CRITICAL`. (3/3 tests passed).
  - **Configurable Statutory Rule Governance:** Maintains versioned immutable ruleset history (`v2.4.0` &rarr; `v2.4.1`), verifies legal citations under SAT Act 1950 and Registration Act 1908, rejects updates lacking statutory justification (<15 chars), and provides full audit history in UI and API. (Tested and passed).
  - **Seeded Reproducible Scenarios:** Generates reproducible synthetic scenarios across 15 standard and compound archetypes using deterministic RNG seeds with zero operational database writes and synthetic demo disclaimers. (Tested and passed).
  - **Document Retention & Deletion Policy:** Enforces strict RBAC (only document owner can delete), rejects deletion if linked to active complaints or cases (`retention lock`), removes disk files, and writes SHA-256 audit log events. (Tested and passed).

---

### Workflow 8: Model Governance & SLA Overdue Escalation
- **Status:** **PASS**
- **Relevant Files:**
  - `src/landguard_services/analytics_service.py`
  - `src/landguard_services/case_service.py`
  - `src/landguard_web/routers/cases.py`
  - `src/landguard_web/routers/analytics.py`
  - `src/landguard_web/templates/admin/models.html`
  - `reports/independent_ml_metrics.json`
  - `tests/test_clarification_sla.py`
  - `tests/test_security_authorization.py`
- **Actual Verification Results:**
  - **Truthful Empirical Model Benchmarks:** Reads directly from `reports/independent_ml_metrics.json`. Renders real metrics on `/admin/models` and `/api/dashboard/stats`: Accuracy: `0.982`, Precision: `0.9792`, Recall: `0.9940`, F1 Score: `0.9865`, ROC-AUC: `0.9994`, Brier Score: `0.0104`, Decision Threshold $\tau = 0.41$, Test Set $N = 500$, Group-Disjoint Split (parcel_id, primary_seller_id, scenario_id, template cohort with 0 leakage), and Confusion Matrix (TN: 161, FP: 7, FN: 2, TP: 330).
  - **Idempotent SLA Overdue Escalation:** `process_sla_escalations()` identifies breached cases, sets `overdue_escalated = True` (ensuring exactly one escalation trigger), appends `[SLA OVERDUE ESCALATION]` case note, dispatches in-app notification to Senior Registrar, and logs `CASE_SLA_OVERDUE_ESCALATION` audit event. Exposed via `POST /api/cases/sla/escalate`.
  - **Case Reassignment & Priority History:** Tracks every officer reassignment and priority change with timestamp, previous state, new state, modifying user, and administrative rationale.
  - **Production Security Guards:** `check_production_security()` enforces minimum 32-char `SECRET_KEY` and restricts `/api/auth/demo-login` when `ENVIRONMENT=production`.

---

### Workflow 9: Test Suite Baseline & Git Hygiene
- **Status:** **PASS**
- **Test Suite Command:** `pytest -q`
- **Output:**
  ```text
  [LandGuard DB] Active primary database: SQLite at C:\Users\ASHIK_~1\AppData\Local\Temp\landguard_test_isolation_e_mrcgvk\landguard_operational.db
  [LandGuard DB] Verified SQLite operational schema at C:\Users\ASHIK_~1\AppData\Local\Temp\landguard_test_isolation_e_mrcgvk\landguard_operational.db
  [LandGuard Service] Loaded frozen XGBoost risk model from F:\land gurd main project\models\xgboost_risk_model.joblib
  ============================ 177 passed in 31.64s =============================
  ```
- **Test Metrics:**
  - Total collected test cases: **177**
  - Passed: **177 (100%)**
  - Failed: **0**
  - Skipped: **0**
  - Warnings: **0**
  - Regressions: **0**
  - Total Test Files: **33 test suites**
  - Test Database Isolation: **Active & Verified (0 operational DB writes)**
- **Git State:**
  - `git diff --check`: **Exited with code 0 (zero whitespace errors)**.
  - `git status -s`: Working tree contains verified modular components and reports. **Zero Git commits were executed**, adhering strictly to the user prompt instructions.

---

## 3. Unresolved Defects, Risks, or Blockers

- **Critical Bugs / Functional Regressions:** **None identified.**
- **Security Vulnerabilities:** **None identified.** (RBAC, IDOR, password hashing, and CSRF protection active).
- **Environmental Limitations:** Live audio speech recognition requires a browser environment supporting the Web Speech API (e.g., Chrome or Edge) with microphone hardware permissions enabled. The platform handles headless/unsupported environments with graceful text console fallback.

---

## 4. Prioritized Recommendations for Release

1. **Production Deployment Configuration**:
   - Ensure `SECRET_KEY` in production `.env` is set to a cryptographically secure 256-bit random key.
   - Run behind an HTTPS reverse proxy (such as Nginx or Caddy) to allow browser Web Speech API microphone access (browsers require HTTPS or localhost for microphone permissions).
2. **PostgreSQL Standby Activation (Optional Future Enhancement)**:
   - When migrating from single-node SQLite to high-availability multi-node deployment, switch `DATABASE_BACKEND=POSTGRESQL` to route traffic to the standby Neon PostgreSQL database.

---

**Audited By:** Lead QA & Systems Architect  
**Result:** **ACCEPTED FOR RELEASE**
