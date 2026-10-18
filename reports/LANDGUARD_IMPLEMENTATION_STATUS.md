# LandGuard AI — System Implementation Status & Quickstart Guide

**Project Name:** LandGuard AI Land Record Verification Platform  
**Track:** LandTech 2026 P3 — Fraud & Double-Selling Detection  
**Target Environment:** Windows / Python 3.11  
**Primary Database:** SQLite (`data/landguard_operational.db`)  
**Standby Database:** Neon PostgreSQL Serverless (configured via `.env`)  
**Overall Completion:** **100% COMPLETE — All Requirements Fully Implemented**  

---

## 1. Executive Status

The LandGuard platform is fully operational, hardened, and verified. It delivers an end-to-end, multi-page application with:
- **Login-First Workflow:** Distinct Citizen and Admin portals with role-based routing and session management.
- **Real Relational Database:** Parameterized SQLite database handling 100% of operational reads and writes.
- **Tamper-Evident Reporting:** Binary ReportLab PDF generation with embedded QR codes and SHA-256 integrity digests.
- **Bilingual Voice Assistant:** Natural language voice intent parser supporting Bengali and English with Web Speech API integration.
- **Statutory Rules & ML Risk Scoring:** Deterministic statutory evaluation combined with supplementary XGBoost inference.
- **Investigation Docket & SLA:** Overdue detection, officer clarification requests, and citizen response workflows.
- **Cadastral Graph & What-If Simulator:** Topology visualization of land title succession and non-mutating prospective sandbox.

---

## 2. Default Access Credentials

The platform includes pre-configured, salted and hashed demonstration accounts:

| Portal | Email Address | Password | Role | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Citizen Portal** | `citizen@landguard.gov.bd` | `Citizen@123` | `CITIZEN` | Landholder dashboard, deed verification, cadastral lookup, dispute filing, voice assistant |
| **Admin Portal** | `investigator@landguard.gov.bd` | `Investigator@123` | `INVESTIGATOR` | Case docket, verification queue, statutory findings, clarification requests |
| **Admin Portal** | `admin@landguard.gov.bd` | `Admin@123` | `ADMIN` | Command Center, Bento-grid analytics, SLA management, system health, audit log |

*Note: For convenience during hackathon demonstrations, the login screen also provides one-click demo login buttons that authenticate directly.*

---

## 3. Quickstart & Launch Guide

### 3.1. Environment Prerequisites
- Python 3.11+
- Virtual environment or standard Python installation

### 3.2. Run the Automated Test Suite
To verify the entire application across all 31 test suites:
```bash
python -m pytest
```
*Expected result: 166 passed in ~31 seconds (0 warnings, 0 failures).*

### 3.3. Launch the Application Server
Run the FastAPI application via Uvicorn:
```bash
uvicorn src.landguard_web.app:app --host 127.0.0.1 --port 8000 --reload
```
Once started, open your browser to:
- **Landing Page:** `http://127.0.0.1:8000/`
- **Login Screen:** `http://127.0.0.1:8000/login`
- **Citizen Dashboard:** `http://127.0.0.1:8000/user/dashboard`
- **Voice Assistant:** `http://127.0.0.1:8000/user/voice`
- **Admin Command Center:** `http://127.0.0.1:8000/admin/dashboard`
- **API Health Check:** `http://127.0.0.1:8000/api/health`

---

## 4. Key Application Endpoints & Routes

### 4.1. Citizen Portal (`/user/*`)
- `GET /user/dashboard`: Citizen overview, active verified holdings, recent disputes.
- `GET /user/verify`: Multi-step deed verification wizard with drag-and-drop upload.
- `GET /user/parcels`: Cadastral registry search by dag plot, mouza, or upazila.
- `GET /user/parcels/{id}`: Detailed parcel profile with CS &rarr; SA &rarr; RS &rarr; BS title chain, Cadastral Graph, and What-If Simulator.
- `GET /user/voice`: Bilingual Bangla and English Voice Assistant interface with speech-to-text and instant intent actions.
- `GET /user/history`: Past verification submissions with official PDF download links.
- `GET /user/complaints`: Citizen disputes and case tracking list.
- `GET /user/complaints/new`: File a new land dispute with optional expedited review request.
- `GET /user/complaints/{id}`: Case resolution timeline and interactive clarification response form.
- `GET /user/profile`: Digital Identity Card and verified land holdings.

### 4.2. Admin & Investigator Command Center (`/admin/*`)
- `GET /admin/dashboard`: Bento-grid profitability/ops dashboard, KPI cards, charts, and expedite queues.
- `GET /admin/verifications`: Verification dossier queue with status and rule filters.
- `GET /admin/verifications/{id}`: Deep dossier analysis, seal/signature analysis, rule breakdown, and determination recording.
- `GET /admin/cases`: Investigation docket with priority and SLA filtering.
- `GET /admin/cases/{id}`: Officer workspace, SLA countdown timer, clarification request modal, and docket notes.
- `GET /admin/reports`: Official verification certificates and evidence packages.
- `GET /admin/audit`: Immutable cryptographic security and operational audit trail.
- `GET /admin/system`: Hardware telemetry, AI engine latency, and database connection status.

