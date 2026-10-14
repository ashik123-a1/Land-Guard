# LandGuard Master AI/Data Quality, Validation & Acceptance Audit

> [!IMPORTANT]
> **Authoritative Audit Verdict: ACCEPT WITH GOVERNANCE LIMITATIONS**
> The LandGuard AI, synthetic dataset, OCR, computer vision, deterministic rule engine, and web demonstration stack have undergone rigorous empirical verification, adversarial stress testing, and artifact freezing. All models, metrics, and evidence tables are physically verified and reproduced from source artifacts.

---

## 1. Executive Summary & Audit Scorecard

| Audit Domain | Primary Verification Standard | Evaluated Target | Measured Result | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **Dataset Integrity** | 100% schema compliance, 0 referential linkage errors | 2,600 records | **100% Valid (0 errors)** | PASS |
| **Image Watermarks & Hashes** | SHA-256 match & mandatory synthetic watermark | 600 scans | **600 / 600 (100%)** | PASS |
| **Data Partitioning & Leakage** | Group-disjoint splits (Cohort / Parcel / Seller) | 4 Group Keys | **0% Leakage across splits** | PASS |
| **Ablation Transparency** | Incremental value of features across 6 regimes | 6 Regimes | **Evaluated on held-out test** | PASS |
| **Supervised ML Model** | Authoritative XGBoost Risk Benchmark ($n=500$) | Test F1 $\ge 0.95$ | **F1: 0.9985, Acc: 0.9980** | PASS |
| **Model Calibration** | Expected Calibration Error (ECE) & Brier Score | ECE $\le 0.05$ | **ECE: 0.0110, Brier: 0.0013** | PASS |
| **Model Freeze & Persistence** | Serialized `.joblib` + SHA-256 metadata descriptor | Persistent file | **Frozen to disk (SHA-256 verified)** | PASS |
| **OCR Document Parsing** | Multimodal character & legal field extraction | Field Acc $\ge 0.85$ | **Exact Field Match: 88.89%** | PASS |
| **Computer Vision Detector** | Clean FPR $\le 0.05$, Altered Recall $\ge 0.90$ | 6 Mechanisms | **Clean FPR: 2.22%, Recall: 93.33%** | PASS |
| **Statutory Rule Engine** | 100% Truth table compliance across 4 categories | 16 Test Cases | **100% Pass (0 semantic faults)** | PASS |
| **Multimodal Precedence** | Rules override ML; Missing archives $\rightarrow$ `MISSING_EVIDENCE` | 5 Scenarios | **100% Precedence Compliance** | PASS |
| **Boundary & Stress Hardening**| Zero-division, calendar edge dates, SQL injection | 26 Stress Tests | **100% Pass (197.4 req/sec)** | PASS |
| **Test Suite Stability** | Unit, integration, and UI test suite passing | Pytest Suite | **52 / 52 Passed (2.86s)** | PASS |

---

## 2. Dataset & Split Disjointness Verification

All evaluations are grounded in the verified canonical LandGuard dataset:
- **Canonical Structured Records**: 2,500 scenarios (`data/full/records/canonical_records.json`, SHA-256: `24b1bee2a3cb27a7...`)
- **Targeted Expansion Records**: 100 scenarios (`data/targeted_expansion/records/targeted_records.json`)
- **Document Images**: 600 synthetic documents across 15 degradation regimes (`data/full/images/`)
- **Partitioning Method**: Grouped by `template_cohort` ($n=25$ cohorts):
  - **Train Partition**: 17 cohorts (1,700 records, 420 images)
  - **Validation Partition**: 3 cohorts (300 records, 90 images)
  - **Held-Out Test Partition**: 5 cohorts (500 records, 90 images)
- **Disjointness Audit**: Zero overlap across train/val/test splits in `template_cohort`, `parcel_id`, `primary_seller_id`, and `scenario_id`.
- **Target Leakage Audit**: All 15 simulator-only and oracle shortcut keys strictly banned and validated absent from feature pipelines.

---

## 3. Six-Regime Feature Ablation Summary

Evaluated on the held-out test cohort ($n=500$):

| Regime | Model Architecture | Features Included | Accuracy | Precision | Recall | F1 Score | Brier Score | ECE |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | Majority Class Dummy | None (Prior mode) | 0.6640 | 0.6640 | 1.0000 | 0.7981 | 0.3360 | 0.3360 |
| **2** | Logistic Regression | 15 Registry Features | 0.8960 | 0.9412 | 0.9127 | 0.9261 | 0.0762 | 0.0734 |
| **3** | Random Forest | 15 Registry Features | 0.9280 | 0.9576 | 0.9367 | 0.9472 | 0.0581 | 0.0520 |
| **4** | XGBoost Benchmark | 15 Registry Features | 0.9240 | 0.9634 | 0.9277 | 0.9459 | 0.0554 | 0.0489 |
| **5** | XGBoost Benchmark | Registry + 2 OCR Features | 0.9220 | 0.9693 | 0.9157 | 0.9399 | 0.0420 | 0.0395 |
| **6** | XGBoost Multimodal | Registry + OCR + 2 CV Features | **0.9980** | **0.9970** | **1.0000** | **0.9985** | **0.0013** | **0.0110** |

---

## 4. Authoritative Supervised ML Benchmark

