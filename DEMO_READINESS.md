# LandGuard AI — Complete Project & Demo Readiness Report (Version 5.0)

> **Project Root**: `F:\land gurd main project`  
> **Source Foundation**: `F:\land gurd`  
> **Target Track**: LandTech 2026 P3 — Fraud & Double-Selling Detection  
> **Architecture**: Login-First Multi-Page Web Application, Server-Enforced RBAC, Separate Citizen & Admin Portals  
> **Operational Database**: Neon PostgreSQL (`DATABASE_URL`) with seamless SQLite local fallback (`data/landguard_operational.db`)  
> **Legal Notice & Watermark**: `SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT`  
> **Test Status**: **`63 / 63 AUTOMATED TESTS PASSING (100%)`**  
> **Demo Seed**: **`7 / 7 SCENARIOS VERIFIED (100%)`**  

---

## 1. Executive Summary & Verification Classification

This document provides the definitive verification, inventory, and operational execution guide for the **LandGuard AI Land Record Verification Platform**. Following the SRS v5.0 consolidated specification and hackathon prompt requirements:
- The application is **login-first**: unauthenticated visitors cannot access private dashboards and are routed through `/` (Landing) and `/login`.
- **Two distinct portals** are fully implemented:
  - **Citizen / User Portal** (`/user/*`) featuring the bank-card-inspired LandGuard Digital Identity Card, verification wizard, cadastral search, and grievance tracking.
  - **Admin / Investigator Portal** (`/admin/*`) featuring the operational command center, case docket, priority controls, expedite approval queue, and evidence dossiers.
- **Server-enforced RBAC**: Protected by server-side session checks and role boundaries. A citizen cannot access admin screens or APIs (redirected to `/access-denied`).
- **Database & Auditing**: Schema covers all 10 table groups with indexed relational tables and an immutable audit log.

| Category | Definition | Status in Project |
| :--- | :--- | :--- |
| **`DISCOVERED`** | Resource physically located on disk via recursive search | **100% Found** (`data/`, `models/`, `reports/`, `src/`, `tests/`) |
| **`VERIFIED`** | Code integrity, schema compliance, checksums, and model loading tested | **100% Verified** (63/63 automated tests passing in 3.02s) |
| **`IMPLEMENTED`** | Application features, APIs, UI workflows, and seed scripts built | **100% Implemented** (Separate Portals, Stepper, Identity Card, Dockets) |
| **`DEMO READY`** | One-click demo roles, reproducible seed fixtures, running server | **100% Ready** (Port 8000 live) |

---

## 2. Access Credentials & Demo Roles

For local hackathon evaluation, three isolated demo accounts are configured with instant one-click login buttons on `/login`:

| Role | Demo Email | Password | Display Name & Staff/Digital ID | Authorized Portal |
| :--- | :--- | :--- | :--- | :--- |
| **`CITIZEN`** | `citizen@landguard.gov.bd` | `demo123` | **Rafiqul Islam** (`CIT-BD-884920`) | `/user/dashboard` |
| **`INVESTIGATOR`** | `investigator@landguard.gov.bd` | `demo123` | **Inspector S. Karim** (`OFF-INV-2041`) | `/admin/dashboard` |
| **`ADMIN`** | `admin@landguard.gov.bd` | `admin123` | **Senior Registrar M. Rahman** (`ADM-REG-1001`) | `/admin/dashboard` |

---

## 3. Full Application Route Catalog

Every page is a **real, dedicated route** with its own semantic layout, navigation, and workflows:

### A. Public Routes (Unauthenticated)
- **`/`** — Public Landing Page (P3 problem statement, 3 process steps, core capabilities, metric highlights, synthetic disclaimer).
- **`/login`** — Authentication Portal (Email/password form, password visibility toggle, error display, 3 one-click Demo Role buttons).
- **`/access-denied`** — 403 Forbidden Access Denied Screen (clean RBAC clearance notification).
- **`/not-found`** — 404 Not Found Page.
- **`/logout`** — Session invalidation endpoint (destroys session and clears cookie).

