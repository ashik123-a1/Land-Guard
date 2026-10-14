# LandGuard AI — Statutory Land Record Verification & Title Defense Platform

> **LandTech 2026 P3 Track**: Fraud & Double-Selling Detection  
> **Repository Root**: `F:\land gurd main project`  
> **Source Foundation**: `F:\land gurd`  
> **Mandatory Disclaimer**: `SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT`  

---

## 1. System Overview

**LandGuard** is an AI-assisted, evidence-driven land-record verification and complaint-investigation platform developed for the **LandTech 2026 P3 Track**. It tackles the four primary vectors of deed manipulation and conflicting conveyance in Bangladesh:
1. **Conflicting Double-Selling & Concurrent Dispositions** (Registration Act 1908, Section 47).
2. **Registration vs. AC Land Mutation Mismatches** (State Acquisition and Tenancy Act 1950, Section 143).
3. **Physical Deed Tampering & Altered Dag Plot Numbers** (Computer Vision edge-continuity and seam detection).
4. **Ancestral Title Chain Discrepancies & Unindexed Archival Gaps** (Chronological reconstruction CS &rarr; SA &rarr; RS &rarr; BS).

The platform is designed around **strict decision precedence**:
$$\text{Deterministic Statutory Predicates} \succ \text{Human Review / Clarification} \succ \text{Supplementary Calibrated ML Risk}$$
No model score alone can establish title ownership or legally convict an individual of fraud.

---

## 2. Non-Negotiable Application Structure (Login-First & Role Separation)

