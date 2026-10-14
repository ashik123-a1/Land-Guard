# LandGuard Multimodal Decision Synthesis & Precedence Audit

> [!IMPORTANT]
> **Multimodal Hierarchy Guarantee**:
> In LandGuard, evidentiary signals are synthesized under strict statutory precedence:
> `Cadastral Registry Rules` > `Archival Relational Checks` > `Document OCR Verification` > `CV Anomaly Evidence` > `Supervised ML Risk Score`.

---

## 1. Decision Hierarchy Architecture

```mermaid
flowchart TD
    Ingest["Uploaded Deed & Form Input"] --> OCR["Bilingual OCR & Entity Extraction"]
    OCR --> HIL["Officer Confirmation (Human-in-the-Loop)"]
    HIL --> Reg["Cadastral Registry & Relational Chain Lookup"]
    Reg --> RulesDeterministic Rule Engine
    
    Rules -->|Contradiction Found| CI["CONFIRMED_INCONSISTENCY<br/>(Immediate Hold for Statutory Review)"]
    Rules -->|Archival Record Missing| ME["MISSING_EVIDENCE<br/>(Request Missing Archival Records)"]
    Rules -->|Pending Mutation / Subdivision| RR["REVIEW_REQUIRED<br/>(Officer Administrative Hearing)"]
    
    Rules -->|Rules Clean| MLML Risk Score<br/>& CV Anomaly
    ML -->|Score >= 0.50| RI["RISK_INDICATOR<br/>(Secondary Clerk Screening)"]
    ML -->|Score < 0.50| CLEAR["CLEAR_FOR_STANDARD_PROCESSING<br/>(Proceed with Standard Registration)"]
```

---

## 2. Multimodal Precedence Verification Matrix

Verified across all critical conflict scenarios:

| Conflict Scenario | ML Risk Score | Overall Decision Status | Recommended Administrative Action | Verdict |
| :--- | :---: | :---: | :--- | :---: |
| Precedence A: Statutory Contradiction overrides low ML score | `0.05` | `CONFIRMED_INCONSISTENCY` | `HOLD_FOR_STATUTORY_VERIFICATION: Inspect phys...` | **PASS** |
| Precedence B: Clean registry with high ML score routes to RISK_INDICATOR (never fraud) | `0.88` | `RISK_INDICATOR` | `SECONDARY_SCREENING_RECOMMENDED: Statistical ...` | **PASS** |
| Precedence C: Damaged historical archive with high ML score routes to MISSING_EVIDENCE | `0.94` | `MISSING_EVIDENCE` | `REQUEST_MISSING_RECORDS: Obtain missing histo...` | **PASS** |
| Precedence D: Pending Namzari mutation routes to REVIEW_REQUIRED | `0.40` | `REVIEW_REQUIRED` | `MANUAL_OFFICER_REVIEW: Verify pending Namzari...` | **PASS** |
| Precedence E: Verified conveyance routes to CLEAR_FOR_STANDARD_PROCESSING | `0.02` | `CLEAR_FOR_STANDARD_PROCESSING` | `PROCEED_WITH_STANDARD_REVIEW: No statutory co...` | **PASS** |

---

## 3. Key Safety & Governance Guarantees

1. **Pre-1972 Archival Safety Guarantee**:
   When colonial or pre-liberation archival volumes are damaged or unindexed, the system strictly outputs **`MISSING_EVIDENCE`** (`REQUEST_MISSING_RECORDS`). Even if statistical ML models flag elevated risk due to missing prior citations, the overall category NEVER labels the applicant as fraudulent.

2. **Statistical Model Demotion Guarantee**:
   Supervised ML scores are strictly classified as **`RISK_INDICATOR`**. An elevated ML score in the absence of a confirmed statutory contradiction triggers a secondary screening recommendation (`SECONDARY_SCREENING_RECOMMENDED`), preserving citizen due process.

3. **Computer Vision Forensic Boundary**:
   Visual anomaly scores represent physical document seam irregularity, not statutory fraud. A visual anomaly prompts physical inspection of volume paper originals, preventing automated denial of land rights.