### B. Citizen / User Portal (`/user/*`)
- **`/user/dashboard`** — Citizen Verification Center (Bank-card-styled LandGuard Identity Card, stats counters, quick verification action, recent activity).
- **`/user/verify`** & **`/user/verify/new`** — 4-Step Interactive Verification Stepper (Ingestion -> Bilingual OCR -> Human Confirmation -> Statutory Result & Risk Gauge).
- **`/user/verify/{id}`** — Verification Result Dossier (Deterministic rules breakdown, ML risk score, CV physical tampering score, report export).
- **`/user/parcels`** — Cadastral Registry Search (Search by Dag plot, Mouza, Upazila, District; holding capacity and mutation counts).
- **`/user/parcels/{id}`** — Parcel Profile (CS -> SA -> RS -> BS survey chain of title, conveyance deed history, AC Land mutation records, tax status).
- **`/user/history`** — Citizen's Past Submissions (Table of verified dossiers with status badges and report download links).
- **`/user/complaints`** — Citizen Grievances List (Status tracking, expedited review flags, case IDs).
- **`/user/complaints/new`** — File Dispute Grievance (Category, Dag plot, deed ref, narrative description, expedited review request toggle).
- **`/user/complaints/{id}`** — Complaint Progression Workspace (Resolution timeline, investigator notes, expedite status).
- **`/user/notifications`** — Real-Time Notification Alerts Feed.
- **`/user/profile`** — Full Citizen Profile & Large Digital Identity Card.
- **`/user/settings`** — Citizen Preferences (Language selection English / Bangla, alert preferences).

### C. Admin / Investigator Portal (`/admin/*`)
- **`/admin/dashboard`** — Investigator Command Center (KPI counters, pending expedite review alert queue, priority case docket, real-time alert stream).
- **`/admin/verifications`** — Verification Operations Queue (Status filters `CONFIRMED_INCONSISTENCY`, `REVIEW_REQUIRED`, `MISSING_EVIDENCE`, `CLEAR_FOR_STANDARD_PROCESSING`).
- **`/admin/verifications/{id}`** — Investigator Review Workspace (Statutory rules table, ML contributing factors, CV seal/signature inspection, decision actions).
- **`/admin/cases`** — Investigation Case Docket (Case search, status filters, priority filters, overdue flags).
- **`/admin/cases/{id}`** — Case Investigation Workspace (Priority changer `CRITICAL`, `HIGH`, `NORMAL`, `LOW`, status progression, investigator assignment, officer notes timeline).
- **`/admin/parcels`** — Cadastral Registry Explorer.
- **`/admin/reports`** — Evidence Dossiers List (SHA-256 certificate hashes).
- **`/admin/reports/{id}`** — Official Printable Statutory Audit Certificate (Double-border cert paper, SHA-256 hash, watermark, signature block).
- **`/admin/analytics`** — Empirical Analytics & Insights (Outcome distributions, top triggered rules, resolution pipeline, ML benchmark scores).
- **`/admin/audit`** — Immutable Security Audit Log (Append-only database event trail).
- **`/admin/users`** — User Directory & RBAC Clearance Matrix.
- **`/admin/models`** — AI Model Governance Card (19 features, evaluation metrics, OCR and CV detector specifications).
- **`/admin/system`** — System Health & Infrastructure Diagnostics (Subsystem status, dataset counts, database status).
- **`/admin/settings`** — Operations Settings & SLA Turnaround Targets.

---

## 4. Discovered Resource Paths & Data Inventory