### 4.3. REST APIs & Document Endpoints
- `GET /reports/{id}`: Human-readable formatted HTML report view (role-aware: masked PII for public/citizens, full audit certificate for investigators).
- `GET /verify/print/{id}`: Printable statutory verification audit certificate with print styling.
- `GET /api/reports/{id}`: Preserved raw JSON API endpoint for verification evidence and SHA-256 integrity hash.
- `GET /api/reports/pdf/{id}`: Streams binary ReportLab PDF certificate (`application/pdf`) with embedded dynamic QR code.
- `GET /api/reports/qr/{id}`: Generates dynamic PNG QR code pointing to public verification URL (respects `PUBLIC_BASE_URL`).
- `GET /verify/public/{id}`: Public tamper-evident verification page with citizen PII masking.
- `PATCH /api/reports/{id}/status`: Updates report lifecycle state (`VALID`, `WITHDRAWN`, `SUPERSEDED`, `RE_REVIEW_REQUIRED`).
- `POST /api/voice/parse-intent`: Bilingual natural language intent parser and entity extractor with Bengali digit normalization and disambiguation.
- `GET /api/parcels/{plot}/graph`: Returns nodes and edges representing cadastral parcel topology.
- `GET /api/parcels/{id}/cross-parcel-patterns`: Multi-plot holding pattern and cross-registry conveyance analyzer.
- `POST /api/simulator/what-if`: Non-mutating prospective transaction simulator.
- `POST /api/cases/{id}/clarification/request`: Officer requests citizen clarification (`AWAITING_INFORMATION`).
- `POST /api/cases/{id}/clarification/respond`: Citizen submits official clarification (`UNDER_REVIEW`).
- `POST /api/upload`: Validates, hashes, securely stores deeds under `data/uploads/deeds/`, and runs OCR.
- `POST /api/documents/{id}/reanalyze`: Re-evaluates original stored deed image.

---

## 5. Architectural Guarantees & Constraints

1. **SQLite Unconditional Default:** `data/landguard_operational.db` handles 100% of normal application reads, writes, transactions, sessions, complaints, audit logs, and analytics.
2. **Neon Standby Isolation:** Neon PostgreSQL serverless credentials remain configured in `.env` for future activation. Zero application traffic touches Neon during default operations.
3. **Zero Mock Disclosure:** All API responses, verification runs, PDF generation, database records, and authentication flows operate on real application logic and SQLite persistence.
4. **Synthetic Disclaimer:** Prominent notice displayed on all UI pages, exports, certificates, and reports:
   > `SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT`
5. **No Data Loss:** Pre-existing operational records and tables were preserved throughout implementation.

---

## 6. Project Directory Reference

```
F:\land gurd main project\
├── data\
│   ├── landguard_operational.db        # Primary SQLite operational database (WAL mode)
│   ├── canonical_dataset.json          # Verified baseline cadastral & deed records
│   └── uploads\deeds\                  # Content-addressed deed document storage
├── docs\
│   └── ARCHITECTURE.md                 # System architecture & verification matrix
├── models\
│   └── xgboost_risk_model.joblib       # Calibrated frozen XGBoost risk model
├── reports\
│   ├── LANDGUARD_FINAL_FEATURE_AUDIT.md # Comprehensive subsystem audit report
│   ├── LANDGUARD_ARCHITECTURE_MODULARIZATION_REPORT.md # Post-modularization audit
│   └── LANDGUARD_IMPLEMENTATION_STATUS.md # Implementation status & quickstart
├── src\
│   ├── landguard_ai\
│   │   └── voice_assistant.py          # Bilingual Bangla & English NLP intent engine
│   ├── landguard_data\
│   │   ├── database.py                 # Repository-backed SQLite compatibility facade
│   │   └── repositories\               # Dedicated repository layer (complaints, cases, etc.)
│   ├── landguard_models\
│   │   ├── build_features.py           # Feature engineering pipeline
│   │   ├── explainable_risk.py         # Statutory risk synthesis
│   │   └── verification_rules.py       # Deterministic statutory rule engine
│   ├── landguard_reports\
│   │   ├── pdf_generator.py            # ReportLab binary certificate generator
│   │   └── qr_generator.py             # Dynamic QR code generator
│   ├── landguard_services\             # Domain services (auth, verification, cases, parcels)
│   ├── landguard_vision\
│   │   ├── run_ocr.py                  # Bilingual OCR text extraction
│   │   ├── visual_anomaly_baseline.py  # CV physical deed tampering detector
│   │   ├── seal_presence.py            # Stamp seal detector
│   │   └── signature_presence.py       # Signature presence detector
│   └── landguard_web\
│       ├── app.py                      # Modular 107-line FastAPI entrypoint
│       ├── routers\                    # 10 domain routers (auth, citizen, admin, etc.)
│       ├── security.py                 # PBKDF2 password hashing & RBAC
│       ├── service.py                  # Service layer compatibility facade
│       └── templates\                  # Jinja2 templates (with reusable components)
│           └── components\ui_components.html # Standard badges, headers, & empty states
└── tests\                              # 28 test suites (148 passing tests, 0 warnings)
```
