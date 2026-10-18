<div align="center">

# 🛡️ LandGuard AI
### Statutory Land Record Verification & Title Defense Platform

**LandTech 2026 P3 Track: Fraud & Double-Selling Detection**  
*Autonomous Cadastral Chain Reconstruction (CS ➔ SA ➔ RS ➔ BS) • Bilingual OCR & Tampering Detection • Explainable Risk Scoring • Cryptographic QR Evidence Dossiers*

<br>

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-Risk_Engine-FF6600?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://xgboost.ai)
[![RapidOCR](https://img.shields.io/badge/RapidOCR-Bengali_Vision-7928CA?style=for-the-badge&logo=opencv&logoColor=white)](https://github.com/RapidAI/RapidOCR)
[![SQLite WAL](https://img.shields.io/badge/SQLite_WAL-Persistent_Storage-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Neon PostgreSQL](https://img.shields.io/badge/Neon_Postgres-Standby_Ready-00E599?style=for-the-badge&logo=postgresql&logoColor=black)](https://neon.tech)
[![Tests 277 Passed](https://img.shields.io/badge/Tests-277%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Render Backend](https://img.shields.io/badge/Render-Persistent_Cloud-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com)
[![Vercel Edge](https://img.shields.io/badge/Vercel-Edge_Routing-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![Bilingual](https://img.shields.io/badge/Localization-Bilingual_(EN%20%7C%20বাংলা)-E91E63?style=for-the-badge)](src/landguard_web/localization.py)

<br>

<img src="landguard_preloader_animated.svg" alt="LandGuard AI Intelligent Land Record Verification & Title Defense Interface" width="100%" style="border-radius: 14px; box-shadow: 0 16px 40px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);">

<br>

| 🌐 **Public Live URL** | ⚙️ **Backend Service** | 🗄️ **Primary Database** | 🛡️ **Test Coverage** |
| :---: | :---: | :---: | :---: |
| [landguard.vercel.app](https://landguard.vercel.app) | **Render Linux Container** (`FastAPI + Uvicorn`) | **SQLite WAL** (`/var/data/landguard_operational.db`) | **277 / 277 Passing (100%)** |

</div>

---

## 📑 Table of Contents

- [1. Executive Summary & Purpose](#1-executive-summary--purpose)
- [2. Key Capabilities & Statutory Vectors](#2-key-capabilities--statutory-vectors)
- [3. System Architecture](#3-system-architecture)
- [4. Multimodal AI & Statutory Rules Decision Pipeline](#4-multimodal-ai--statutory-rules-decision-pipeline)
- [5. Cadastral Survey Chain Lineage & Graph Topology Engine](#5-cadastral-survey-chain-lineage--graph-topology-engine)
- [6. End-to-End Verification & QR Journey](#6-end-to-end-verification--qr-journey)
- [7. Database Entity-Relationship Model](#7-database-entity-relationship-model)
- [8. Technology Stack](#8-technology-stack)
- [9. Repository Structure](#9-repository-structure)
- [10. Demonstration Accounts & Evaluation Flow](#10-demonstration-accounts--evaluation-flow)
- [11. Local Setup & Quickstart](#11-local-setup--quickstart)
- [12. Automated Testing & Verification](#12-automated-testing--verification)
- [13. Environment Configuration](#13-environment-configuration)
- [14. Cloud Deployment (Render + Vercel)](#14-cloud-deployment-render--vercel)
- [15. Statutory Disclaimers](#15-statutory-disclaimers)

---

## 1. Executive Summary & Purpose

**LandGuard** is an AI-assisted, statutory evidence-driven land record verification, cadastral topology reconstruction, and complaint investigation platform built for Bangladesh's **LandTech 2026 P3 Track**.

The platform is purpose-engineered to mitigate the four principal vectors of deed manipulation in Bangladesh land administration:

1. ⚡ **Concurrent Double-Selling & Multiple Conveyances** (*Registration Act 1908, Section 47*): Multiple deed registrations executed across different Sub-Registry offices on the exact same Dag/Plot parcel before mutation indexation.
2. 🏛️ **Registration vs. AC Land Mutation Discrepancies** (*State Acquisition and Tenancy Act 1950, Section 143*): Divergence between registered sale deeds and official AC (Land) Upazila Mutation ledgers.
3. 🔍 **Physical Deed Tampering & Altered Dag Numbers**: Detection of physical paste-overs, razor scrapes, and altered digits via Computer Vision seam analysis and HSV seal texture anomalies.
4. 📜 **Ancestral Title Chain Discrepancies & Archival Gaps**: Complete genealogical and survey succession mapping across **CS (Cadastral Survey)** ➔ **SA (State Acquisition)** ➔ **RS (Revisional Survey)** ➔ **BS (Bangladesh Survey)**.

### ⚖️ Non-Negotiable Evidence Hierarchy

$$\Large \text{Deterministic Statutory Predicates} \succ \text{Human Review / Clarification} \succ \text{Supplementary Calibrated ML Risk}$$

> **Evidence Act 1872 Section 45 Adherence**: Machine learning risk scores and computer vision edge heatmaps serve strictly as supplementary decision-support evidence for authorized investigators; they never automatically override statutory deeds or administrative title deeds.

---

## 2. Key Capabilities & Statutory Vectors

<table>
  <tr>
    <td width="50%">
      <h3>🏛️ Dual-Portal Role Architecture</h3>
      <ul>
        <li><strong>Citizen Portal</strong>: Upload deeds, track verification status, submit land disputes, request expedited reviews, and manage digital land identity.</li>
        <li><strong>Investigator Command Center</strong>: Bento-grid analytics, real-time alerts, priority docket queues, official case notes, and SLA tracking.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🧠 Calibrated AI Risk Engine</h3>
      <ul>
        <li><strong>19 Domain Features</strong>: Extracted from chain depth, party continuity, temporal gaps, and mutation records.</li>
        <li><strong>XGBoost 3.x Classifier</strong>: Trained on 2,500 scenarios with probability calibration (Brier score 0.0013) and SHAP feature attribution.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>👁️ Vision & Tamper Detection</h3>
      <ul>
        <li><strong>RapidOCR Engine</strong>: Bilingual text extraction supporting Bengali unicode with complex conjuncts (যুক্তাক্ষর).</li>
        <li><strong>Physical Seam Detector</strong>: Edge-discontinuity, adhesive artifact identification, and official ink seal HSV analysis.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🎙️ Voice Assistant ("Hello Daffodil")</h3>
      <ul>
        <li><strong>Site-Wide Voice Control</strong>: Hands-free navigation and action execution across both English and Bengali.</li>
        <li><strong>Voice Actions</strong>: "Show Dashboard", "Verify Deed", "Open Complaints", "Check Plot 9044".</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🌐 100% Bilingual Localization</h3>
      <ul>
        <li><strong>Instant Language Toggle</strong>: Seamless switching between <strong>বাংলা</strong> and <strong>English</strong>.</li>
        <li><strong>Jinja2 i18n Integration</strong>: Centralized dictionaries with persistent cookie and database preference storage.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🔏 Cryptographic PDF Evidence Dossier</h3>
      <ul>
        <li><strong>ReportLab Generator</strong>: Official court-ready PDF dossier with embedded SHA-256 integrity hash.</li>
        <li><strong>Public QR Verification</strong>: Scannable QR code directing to live public certificate (<code>/verify/public/:id</code>).</li>
      </ul>
    </td>
  </tr>
</table>

---

## 3. System Architecture

LandGuard utilizes a hybrid cloud architecture combining **Render's persistent backend compute** with **Vercel's global edge network**.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#38bdf8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e1b4b',
    'fontFamily': 'Inter, system-ui, sans-serif'
  }
}}%%
flowchart TD
    classDef client fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#ffffff;
    classDef edgeGateway fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef backend fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff;
    classDef aiEngine fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef storage fill:#3b0764,stroke:#d8b4fe,stroke-width:2px,color:#ffffff;
    classDef standby fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#ffffff;

    subgraph ClientLayer["🖥️ Client & Device Layer"]
        CitizenBrowser["Citizen Browser / Mobile Device"]:::client
        RegistrarDesktop["Sub-Registrar / Investigator Desktop"]:::client
        PublicScanner["Smartphone Scanning Authenticity QR Code"]:::client
    end

    subgraph VercelEdge["⚡ Vercel Global Edge (Public Gateway)"]
        VercelDNS["🌐 https://landguard.vercel.app"]:::edgeGateway
        VercelProxy["🔀 Vercel Edge Proxy / Rewrites (vercel.json)"]:::edgeGateway
        VercelDNS --> VercelProxy
    end

    subgraph RenderBackend["🚀 Render Cloud Service (Linux Container)"]
        RenderLB["🛡️ Render TLS Termination & Load Balancer"]:::backend
        UvicornASGI["⚙️ Uvicorn ASGI Server (0.0.0.0:$PORT)"]:::backend
        FastAPIApp["⚡ FastAPI Modular Application (src.landguard_web.app)"]:::backend
        DomainServices["📦 Domain Services (Auth, Cases, Verification, Reports, Voice)"]:::backend
        Repositories["🗄️ Repository Facade (BaseRepository, SQLite WAL Engine)"]:::backend
        XGBoostEngine["🧠 XGBoost Risk Model & RapidOCR ONNX Engine"]:::aiEngine

        RenderLB --> UvicornASGI
        UvicornASGI --> FastAPIApp
        FastAPIApp --> DomainServices
        DomainServices --> Repositories
        DomainServices --> XGBoostEngine
    end

    subgraph RenderStorage["💾 Render Attached Persistent Disk (/var/data)"]
        OperationalDB[("📁 landguard_operational.db (WAL Mode, Foreign Keys ON)")]:::storage
        UploadsStorage[("📂 uploads/deeds (SHA-256 Masked Document Store)")]:::storage
    end

    subgraph StandbyDatabase["☁️ Standby Cloud Database"]
        NeonPostgres[("🐘 Neon Serverless PostgreSQL (Standby via DATABASE_URL)")]:::standby
    end

    CitizenBrowser -->|"HTTPS Requests"| VercelDNS
    RegistrarDesktop -->|"HTTPS Requests"| VercelDNS
    PublicScanner -->|"Direct QR Inspection (/verify/public/:id)"| VercelDNS

    VercelProxy -->|"Transparent Proxy Rewrite: /(.*) -> Render"| RenderLB
    Repositories -->|"Read / Write Operations (LANDGUARD_DB_PATH)"| OperationalDB
    DomainServices -->|"Secure Document Ingestion (LANDGUARD_UPLOADS_PATH)"| UploadsStorage
    Repositories -.->|"Standby Connection (when DATABASE_BACKEND=POSTGRESQL)"| NeonPostgres

    style ClientLayer fill:#0f172a,stroke:#6366f1,stroke-width:2px,stroke-dasharray: 5 5,color:#c7d2fe
    style VercelEdge fill:#082f49,stroke:#0ea5e9,stroke-width:2px,color:#bae6fd
    style RenderBackend fill:#022c22,stroke:#10b981,stroke-width:2px,color:#a7f3d0
    style RenderStorage fill:#2e1065,stroke:#a855f7,stroke-width:2px,color:#e9d5ff
    style StandbyDatabase fill:#451a03,stroke:#f59e0b,stroke-width:2px,stroke-dasharray: 4 4,color:#fde68a
```

### 🔒 Architectural Guarantees

- **Unified Domain Experience**: The entire application, static assets, login sessions, and forms are exposed seamlessly under the public Vercel domain (`https://landguard.vercel.app`).
- **Complete Data Persistence**: Render mounts an attached persistent SSD disk at `/var/data`. The operational SQLite database (`/var/data/landguard_operational.db`) survives service restarts, deployments, and rebuilds.
- **Zero-Overwrite Deployment Guard**: The initialization guard (`scripts/init_persistent_db.py`) automatically seeds the persistent disk on first boot, and strictly skips re-initialization on subsequent deployments, preserving all live user data and complaints.

---

## 4. Multimodal AI & Statutory Rules Decision Pipeline

The deed verification engine runs a dual-track multimodal inspection combining deterministic statutory predicates (Registration Act 1908, SAT Act 1950) with supplementary machine learning risk scoring:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#38bdf8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e1b4b',
    'fontFamily': 'Inter, system-ui, sans-serif'
  }
}}%%
flowchart TD
    classDef inputNode fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef visionNode fill:#3b0764,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef ruleNode fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff;
    classDef mlNode fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#ffffff;
    classDef matrixNode fill:#451a03,stroke:#f59e0b,stroke-width:2px,color:#ffffff;
    classDef outputNode fill:#022c22,stroke:#10b981,stroke-width:2px,color:#ffffff;

    subgraph TierInput["📥 1. Ingestion Layer"]
        DeedUpload["📄 Deed Document (.pdf / .png)<br/>SHA-256 Digest Hashing"]:::inputNode
        ParcelMeta["📋 Cadastral Metadata<br/>(Dag, Khatian, Mouza, Area, Parties)"]:::inputNode
    end

    subgraph TierVision["👁️ 2. Computer Vision & Multimodal Extraction"]
        RapidOCR["🔤 RapidOCR Engine<br/>HarfBuzz Bengali Script Shaping & Key-Value Extraction"]:::visionNode
        SeamDetect["🔍 OpenCV Seam & Tamper Detector<br/>Laplacian Edge Variance & Physical Alteration Heatmap"]:::visionNode
        SealDetect["💮 HSV Seal & Signature Verifier<br/>Circular Hough Transform & Color Morphology"]:::visionNode
    end

    subgraph TierReasoning["⚖️ 3. Dual-Track Analysis Engine"]
        subgraph StatutoryEngine["🏛️ Deterministic Statutory Rules (R-01 to R-10)"]
            R01["R-01: Conflicting Double Disposition (Reg. Act 1908 §47)"]:::ruleNode
            R02["R-02: Seller Not Titleholder in BS Record"]:::ruleNode
            R03["R-03: Area Exceeds Khatian Quota (SAT Act 1950)"]:::ruleNode
            R04["R-04: Unverified Mutation / Missing AC Land Order"]:::ruleNode
            R05["R-05: Unindexed Pre-1972 Archival Gap"]:::ruleNode
        end
        subgraph MLEngine["🧠 Supervised Machine Learning"]
            XGBoost["⚡ Frozen XGBoost Classifier<br/>19 Cadastral & Temporal Features<br/>Calibrated Risk Score (Brier: 0.0013)"]:::mlNode
        end
    end

    subgraph TierSynthesis["🏛️ 4. Statutory Precedence Synthesis Hierarchy"]
        PrecedenceMatrix{"Evidence Act 1872 §45 Synthesis:<br/>Do Statutory Violations or Archival Gaps Exist?"}:::matrixNode
        VerdictIncons["🚨 CONFIRMED_INCONSISTENCY<br/>(Statutory Violation Overrides ML)"]:::matrixNode
        VerdictMissing["⚠️ MISSING_EVIDENCE<br/>(Archival Absence Overrides ML)"]:::matrixNode
        VerdictReview["🕒 REVIEW_REQUIRED<br/>(Pending Mutation / Revenue Hearing)"]:::matrixNode
        VerdictClear["✅ CLEAR_FOR_STANDARD_PROCESSING<br/>(Valid Title Conveyance)"]:::matrixNode
    end

    subgraph TierOutput["📑 5. Cryptographic Evidence Output"]
        PDFReport["📜 Court-Ready PDF Evidence Dossier (ReportLab)"]:::outputNode
        DynamicQR["📱 Dynamic Verification QR Code (Public Redaction)"]:::outputNode
        AuditTrail["🔒 Immutable SHA-256 Audit Trail Entry"]:::outputNode
    end

    DeedUpload --> RapidOCR & SeamDetect & SealDetect
    ParcelMeta --> StatutoryEngine & XGBoost
    RapidOCR & SeamDetect & SealDetect --> StatutoryEngine & XGBoost
    StatutoryEngine --> PrecedenceMatrix
    XGBoost --> PrecedenceMatrix
    PrecedenceMatrix --> VerdictIncons & VerdictMissing & VerdictReview & VerdictClear
    VerdictIncons & VerdictMissing & VerdictReview & VerdictClear --> PDFReport
    PDFReport --> DynamicQR --> AuditTrail

    style TierInput fill:#090d16,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    style TierVision fill:#1c102a,stroke:#a855f7,stroke-width:2px,color:#f3e8ff
    style TierReasoning fill:#06221c,stroke:#10b981,stroke-width:2px,color:#d1fae5
    style StatutoryEngine fill:#022c22,stroke:#059669,stroke-width:1.5px,color:#a7f3d0
    style MLEngine fill:#1e1b4b,stroke:#6366f1,stroke-width:1.5px,color:#e0e7ff
    style TierSynthesis fill:#261605,stroke:#f59e0b,stroke-width:2px,color:#fef3c7
    style TierOutput fill:#022c22,stroke:#34d399,stroke-width:2px,color:#ecfdf5
```

---

## 5. Cadastral Survey Chain Lineage & Graph Topology Engine

LandGuard models Bangladesh's multi-generational land records as a Directed Acyclic Graph (DAG) across the four canonical survey epochs:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#38bdf8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e1b4b',
    'fontFamily': 'Inter, system-ui, sans-serif'
  }
}}%%
flowchart TD
    classDef csNode fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#ffffff;
    classDef saNode fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef rsNode fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ffffff;
    classDef bsNode fill:#3b0764,stroke:#c084fc,stroke-width:2px,color:#ffffff;
    classDef engineNode fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#ffffff;
    classDef simNode fill:#451a03,stroke:#f59e0b,stroke-width:2px,color:#ffffff;

    subgraph SurveyChain["📜 Historical Cadastral Lineage Chronology (Bangladesh)"]
        subgraph CS_Tier["🏛️ CS Survey (~1920) • Cadastral Survey"]
            CS_Plot["Parent Dag Plot 101<br/>Khatian 42 • Total Area: 100 Decimals<br/>Original British Bengal Cadastral Baseline"]:::csNode
        end

        subgraph SA_Tier["🏛️ SA Survey (~1956) • State Acquisition"]
            SA_Plot1["Subdivided Dag 101/1<br/>Khatian 78 • Area: 60 Decimals"]:::saNode
            SA_Plot2["Subdivided Dag 101/2<br/>Khatian 79 • Area: 40 Decimals"]:::saNode
        end

        subgraph RS_Tier["🏛️ RS Survey (~1982) • Revisional Survey"]
            RS_Plot1["Daughter Dag 305<br/>Area: 35 Decimals"]:::rsNode
            RS_Plot2["Daughter Dag 306<br/>Area: 25 Decimals"]:::rsNode
            RS_Plot3["Daughter Dag 307<br/>Area: 40 Decimals"]:::rsNode
        end

        subgraph BS_Tier["🏛️ BS / City Survey (~2000+) • Active Registry"]
            BS_Plot1["Active BS Dag 5012<br/>Area: 20 Decimals (Title Valid)"]:::bsNode
            BS_Plot2["Active BS Dag 5013<br/>Area: 15 Decimals (Disputed)"]:::bsNode
            BS_Plot3["Active BS Dag 5014<br/>Area: 40 Decimals (Intact)"]:::bsNode
        end

        CS_Plot -->|"SAT Act 1950 Partition"| SA_Plot1 & SA_Plot2
        SA_Plot1 -->|"Revisional Subdivision"| RS_Plot1 & RS_Plot2
        SA_Plot2 -->|"Revisional Succession"| RS_Plot3
        RS_Plot1 -->|"BS Modern Mutation"| BS_Plot1
        RS_Plot2 -->|"Conflicting Mutation"| BS_Plot2
        RS_Plot3 -->|"Unbroken Inheritance"| BS_Plot3
    end

    subgraph TopologyEngine["🌐 LandGuard Cadastral Topology Graph Engine (NetworkX)"]
        DirectedGraph["Directed Acyclic Graph (DAG)<br/>Nodes: Parcels & Khatians | Edges: Subdivisions & Mutations"]:::engineNode
        ChainValidator["🔍 Survey Chain Traversal<br/>Validates complete genealogy back to CS baseline"]:::engineNode
        AreaIntegrity["📐 Area Conservation Auditing<br/>Ensures Sum(Daughter Areas) &le; Parent Area"]:::engineNode

        DirectedGraph --> ChainValidator & AreaIntegrity
    end

    subgraph SimulationSuite["🧪 Simulation & Fraud Discovery Services"]
        WhatIfSim["🧪 Zero-Mutation What-If Simulator<br/>(POST /api/simulator/what-if)<br/>Simulates land subdivision without mutating operational DB"]:::simNode
        PatternDetector["🚨 Cross-Parcel Fraud Pattern Discovery<br/>(GET /api/parcels/:id/patterns)<br/>Detects fraudulent sellers disposing fractional rights across multiple dags"]:::simNode
    end

    BS_Tier --> DirectedGraph
    TopologyEngine --> SimulationSuite

    style SurveyChain fill:#090d16,stroke:#64748b,stroke-width:2px,color:#e2e8f0
    style CS_Tier fill:#1e1b4b,stroke:#6366f1,stroke-width:1.5px,color:#c7d2fe
    style SA_Tier fill:#082f49,stroke:#0ea5e9,stroke-width:1.5px,color:#bae6fd
    style RS_Tier fill:#022c22,stroke:#10b981,stroke-width:1.5px,color:#a7f3d0
    style BS_Tier fill:#2e1065,stroke:#a855f7,stroke-width:1.5px,color:#e9d5ff
    style TopologyEngine fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#e0f2fe
    style SimulationSuite fill:#261605,stroke:#f59e0b,stroke-width:2px,color:#fef3c7
```

---

## 6. End-to-End Verification & QR Journey

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#0f172a',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#38bdf8',
    'actorBkg': '#1e1b4b',
    'actorBorder': '#818cf8',
    'actorTextColor': '#ffffff',
    'actorLineColor': '#6366f1',
    'signalColor': '#38bdf8',
    'signalTextColor': '#e2e8f0',
    'labelBoxBkgColor': '#0c4a6e',
    'labelBoxBorderColor': '#38bdf8',
    'labelTextColor': '#ffffff',
    'loopTextColor': '#ffffff',
    'noteBkgColor': '#1e1b4b',
    'noteBorderColor': '#c084fc',
    'noteTextColor': '#e9d5ff',
    'activationBkgColor': '#064e3b',
    'activationBorderColor': '#34d399',
    'sequenceNumberColor': '#ffffff',
    'fontFamily': 'Inter, system-ui, sans-serif'
  }
}}%%
sequenceDiagram
    autonumber
    actor Citizen as 👤 Citizen / Landholder
    actor Registrar as 👨‍💼 Sub-Registrar / Admin
    participant WebApp as 💻 LandGuard Web UI (Vercel)
    participant API as 🚀 FastAPI Backend (Render)
    participant OCR as 👁️ RapidOCR & CV Engine
    participant DB as 🗄️ SQLite DB (/var/data)
    actor PublicUser as 📱 Third-Party Buyer / Verifier

    Citizen->>WebApp: Upload Deed Image (.png / .pdf)
    WebApp->>API: POST /api/upload (Multipart)
    API->>OCR: Run Bilingual OCR & CV Tampering Detection
    OCR-->>API: Extracted Fields (Plot, Khatian, Area, Parties) + Edge Heatmap
    API->>DB: Store Document & SHA-256 Hash
    API-->>WebApp: Return Extracted Fields with Uncertainty Badges

    Citizen->>WebApp: Confirm Fields & Submit Statutory Verification
    WebApp->>API: POST /api/verify
    API->>DB: Query Cadastral Chain (CS -> SA -> RS -> BS) & Active Mutations
    API->>API: Evaluate Statutory Rules (R-01 to R-10) + XGBoost Risk
    API->>DB: Persist Verification Run (Verdict, SHA-256, Rule Findings)
    API-->>WebApp: Render Verification Dossier

    Registrar->>WebApp: Review Dossier & Issue Determination
    WebApp->>API: POST /api/verifications/:id/decision
    API->>DB: Update Official Registrar Determination & Audit Event

    Registrar->>WebApp: Request Official Evidence Dossier Certificate (PDF)
    WebApp->>API: GET /api/reports/:id/pdf
    API->>API: Compute SHA-256 Hash & Generate Authenticity QR Code
    Note over API: QR Code links to canonical PUBLIC_BASE_URL/verify/public/:id
    API-->>Registrar: Download Printable Cryptographic PDF Dossier

    PublicUser->>PublicScanner: Scan QR Code on Printed Certificate
    PublicScanner->>WebApp: GET /verify/public/:id
    WebApp->>API: Fetch Dossier Details
    API-->>WebApp: Return Dossier Metadata (Masked PII, Official Seal)
    WebApp-->>PublicUser: Display Statutory Integrity Proof & Live Verdict
```

---

## 7. Database Entity-Relationship Model

The operational database maintains strict foreign-key constraints and relational integrity across all domain entities:

```mermaid
erDiagram
    USERS ||--o{ COMPLAINTS : submits
    USERS ||--o{ CASES : manages
    USERS ||--o{ VERIFICATION_RUNS : executes
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_EVENTS : triggers

    COMPLAINTS ||--o| CASES : escalated_to
    CASES ||--o{ CASE_NOTES : contains
    CASES ||--o| VERIFICATION_RUNS : references
    VERIFICATION_RUNS ||--o| DOCUMENTS : analyzes
    VERIFICATION_RUNS ||--o| PARCELS : verifies

    USERS {
        string user_id PK
        string email UK
        string password_hash
        string full_name
        string role "CITIZEN | INVESTIGATOR | ADMIN"
        datetime created_at
    }

    COMPLAINTS {
        string complaint_id PK
        string citizen_id FK
        string dispute_type
        string parcel_id
        text narrative
        string priority "CRITICAL | HIGH | NORMAL | LOW"
        string status "SUBMITTED | UNDER_INVESTIGATION | RESOLVED"
        boolean expedite_requested
        text expedite_reason
        datetime created_at
    }

    CASES {
        string case_id PK
        string complaint_id FK
        string assigned_officer_id FK
        string docket_number UK
        string priority
        string status "OPEN | UNDER_REVIEW | RESOLVED | CLOSED"
        datetime sla_deadline
        datetime created_at
    }

    CASE_NOTES {
        string note_id PK
        string case_id FK
        string author_id FK
        text content
        datetime created_at
    }

    VERIFICATION_RUNS {
        string verification_id PK
        string initiated_by FK
        string parcel_id FK
        string document_id FK
        string final_verdict "VALID | DISPUTED | SUSPICIOUS | REJECTED"
        float ml_risk_score
        string sha256_hash
        string report_status "VALID | DISPUTED | REVOKED"
        datetime created_at
    }

    DOCUMENTS {
        string document_id PK
        string uploaded_by FK
        string filename
        string storage_path
        string sha256_hash
        string mime_type
        datetime created_at
    }

    PARCELS {
        string parcel_id PK
        string dag_plot_number
        string khatian_number
        string mouza_name
        string upazila
        string district
        float declared_area_decimals
    }

    NOTIFICATIONS {
        string notification_id PK
        string user_id FK
        string title
        text message
        boolean is_read
        datetime created_at
    }

    AUDIT_EVENTS {
        string event_id PK
        string user_id FK
        string action_type
        string resource_id
        text diff_payload
        string ip_address
        datetime created_at
    }
```

---

## 8. Technology Stack

| Layer | Component | Technology & Specification |
| :--- | :--- | :--- |
| **Edge Routing & Proxy** | Vercel Edge Network | Transparent reverse-proxy rewrites via `vercel.json` |
| **Backend Application** | FastAPI 0.110+ | Asynchronous ASGI RESTful API & Server-Side Rendered (SSR) routes |
| **ASGI Web Server** | Uvicorn 0.28+ | High-performance ASGI server with forwarded headers enabled |
| **Templating & UI** | Jinja2 3.1+ & TailwindCSS | Bento-grid responsive layout with bilingual i18n support |
| **Primary Operational DB** | SQLite 3 (WAL Mode) | Persistent transactional disk storage on Render persistent disk (`/var/data`) |
| **Standby Cloud DB** | Neon Serverless PostgreSQL | Serverless PostgreSQL driver (`psycopg2-binary`) on standby |
| **Machine Learning** | XGBoost 3.x & Scikit-learn | 19 domain features, calibrated risk score, Brier score 0.0013 |
| **Vision & OCR** | RapidOCR, OpenCV, PyMuPDF | Text line detection, HarfBuzz Bengali shaping, seam artifact analysis |
| **Cryptographic Reports** | ReportLab & Qrcode | Court-ready PDF dossiers with embedded SHA-256 hash & dynamic QR links |
| **Cadastral Maps** | Leaflet.js & GeoJSON | Interactive cadastral topology and plot boundary visualizations |

---

## 9. Repository Structure

```
.
├── render.yaml                          # Render cloud service & persistent disk blueprint
├── vercel.json                          # Vercel domain reverse-proxy configuration
├── requirements.txt                     # Production Python dependencies (Linux/Render ready)
├── pyproject.toml                       # Python package specification and pytest configuration
├── .env.example                         # Environment configuration template with safe placeholders
├── .gitignore                           # Git ignore specification protecting operational databases
├── README.md                            # Comprehensive system documentation & deployment guide
├── TESTS.md                             # Automated test suite specification & coverage metrics
├── landguard_preloader_animated.svg     # Animated cyber radar & statutory verification SVG
├── landguard_preloader_animated.gif     # High-definition animated preview asset
├── docs/                                # Technical system specifications & architectural blueprints
│   ├── ARCHITECTURE.md                  # Comprehensive architecture & system design document
│   └── landguard_preloader_animated.svg # Vector assets and design references
├── scripts/
│   ├── init_persistent_db.py           # Idempotent persistent volume initialization & seeding guard
│   ├── generate_all_markdown_and_pdfs.py # Batch dossier generation utility
│   ├── generate_favicon.py             # Favicon asset generator
│   └── test_selenium_hands_free.py     # End-to-end automated browser test script
├── data/
│   ├── landguard_operational.db         # Canonical seed database (399 complaints, 120 cases)
│   ├── fixtures/demo_manifest.json     # Demonstration parcel and scenario fixtures
│   ├── manifests/dataset_manifest.json  # Comprehensive dataset metadata
│   └── targeted_expansion/             # High-resolution benchmark deed images and annotations
├── models/
│   ├── xgboost_risk_model.joblib        # Pre-trained frozen XGBoost title risk classifier
│   └── model_metadata.json              # Model hyperparameters, feature names, and ROC metrics
├── src/
│   ├── landguard_ai/                    # Multi-modal grievance claim extraction & grounding
│   ├── landguard_data/                  # Database connections and domain repositories
│   │   ├── database.py                  # Primary database manager and repository facade
│   │   └── repositories/               # Specialized repositories (Cases, Complaints, Users, etc.)
│   ├── landguard_models/                # Feature engineering, XGBoost, and statutory rules
│   │   ├── verification_rules.py        # Statutory rules engine (R-01 through R-10)
│   │   └── explainable_risk.py          # SHAP/Tree-based feature importance breakdown
│   ├── landguard_vision/                # Bilingual OCR and computer vision seam analysis
│   ├── landguard_reports/               # Tamper-evident PDF and QR code generators
│   ├── landguard_services/              # Domain business logic services (Auth, Complaints, Cases)
│   └── landguard_web/                   # FastAPI application presentation layer
│       ├── app.py                       # Main ASGI application entry point
│       ├── dependencies.py              # Authentication dependencies and RBAC guards
│       ├── localization.py              # Bilingual localization engine (English / বাংলা)
│       ├── rate_limiter.py              # In-memory sliding-window request throttling
│       ├── routers/                     # Domain-specific route controllers
│       ├── static/                      # Static CSS, JavaScript, and branding assets
│       └── templates/                   # Jinja2 templates (Public, Citizen, Admin portals)
└── tests/                               # Comprehensive automated test suite (277 passing tests)
    ├── conftest.py                      # Test database isolation fixture (protects operational DB)
    ├── test_web_app.py                  # Core web application and endpoint tests
    ├── test_localization.py             # Bilingual UI and PDF rendering tests
    ├── test_security_authorization.py   # RBAC and IDOR security verification
    └── test_sqlite_persistence.py       # Persistence and volume restart tests
```

---

## 10. Demonstration Accounts & Evaluation Flow

For rapid evaluation and judging, three pre-configured demonstration accounts are available with one-click access on the login screen (`/login`):

| Role | Email | Password | Primary Demonstration Capabilities |
| :--- | :--- | :--- | :--- |
| **Citizen / Landholder** | `citizen@landguard.gov.bd` | `Citizen@123` | Upload deeds, inspect cadastral records, file formal complaints, request expedited review, switch English/বাংলা. |
| **Land Investigator** | `investigator@landguard.gov.bd` | `Investigator@123` | Inspect rule violations, evaluate CV seam anomalies, review timeline evidence, draft official investigation findings. |
| **Sub-Registrar (Admin)** | `admin@landguard.gov.bd` | `Admin@123` | Full statutory governance, approve expedited reviews, issue determination decisions, download cryptographic PDF dossiers. |

### ⏱️ Recommended 5-Minute Evaluation Flow:

1. **Landing & Identity**: Navigate to `/` to view the animated national map and mission brief. Click **Citizen Portal** or **Login** to enter.
2. **Citizen Deed Verification**: In `/user/verify`, upload a sample deed from `data/targeted_expansion/images/IMG-EXP-0001.png`. Review the automated OCR field extraction and submit for statutory verification.
3. **Dispute Filing & Expedited Review**: In `/user/complaints/new`, submit a land grievance and check **Request Expedited Review** with statutory urgency grounds.
4. **Admin Docket & Expedited Approval**: Log out and log in as **Admin**. On `/admin/dashboard`, review the incoming expedited queue and approve the request with one click.
5. **Official Evidence Dossier & QR Code**: In `/admin/verifications`, open the verified dossier, click **Download Dossier (PDF)**, and scan the printed QR code with a smartphone camera to inspect the live public verification certificate (`/verify/public/:id`).

---

## 11. Local Setup & Quickstart

### Prerequisites
- **Python 3.10+** (Python 3.11 recommended)
- **Git**

### Installation

```bash
# 1. Clone repository
git clone https://github.com/ashik123-a1/Land-Gurd.git
cd Land-Gurd

# 2. Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment specification
cp .env.example .env

# 5. Initialize operational database
python scripts/init_persistent_db.py

# 6. Launch development server
uvicorn src.landguard_web.app:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

---

## 12. Automated Testing & Verification

LandGuard features a **strict database isolation harness** (`tests/conftest.py`). Automated tests never touch or mutate the operational database. Each test session creates a disposable temporary SQLite clone via SQLite's online backup API:

```bash
# Run the complete test suite (277 tests)
pytest -q

# Run specific domain test suites
pytest tests/test_web_app.py tests/test_localization.py
pytest tests/test_security_authorization.py tests/test_security_remediation.py
pytest tests/test_sqlite_persistence.py tests/test_database_isolation.py
```

### ✅ Test Suite Status
- **Total Test Cases**: 277
- **Passing**: 277 (100%)
- **Failing**: 0
- **Execution Time**: ~75 seconds

---

## 13. Environment Configuration

Configure these environment variables in your local `.env` file or in your cloud dashboard:

| Variable | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Yes | `production` | Runtime mode (`production` activates secure cookies and strict headers). |
| `PORT` | Auto | `8000` | Port for ASGI binding (assigned by host). |
| `HOST` | No | `0.0.0.0` | Host interface for network binding. |
| `DATABASE_BACKEND` | Yes | `SQLITE` | Active database engine. Must remain `SQLITE` for primary operations. |
| `LANDGUARD_DB_PATH` | Yes | `/var/data/landguard_operational.db` | Absolute path to SQLite operational database on persistent disk. |
| `LANDGUARD_UPLOADS_PATH`| Yes | `/var/data/uploads` | Directory for ingested deed uploads on persistent disk. |
| `LANDGUARD_BASE_URL` | Yes | `https://landguard.vercel.app` | Canonical public URL used to construct dynamic QR code inspection links. |
| `ALLOWED_ORIGINS` | Yes | `https://landguard.vercel.app,http://localhost:8000` | Authorized CORS origins. |
| `ALLOW_DEMO_LOGIN_IN_PROD` | No | `true` | Enables one-click demo credentials for evaluators. |
| `DATABASE_URL` | No | `postgresql://...` | Standby Neon PostgreSQL connection string. |

---

## 14. Cloud Deployment (Render + Vercel)

### A. Backend Deployment on Render
1. In Render Dashboard, click **New &rarr; Blueprint** and select this repository. Render automatically reads `render.yaml`.
2. A 1 GB persistent SSD disk mounted at `/var/data` is automatically provisioned.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `python scripts/init_persistent_db.py && uvicorn src.landguard_web.app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`.

### B. Frontend Deployment on Vercel
1. In Vercel Dashboard, import this repository.
2. Select framework preset **Other** (no build step needed).
3. Ensure `vercel.json` routes all requests to your active Render service:
   ```json
   {
     "version": 2,
     "name": "landguard-frontend-proxy",
     "rewrites": [
       {
         "source": "/(.*)",
         "destination": "https://<your-render-service>.onrender.com/$1"
       }
     ]
   }
   ```
4. Deploy and verify that the public URL loads seamlessly.

---

## 15. Statutory Disclaimers

> **LEGAL NOTICE**: LandGuard was developed as an advanced scientific benchmark and decision-support prototype for the LandTech 2026 competition.  
> 1. All citizen identities, national ID (NID) numbers, mouza cadastral records, and deed parchment images are synthetically generated for benchmark evaluation.  
> 2. Pursuant to the **Registration Act 1908**, **State Acquisition and Tenancy Act 1950**, and **Evidence Act 1872**, algorithmic outputs constitute rebuttable decision-support evidence and do not replace physical title investigation by authorized land registry officials or judicial decree.

---

<div align="center">
  <sub>LandGuard AI • LandTech 2026 P3 Fraud & Double-Selling Track • Developed with ❤️ for Land Administration Modernization in Bangladesh</sub>
</div>