### A. Data & Synthetic Fixtures
- **Canonical Structured Records**:
  - Path: [`data/full/records/canonical_records.json`](file:///F:/land%20gurd%20main%20project/data/full/records/canonical_records.json)
  - Records Count: **100,000 total records** across 2,500 scenarios (`15,000` owners, `10,000` parcels, `30,000` khatians, `25,000` transactions, `10,000` mutations, `10,000` tax receipts).
- **Targeted Expansion Records**:
  - Path: [`data/targeted_expansion/records/targeted_records.json`](file:///F:/land%20gurd%20main%20project/data/targeted_expansion/records/targeted_records.json)
  - Records Count: **100 targeted challenge records** covering compound fraud mechanisms, pre-1972 archival reference gaps, and administrative mutation lag.
- **Rendered Document Images**:
  - Path: [`data/full/images/`](file:///F:/land%20gurd%20main%20project/data/full/images/) (**600 benchmark PNG images** spanning 6 document types and 15 degradation regimes).
  - Path: [`data/targeted_expansion/images/`](file:///F:/land%20gurd%20main%20project/data/targeted_expansion/images/) (**24 targeted PNG images** including physical paste-over seams and pre-1972 archives).
  - Watermark Check: **100.0% (`600/600`)** indelible presence of `SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT`.
- **Demo Fixtures**:
  - Path: [`data/fixtures/demo_manifest.json`](file:///F:/land%20gurd%20main%20project/data/fixtures/demo_manifest.json) (7 standardized demonstration fixtures).

### B. Machine Learning & Computer Vision Models
- **Supervised XGBoost Risk Model Artifact**:
  - Path: [`models/xgboost_risk_model.joblib`](file:///F:/land%20gurd%20main%20project/models/xgboost_risk_model.joblib)
  - Metadata: [`models/model_metadata.json`](file:///F:/land%20gurd%20main%20project/models/model_metadata.json)
  - Feature Architecture: **19 Features** (15 Registry Features + 4 Document Evidence Features).
  - Performance: **Accuracy: 99.8%**, **Precision: 99.7%**, **Recall: 100.0%**, **F1: 0.9985**, **ROC-AUC: 1.0**, **Brier Score: 0.0013**.
- **Deterministic Statutory Rule Engine**:
  - Path: [`src/landguard_models/verification_rules.py`](file:///F:/land%20gurd%20main%20project/src/landguard_models/verification_rules.py)
- **Explainable Multi-Modal Risk Synthesizer**:
  - Path: [`src/landguard_models/explainable_risk.py`](file:///F:/land%20gurd%20main%20project/src/landguard_models/explainable_risk.py)
- **Bilingual OCR Extraction Pipeline**:
  - Path: [`src/landguard_vision/run_ocr.py`](file:///F:/land%20gurd%20main%20project/src/landguard_vision/run_ocr.py) (RapidOCR ONNX + Tesseract 5.4 `ben+eng`).
- **Computer Vision Presence & Tampering Detectors**:
  - Path: [`src/landguard_vision/seal_presence.py`](file:///F:/land%20gurd%20main%20project/src/landguard_vision/seal_presence.py) (99.5% accuracy).
  - Path: [`src/landguard_vision/signature_presence.py`](file:///F:/land%20gurd%20main%20project/src/landguard_vision/signature_presence.py) (98.2% accuracy).
  - Path: [`src/landguard_vision/visual_anomaly_baseline.py`](file:///F:/land%20gurd%20main%20project/src/landguard_vision/visual_anomaly_baseline.py) (96% recall).

---

## 5. Curated Demo Scenarios Matrix (7/7 Pass)

| Demo ID | Scenario Category | Presets / Source | Statutory Verdict | Rules Triggered | ML Risk Score |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **`DEMO-CLEAN`** | `LEGITIMATE_NORMAL_SALE` | Plot 9044, DEED-2006-18946, 8.38 dec | **`CLEAR_FOR_STANDARD_PROCESSING`** | None (0 violations) | **`0.0301`** (3.0%) |
| **`DEMO-MUTATION-MISMATCH`** | `UNREGISTERED_MUTATION_MISMATCH` | Plot 7025, DEED-2017-55696, 47.94 dec | **`CONFIRMED_INCONSISTENCY`** | `RULE_UNVERIFIED_MUTATION_RECORD` | **`0.8721`** (87.2%) |
| **`DEMO-DOUBLE-SALE`** | `CONFLICTING_DOUBLE_SALE` | Plot 6792, DEED-2005-23539, 31.82 dec | **`CONFIRMED_INCONSISTENCY`** | `RULE_SELLER_NOT_TITLEHOLDER` | **`0.9873`** (98.7%) |
| **`DEMO-MISSING-ARCHIVE`** | `AMBIGUOUS_UNTRACED_PRE1972_DEED`| Plot 9289, DEED-2013-52068, 11.58 dec | **`MISSING_EVIDENCE`** | `RULE_BROKEN_CHAIN_OF_TITLE` | **`0.9821`** (Elevated) |
| **`DEMO-AREA-EXCESS`** | `EXAGGERATED_LAND_AREA` | Plot 9262, DEED-2012-85693, 203.89 dec | **`CONFIRMED_INCONSISTENCY`** | `RULE_AREA_EXCEEDS_CAPACITY` | **`0.9999`** (>99.9%) |
| **`DEMO-ALTERED-PLOT`** | `ALTERED_PLOT_NUMBER` | Plot 6274, DEED-2011-19951, 51.96 dec | **`CONFIRMED_INCONSISTENCY`** | `RULE_PLOT_NOT_FOUND_IN_REGISTRY` | **`0.9999`** (>99.9%) |
| **`DEMO-VISUAL-TAMPERING`** | `VISUAL_OVERLAY_TAMPERING` | Plot 5235, DEED-2021-65260, 49.50 dec | **`CONFIRMED_INCONSISTENCY`** | `RULE_VISUAL_TAMPERING_DETECTED` | **`0.8250`** (82.5%) |

---

## 6. How to Install, Seed, Test & Run

### 1. Verify Demo Fixtures (Idempotent Seed)
```bash
python scripts/seed_demo.py
# Outputs: Demo Seeding & Verification Summary: 7/7 Scenarios Verified.
```

### 2. Run Automated Test Suite
```bash
pytest tests/ -v
# Outputs: 63 passed in 3.02s (100% passing)
```

### 3. Start the Application Server
```bash
uvicorn src.landguard_web.app:app --host 127.0.0.1 --port 8000
```
Open a browser and navigate to: **`http://127.0.0.1:8000`**

---

## 7. Step-by-Step Judge / Evaluator Walkthrough

1. **Step 1: Open Home & Login**:
   - Navigate to `http://127.0.0.1:8000/`. Review the public overview and capabilities.
   - Click "Enter Portal" or "Sign In" to reach `http://127.0.0.1:8000/login`.
2. **Step 2: Enter as Citizen**:
   - Click the cyan button **"Continue as Demo Citizen"**.
   - You are authenticated as **Rafiqul Islam** and arrive at `/user/dashboard`.
   - Inspect the bank-card-styled **LandGuard Digital Identity Card** (gold chip, holographic sheen, ID `CIT-BD-884920`).
3. **Step 3: Run Statutory Deed Verification**:
   - Click **"Start New Verification"** to reach `/user/verify`.
   - Click **"Conflicting Double Disposition"** (Plot #6792) to load the benchmark case.
   - Click **"Run Statutory Verification"**.
   - Review findings: `CONFIRMED STATUTORY INCONSISTENCY`, `RULE_SELLER_NOT_TITLEHOLDER` violation, 98.7% risk metric.
   - Click **"Export Certificate"** to view the printable certificate with SHA-256 integrity hash.
4. **Step 4: File a Citizen Dispute Grievance**:
   - Click **"File Grievance"** to open `/user/complaints/new`.
   - Check **"Request Expedited Review"** and enter urgency rationale (e.g. "Vendor demands earnest money within 24 hours").
   - Click **"Submit Grievance to Registry"**. Tracking ID `CMP-2026-XXX` is created.
5. **Step 5: Sign Out & Enter as Admin**:
   - Click **"Logout"** in the topbar or sidebar.
   - On the login screen, click **"Continue as Demo Admin"** (Senior Registrar M. Rahman).
   - You arrive at `/admin/dashboard` (Investigator Command Center).
6. **Step 6: Review Case Docket & Approve Expedite**:
   - Notice the citizen's urgent request in the **Expedited Review Queue**.
   - Click **"Approve Expedite"** and provide statutory justification. The case priority upgrades to `CRITICAL`.
   - Click **"Open Workspace"** on the case (`/admin/cases/CASE-2026-001`).
   - Change case status to `UNDER_REVIEW`, update assigned officer to `Inspector S. Karim`, and append an official investigation note.
7. **Step 7: Inspect System Diagnostics**:
   - Click **"AI Model Ops"** (`/admin/models`) to inspect the 19 features and evaluation curves.
   - Click **"Immutable Audit Log"** (`/admin/audit`) to verify all logins, status changes, and expedite approvals are recorded.

---

## 8. Known Limitations & Responsible Use Boundaries

1. **Synthetic Nature**: 100% of names, National IDs (`OWN-XXXXXXXX`), deeds (`DEED-YYYY-XXXXX`), and plots are synthetically generated for research benchmarking. Not valid for real legal conveyance or official land registration.
2. **Presence vs. Judicial Authenticity**: Seal detection verifies geometric circular stamp ink contours; signature detection verifies stroke complexity. Neither constitutes biometric identification or notarized legal authenticity.
3. **Colonial Handwritten Deeds Gap**: Synthetic typeset fonts do not fully simulate handwritten colonial CS/SA calligraphic deeds.
4. **Severe Degraded Scans**: High shadow illumination gradients or sub-100 DPI scans can elevate OCR character error rates, making human-in-the-loop review mandatory.
5. **Decision Support Only**: LandGuard outputs support administrative review and do not supersede sub-registrar judicial authority.