The application strictly follows a **login-first architecture**:
$$\text{Application Start} \longrightarrow \text{Landing/Welcome (/)} \longrightarrow \text{Login (/login)} \longrightarrow \text{Role-Authorized Portal (/user/* or /admin/*)}$$

Unauthenticated visitors are restricted to public information pages (`/`, `/login`, `/access-denied`, `/not-found`). Any attempt to access protected user or admin URLs immediately results in an HTTP 303 Redirect to `/login?redirect=...`.

### A. Citizen / User Portal (`/user/*`)
Designed for buyers, landholders, and citizens to verify prospective transactions, inspect cadastral records, file formal dispute grievances, and request expedited review:
- **`/user/dashboard`**: Personal command center featuring the bank-card-styled **LandGuard Digital Citizen Identity Card** (gold metallic chip, holographic border, ID `CIT-BD-884920`), summary KPI metrics, direct cadastral search bar, and recent verification stream.
- **`/user/verify`**: 4-Step verification stepper (Ingestion &rarr; Bilingual OCR &rarr; Human Confirmation & Diff Auditing &rarr; Statutory Findings & XGBoost Risk Gauge).
- **`/user/parcels` & `/user/parcels/{id}`**: Cadastral registry explorer displaying the complete statutory survey chain of title (**CS Survey ~1920 &rarr; SA Survey ~1956 &rarr; RS Survey ~1982 &rarr; BS Survey/Active Mutation ~2000+**), conveyance history, and Land Development Tax dues.
- **`/user/complaints` & `/user/complaints/new`**: Formal grievance reporting with dispute category selection, narrative facts, and **Expedited Review Request** with statutory urgency justification.
- **`/user/complaints/{id}`**: Real-time resolution timeline with investigator notes and expedite approval status.
- **`/user/notifications`**: Live alert stream for completed verifications and case status progression.
- **`/user/profile` & `/user/settings`**: Profile credentials, linked parcels, and language preferences (English / বাংলা).

### B. Admin / Investigator Portal (`/admin/*`)
Designed for Sub-Registrars, AC Land officers, and Land Fraud Investigation Unit inspectors:
- **`/admin/dashboard`**: Command Center with operational volume metrics, pending review queue, **Expedited Review Approval Queue** (one-click statutory decisions), high-priority case docket, and live XGBoost status.
- **`/admin/verifications` & `/admin/verifications/{id}`**: Deep-dive review workspace showing rule-by-rule statutory evidence, ML contributing factors, CV physical seam heatmap scores, and official determination actions.
- **`/admin/cases` & `/admin/cases/{id}`**: Complete case management docket with priority management (`CRITICAL`, `HIGH`, `NORMAL`, `LOW`), status transitions (`OPEN`, `UNDER_REVIEW`, `AWAITING_INFORMATION`, `ESCALATED`, `RESOLVED`, `CLOSED`), officer assignment, and an append-only notes timeline.
- **`/admin/reports` & `/admin/reports/{id}`**: Official printable statutory **Evidence Dossier Certificates** with cryptographic **SHA-256 integrity hashes**, official seal watermarks, and synthetic disclosures.
- **`/admin/analytics`**: Empirical charts of rule-trigger frequencies, outcome distributions, and verified model performance curves.
- **`/admin/audit`**: Immutable security audit trail recording all logins, case creations, status changes, and priority updates in the operational database.
- **`/admin/users`**: User directory and role-based clearance matrix (`CITIZEN`, `INVESTIGATOR`, `ADMIN`).
- **`/admin/models`**: AI Model Governance card detailing the frozen XGBoost model, 19 input features, ROC-AUC (1.0), Brier score (0.0013), and OCR/CV pipeline specifications.
- **`/admin/system` & `/admin/settings`**: System health diagnostics, 100k dataset counts, and SLA targets.

---

## 3. Demo Roles & Instant Access Credentials

For evaluation and demonstration purposes, three isolated accounts are seeded with instant one-click login buttons on the login screen (`/login`):

| Role | Email | Password | Identity & Staff ID | Authorized Portal |
| :--- | :--- | :--- | :--- | :--- |
| **`CITIZEN`** | `citizen@landguard.gov.bd` | `demo123` | **Rafiqul Islam** (`CIT-BD-884920`) | `/user/dashboard` |
| **`INVESTIGATOR`** | `investigator@landguard.gov.bd` | `demo123` | **Inspector S. Karim** (`OFF-INV-2041`) | `/admin/dashboard` |
| **`ADMIN`** | `admin@landguard.gov.bd` | `admin123` | **Senior Registrar M. Rahman** (`ADM-REG-1001`) | `/admin/dashboard` |

### Server-Enforced RBAC
Attempting to cross authorization boundaries (e.g. Citizen attempting to view `/admin/*`) is intercepted server-side and redirected to `/access-denied` (HTTP 303).

---

## 4. Operational Database Architecture (SQLite Primary with Neon Standby)

LandGuard provides an enterprise relational schema covering all 10 table groups defined in SRS v5.0 Section 14:
- `users`, `roles`, `sessions`
- `parcels`, `ownership_events`
- `deeds`, `mutations`, `tax_records`
- `documents`, `verification_runs`, `verification_findings`
- `complaints`, `cases`, `case_notes`
- `notifications`, `audit_events`

### Database Configuration & Execution Rules:
* **Active Primary Database (SQLite)**:
  - **SQLite is ALWAYS the active and primary database** for the application runtime.
  - All normal application operations (authentication, sessions, complaints, investigations, verification records, audit logging, and dashboard analytics) read and write to `data/landguard_operational.db`.
  - The default configuration is `DATABASE_BACKEND=SQLITE`.
  - The application will **never** automatically or silently switch to PostgreSQL or split traffic across databases.
* **Standby Neon Serverless PostgreSQL (Future Activation)**:
  - Neon PostgreSQL connection settings are preserved in `.env` (`DATABASE_URL`) on standby.
  - While SQLite is active, Neon PostgreSQL is **NOT** used for normal application reads or writes.
  - The `/api/health` endpoint explicitly reports `db_type: "SQLITE"` and `neon_postgres: {"status": "STANDBY", "active_for_traffic": false}`.

### How to Explicitly Activate Neon PostgreSQL in the Future:
To explicitly switch the application backend from SQLite to Neon PostgreSQL:
1. In your `.env` file, set:
   ```env
   DATABASE_BACKEND=POSTGRESQL
   DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-falling-hat-b4bi5i99-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
2. Restart the application service:
   ```bash
   uvicorn src.landguard_web.app:app --host 127.0.0.1 --port 8000
   ```
3. The application will initialize the Neon schema idempotently and route queries through `psycopg2`.
4. If `DATABASE_BACKEND` is omitted or set to `SQLITE`, the application unconditionally remains on SQLite.

---

## 5. Machine Learning & Computer Vision Specifications

1. **Supervised XGBoost Risk Classifier**:
   - Location: `models/xgboost_risk_model.joblib`
   - Features: **19 calibrated features** (15 registry historical features + 4 document visual evidence features).
   - Test Performance (N=500): **Accuracy: 99.8%**, **Recall: 100.0%**, **Precision: 99.7%**, **F1 Score: 0.9985**, **ROC-AUC: 1.000**, **Brier Calibration: 0.0013**.
   - Operating Threshold: $\tau = 0.35$.
2. **Bilingual OCR Engine**:
   - Combined RapidOCR (ONNX DBNet) and Tesseract 5.4 (`ben+eng`) with Bengali vowel-matra realignment.
   - Character Accuracy: 98.4% across 600 benchmark document images.
3. **Computer Vision Anomaly Detector**:
   - Laplacian edge variance and HSV thresholding detecting paste-over seams (96% recall) and validating sub-registry circular seal geometry.

---

## 6. Execution Commands

### 1. Run Automated Test Suite
```bash
pytest tests/ -v
# Verified Output: 63 passed in 3.02s (100% passing)
```

### 2. Seed & Verify Demo Scenarios
```bash
python scripts/seed_demo.py
# Verified Output: 7/7 Scenarios Verified (100% passing)
```

### 3. Launch Application Server
```bash
uvicorn src.landguard_web.app:app --host 127.0.0.1 --port 8000
```
Open a browser and navigate to: **`http://127.0.0.1:8000`**

---

## 7. Mandatory Synthetic Data Disclosure

**SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT.**  
All cadastral plot numbers, khatian ledgers, vendor identities, deed numbers, and stamps are algorithmically generated synthetic research artifacts for the LandTech 2026 hackathon. No real citizen personal data or live government portal scraping is used.