- **Frozen Binary Artifact**: [`models/xgboost_risk_model.joblib`](file:///F:/land%20gurd/models/xgboost_risk_model.joblib)
- **Artifact SHA-256**: `af74a704ca2e7d9fb9b6bc0bd0731b4cc504a464f32d8c5f219adb878b506d95`
- **Metadata Specification**: [`models/model_metadata.json`](file:///F:/land%20gurd/models/model_metadata.json)
- **Held-Out Test Set Performance ($n=500$)**:
  - Accuracy: **0.9980**
  - Precision: **0.9970**
  - Recall: **1.0000**
  - F1 Score: **0.9985**
  - ROC-AUC: **1.0000**
  - PR-AUC: **1.0000**
  - Brier Score: **0.0013**
  - Expected Calibration Error (ECE): **0.0110**
  - Confusion Matrix: $TN=167, FP=1, FN=0, TP=332$
- **Failure Analysis**: Exactly 1 false positive out of 500 test cases (`SCN-F78C845A`, Legitimate Inheritance, prob=0.6516). Because deterministic statutory rules confirmed no inconsistencies, the system classified it as `CLEAR_FOR_STANDARD_PROCESSING`, proving the fail-safe nature of rule precedence.

---

## 5. Multimodal Vision & OCR Robustness

### 5.1 Bilingual OCR Engine (`n=90` Held-Out Test Scans)
- Overall CER: **0.3970** across 15 physical and mobile capture degradations (English subset: **0.3816**, Bangla subset: **0.4396**).
- Downstream Legal Field Exact Match Rate: **88.89%** (160 / 180 fields matched exactly).
  - `deed_number`: 24 / 24 (100.0%)
  - `dag_plot_number`: 77 / 90 (85.6%)
  - `khatian_number`: 16 / 19 (84.2%)
  - `transferred_area_decimal`: 43 / 47 (91.5%)
- Downstream Field Extraction F1: **0.9169**

### 5.2 Forensic Computer Vision Anomaly Detector
- Evaluated on 90 un-tampered degraded scans and 90 controlled altered documents across all 6 mechanisms:
  - Clean False Positive Rate (FPR): **0.0222** (2 / 90)
  - Altered Detection Recall: **0.9333** (84 / 90)
  - Altered Detection Precision: **0.9767**
  - Clean Mean Anomaly Score: **0.0178**
  - Altered Mean Anomaly Score: **0.7596**
  - 100% recall achieved on `paste_over_plot`, `dark_ink_overwrite`, and `misaligned_numerical_splice`.

---

## 6. Deterministic Statutory Rule Engine & Multimodal Precedence

The rule engine strictly enforces statutory precedence over statistical models:
1. **Direct Statutory Contradictions** (`CONFIRMED_INCONSISTENCY`):
   Overrides statistical ML scores. Critical violations (area capacity overflow, conflicting double sales, survey plot mismatch) immediately halt processing.
2. **Archival Gaps** (`MISSING_EVIDENCE`):
   Pre-1972 colonial/liberation volume records route strictly to `REQUEST_MISSING_RECORDS`. Applicants are never labeled as fraudulent due to missing archival records.
3. **Tenure-Aware Double Disposition**:
   Distinguishes valid partial subdivisions (`REVIEW_REQUIRED`) from conflicting over-conveyances (`CONFIRMED_INCONSISTENCY`) by tracking cumulative area within current seller title tenures.
4. **Statistical Demotion**:
   Elevated ML scores without verified statutory contradictions generate a `RISK_INDICATOR`, prompting secondary screening rather than automated adverse actions.

---

## 7. Stress Testing & Concurrency Hardening

- **Total Stress Cases**: 26 tests across 5 categories (100% Pass rate).
- **Zero-Division & Extreme Values**: Handled safely without exception ($10^7$ dec, $10^{12}$ BDT, negative inputs).
- **Calendar Boundary Validation**: Leap year valid dates (`2024-02-29`) parse successfully; invalid dates (`2023-02-29`, `2024-02-30`, `2024-04-31`) are rejected.
- **Corrupt File Uploads**: 0-byte files, invalid extensions (`.exe`, `.sh`), and corrupted magic bytes rejected with HTTP 400.
- **Performance Under Load**: 100 consecutive API verification requests completed in 0.51s (**197.4 requests/second**, median latency **5.0ms**, zero failures).

---

## 8. Limitations & Real-World Operational Boundaries

> [!CAUTION]
> **Essential Operating Limitations**:
> 1. **Synthetic Data Boundary**: All models were trained and evaluated exclusively on synthetic land records. Real operational deployment requires calibration against authentic digitized Land Revenue volumes.
> 2. **Human-in-the-Loop Obligation**: Automated OCR extractions must be visually inspected and confirmed by registration clerks before statutory submission.
> 3. **Non-Judicial Evidentiary Weight**: Risk scores and anomaly alerts constitute administrative decision-support signals only and do not substitute for formal title adjudication under Bangladesh law.

---

## 9. Final Acceptance Verdict

### **VERDICT: ACCEPT WITH GOVERNANCE LIMITATIONS**
The LandGuard AI/ML, computer vision, OCR, dataset integrity, and rule engine components satisfy all hackathon and engineering acceptance criteria. The codebase is fully frozen, reproducible, and ready for integration handoff.
