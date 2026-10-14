# LandGuard AI — Post-Remediation Independent Verification Report

> **Report Location:** `reports/post_remediation_validation/POST_REMEDIATION_REPORT.md`  
> **Evaluation Date:** 2026-10-13  
> **Repository Path:** `F:\land gurd`  
> **Baseline Commits:** `a31bc04` (Phase 1 Benchmark) $\rightarrow$ `6dfc79f` (Audit) $\rightarrow$ `50ca720` (Readiness Gate) $\rightarrow$ `953a2dc` (Targeted Remediation) $\rightarrow$ Current Post-Remediation Verification  
> **Execution Environment:** Windows 10, Python 3.11.9, Tesseract 5.4.0 (`ben+eng`), OpenCV 4.10.0, scikit-learn 1.5.2, XGBoost 2.1.1  
> **Final Authoritative Decision:** **`READY WITH LIMITATIONS FOR APP INTEGRATION`**

---

## 1. Executive Summary & Verification Purpose

Following the implementation of targeted fixes at commit [`953a2dc`](file:///F:/land%20gurd) (tenure-aware seller title disposition, continuous physics-based visual anomaly scoring, and anti-leakage guards), this post-remediation independent verification was conducted to assess generalization **without modifying rules or tuning thresholds on evaluation data**.

The evaluation was executed across four independent dimensions:
1. **Fresh Deterministic Holdout ($n=60$):** An untouched set of unseen ownership histories, seller reacquisition sequences, successive partial subdivisions, and compound fraud scenarios generated with a distinct random seed (`seed=8888`).
2. **Computer Vision Holdout ($n=80$):** A fresh set of 20 clean images across 4 template cohorts and 60 altered images across all 6 physical/digital alteration mechanisms with independent rendering seeds (`seeds 200–220`).
3. **Probability Calibration Analysis ($n=500$):** Reliability diagrams, 10 equal-width bins, Brier scores, and Expected Calibration Error (ECE) evaluated on untouched test sets.
4. **Unmodified OCR Field Extraction:** Exact match accuracy audited across all legal fields without altering ground truth.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                             POST-REMEDIATION VERIFICATION RESULTS                                │
│                                                                                                  │
│  1. FRESH HOLDOUT (n=60): 35 Legitimate, 25 Compound Fraud.                                      │
│     Rule Engine Confusion Matrix: [[35, 0], [0, 25]] -> 100% Acc, 100% Prec, 100% Rec, 1.000 F1. │
│     Zero False Positives on Seller Reacquisition sequences and Successive Subdivisions.          │
│  2. CV IMAGE HOLDOUT (n=80): 20 Clean, 60 Altered (6 mechanisms).                                │
│     Clean FPR: 0.00% (0/20) | Altered Recall: 100.00% (60/60) | F1: 1.0000.                       │
│     Continuous Scores vary smoothly: 0.7679 to 0.8273 (Clean = 0.0000). Zero label leakage.      │
│  3. ML PROBABILITY CALIBRATION (n=500):                                                          │
│     XGBoost: Brier = 0.0013, ECE = 0.0110 (Polarized confidence distribution)                   │
│     Logistic Regression: Brier = 0.0028, ECE = 0.0116                                            │
│     Random Forest: Brier = 0.0362, ECE = 0.0946 (Mid-range [0.5-0.7] overconfidence gap)        │
│  4. OCR FIELD MATCH RATES: Plot Number 89.6%, Transferred Area 93.8%, Deed Number 87.5%.         │
│     Execution date requires manual form review (0.0% unassisted regex match).                   │
│  5. TEST SUITE & VALIDATION: pytest: 39/39 PASSED (1.51s) | validate_all.py: PASSED (1.41s).     │
│  6. VERDICT: READY WITH LIMITATIONS FOR APP INTEGRATION.                                         │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Verification of Repository State & Commit Lineage

Prior to running holdout evaluations, the Git baseline was checked:
- **Baseline Commit:** [`953a2dc`](file:///F:/land%20gurd) (*feat: complete deep AI validation, stress-test independence audit, and tenure-epoch remediation*).
- **Working Tree State:** Tracked and intact on branch `master`.
- **Existing Reports Preserved:** All historical audit reports ([`AI_DATA_READINESS_GATE.md`](file:///F:/land%20gurd/reports/AI_DATA_READINESS_GATE.md), [`FINAL_INDEPENDENT_ACCEPTANCE_AUDIT.md`](file:///F:/land%20gurd/reports/FINAL_INDEPENDENT_ACCEPTANCE_AUDIT.md), [`reports/deep_validation/DEEP_VALIDATION_REPORT.md`](file:///F:/land%20gurd/reports/deep_validation/DEEP_VALIDATION_REPORT.md)) were preserved intact.

---

## 3. Fresh Deterministic Holdout ($n=60$) & Rule Generalization

### 3.1 Holdout Dataset Construction
To prevent data contamination, a completely fresh holdout was generated using `seed=8888` and entity partition offset `+5000` (300 new fictional owners, 60 new fictional parcels). None of these cases were used to alter rules, adjust thresholds, or tune feature extractors.

The 60 holdout scenarios consist of:
1. **Legitimate Seller Reacquisition Chains ($n=10$, `HLD-REACQ-01` to `10`):**
   - 4-link conveyancing sequence: Owner A sells to Owner B in 2002; B sells to C in 2010; C sells back to A in 2018 (reacquisition); Owner A executes conveyance to Owner D in 2024.
   - Evaluates whether the tenure-aware rule correctly isolates sales to the current ownership tenure (since 2018) rather than summing across all time.
2. **Legitimate Successive Partial Subdivisions ($n=10$, `HLD-SUBDIV-01` to `10`):**
   - Owner executes initial partial transfer (30% area) in 2015, followed by second partial transfer (35% area) in 2023. Cumulative disposition is $65\% \le 100\%$ parcel capacity.
3. **Legitimate Multi-Heir Succession Partitions ($n=10$, `HLD-WARISH-01` to `10`):**
   - Co-heir executes Warishnama partition conveyance strictly equal to individual entitlement (25% parcel area).
4. **Ambiguous Untraced Pre-1972 Archival Conveyances ($n=5$, `HLD-ARCH-01` to `05`):**
   - Deed cites damaged/unindexed pre-1972 sub-registry archival volume (`UNINDEXED_PRE1972_VOLUME_...`). Tests whether the engine generates `MISSING_EVIDENCE` without false-flagging criminal fraud.
5. **Compound Double Sales Across Tenure ($n=10$, `HLD-DBLSALE-01` to `10`):**
   - Seller conveys 80% of parcel in 2021 without reacquisition, and executes competing 75% sale in 2024 (cumulative $155\% > 100\%$) accompanied by deed schedule plot tampering.
6. **Compound Area Excess & Fabricated Mutation ($n=8$, `HLD-AREAXS-01` to `08`):**
   - Transferred area represents 170% of parcel capacity, accompanied by fictitious mutation case number and tax arrears.
7. **Compound Imposter Seller & Tampered Deed ($n=7$, `HLD-IMPOST-01` to `07`):**
   - Seller identity does not appear in chain of title, registrar seal is absent, and document contains physical paste-over seam.

### 3.2 Holdout Rule Evaluation Results
From [`reports/post_remediation_validation/fresh_holdout_rule_metrics.json`](file:///F:/land%20gurd/reports/post_remediation_validation/fresh_holdout_rule_metrics.json) and [`fresh_holdout_rule_predictions.csv`](file:///F:/land%20gurd/reports/post_remediation_validation/fresh_holdout_rule_predictions.csv):

| Metric | Target / Benchmark | Fresh Holdout Result ($n=60$) | Verification Status |
| :--- | :---: | :---: | :---: |
| **Total Cases Evaluated** | 60 | **60** | Complete |
| **True Negatives (Legitimate)** | 35 | **35** | 100% Specificity |
| **False Positives** | 0 | **0** | **0 False Positives** |
| **True Positives (Fraud)** | 25 | **25** | 100% Recall |
| **False Negatives** | 0 | **0** | **0 False Negatives** |
| **Accuracy** | $\ge 0.90$ | **`1.0000`** ($60/60$) | **PASSED** |
| **Precision** | $\ge 0.90$ | **`1.0000`** ($25/25$) | **PASSED** |
| **Recall** | $\ge 0.95$ | **`1.0000`** ($25/25$) | **PASSED** |
| **Specificity** | $\ge 0.90$ | **`1.0000`** ($35/35$) | **PASSED** |
| **F1-Score** | $\ge 0.90$ | **`1.0000`** | **PASSED** |

### 3.3 Confusion Matrix
$$\text{Confusion Matrix} = \begin{bmatrix} \text{TN} = 35 & \text{FP} = 0 \\ \text{FN} = 0 & \text{TP} = 25 \end{bmatrix}$$

### 3.4 False Positive & False Negative Log
- **False Positives ($n=0$):** None. All 10 seller reacquisition sequences (`HLD-REACQ-01` to `10`) were correctly identified as valid conveyances under the seller's current title tenure. All 10 partial subdivisions (`HLD-SUBDIV-01` to `10`) were correctly routed to `RULE_PARTIAL_SUBDIVISION_CAPACITY_CHECK` (`REVIEW_REQUIRED`, score `0.30`) rather than fraud. All 5 archival cases (`HLD-ARCH-01` to `05`) were correctly assigned to `RULE_BROKEN_CHAIN_OF_TITLE` under `MISSING_EVIDENCE` (score `0.20`).
- **False Negatives ($n=0$):** None. All 25 compound fraud cases triggered high/critical inconsistency flags (`RULE_CONFLICTING_DOUBLE_DISPOSITION`, `RULE_AREA_EXCEEDS_CAPACITY`, `RULE_SELLER_NOT_TITLEHOLDER`, `RULE_PLOT_MISMATCH_WITH_KHATIAN`).

> [!IMPORTANT]
> **Scientific Integrity Disclaimer:** Although the remediated rule engine achieved $100\%$ accuracy across both the 100 targeted expansion scenarios and the 60 fresh holdout scenarios, **we do not claim 100% real-world generalization**. In live operational environments with corrupt registry databases, handwritten deed illegibility, and unstandardized mouza boundaries, edge cases will arise. This $100\%$ score confirms mathematical and algorithmic correctness under the synthetic relational schema.

---

## 4. Computer Vision Holdout ($n=80$) Evaluation

### 4.1 Test Setup & Content-Only Verification
To verify the visual anomaly baseline independently of metadata shortcuts:
- Evaluated on **80 fresh images**: 20 clean synthetic documents across 4 distinct template cohorts (`TMPL-COHORT-01` through `04`) and 60 tampered documents across all 6 alteration mechanisms (`seeds 210–219`).
- **Zero Metadata Leakage:** The detector function [`detect_visual_anomalies(img)`](file:///F:/land%20gurd/src/landguard_vision/visual_anomaly_baseline.py) receives only a raw PIL `Image` object. It has no access to generator metadata, alteration labels, scenario IDs, or sidecar files. All bounding boxes, edge gradients, and saliency scores are computed strictly from pixel arrays via Canny edge detection, dark contour analysis, and perimeter Sobel energy.

### 4.2 Audited CV Performance Metrics
From [`reports/post_remediation_validation/cv_holdout_metrics.json`](file:///F:/land%20gurd/reports/post_remediation_validation/cv_holdout_metrics.json):

$$\text{CV Confusion Matrix} = \begin{bmatrix} \text{Clean TN} = 20 & \text{Clean FP} = 0 \\ \text{Altered FN} = 0 & \text{Altered TP} = 60 \end{bmatrix}$$

- **Clean False-Positive Rate:** **`0.00%`** ($0/20$). Clean document table grids and stencils were correctly rejected by multi-cell collinearity filtering.
- **Altered Recall:** **`100.00%`** ($60/60$). Every controlled alteration across all 6 mechanisms was successfully detected.
- **Precision:** **`100.00%`** ($60/60$).
- **F1-Score:** **`1.0000`**.

### 4.3 Continuous Score Distribution per Mechanism
From [`reports/post_remediation_validation/cv_holdout_evaluation.csv`](file:///F:/land%20gurd/reports/post_remediation_validation/cv_holdout_evaluation.csv):

| Alteration Mechanism | Sample Count | Detection Rate | Min Score | Mean Score | Max Score | Score Std | Physical Characteristics |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`CLEAN_UNTAMPERED`** | 20 | **0.0%** | **0.0000** | **0.0000** | **0.0000** | 0.0000 | Zero isolated anomalies |
| **`paste_over_plot`** | 10 | **100.0%** | 0.8206 | **0.8242** | 0.8273 | 0.0031 | Sharp rectangular seam, high edge gradient |
| **`copy_move_clone`** | 10 | **100.0%** | 0.7733 | **0.7784** | 0.7856 | 0.0050 | Cloned patch texture with boundary step |
| **`localized_erasure_blur`** | 10 | **100.0%** | 0.7695 | **0.7748** | 0.7826 | 0.0053 | Diffuse boundary halo, high patch area |
| **`dark_ink_overwrite`** | 10 | **100.0%** | 0.8109 | **0.8109** | 0.8109 | 0.0000 | Extreme contrast delta ($> 90$ luminance gap) |
| **`faded_chemical_erasure`**| 10 | **100.0%** | 0.7679 | **0.7733** | 0.7811 | 0.0054 | Faint residual stroke, low edge energy |
| **`misaligned_numerical_splice`** | 10 | **100.0%** | 0.8045 | **0.8089** | 0.8115 | 0.0020 | Displaced baseline seam, moderate Sobel |

**Conclusion:** The constant `0.85` anomaly score is completely eliminated. Saliency scores vary smoothly between **`0.7679`** and **`0.8273`** based on physical patch geometry, Sobel edge energy, and local contrast.

---

## 5. Machine Learning Probability Calibration Evaluation

### 5.1 Calibration Methodology
Calibration was evaluated on the untouched canonical test set ($n=500$, $168$ Legitimate vs $332$ Fraud) using $M = 10$ equal-width reliability bins:
$$B_m = \left[\frac{m-1}{10}, \frac{m}{10}\right), \quad m \in \{1, \dots, 10\}$$
For each bin, we compute the mean predicted confidence $\bar{p}_m$, empirical accuracy $\bar{y}_m$, and calibration gap $|\bar{y}_m - \bar{p}_m|$.
- **Brier Score:** $\text{Brier} = \frac{1}{N} \sum_{i=1}^N (\hat{p}_i - y_i)^2 \in [0, 1]$ (lower is better; $0.0$ is perfect probability forecast).
- **Expected Calibration Error (ECE):** $\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} |\bar{y}_m - \bar{p}_m|$.

### 5.2 Model Calibration Summary
From [`reports/post_remediation_validation/ml_calibration_metrics.json`](file:///F:/land%20gurd/reports/post_remediation_validation/ml_calibration_metrics.json):

| Model Name | Test Size ($N$) | Brier Score | ECE | Mean Predicted Prob | Actual Positive Fraction | Calibration Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **XGBoost Classifier** | 500 | **`0.0013`** | **`0.0110`** | 0.6621 | 0.6640 | **Highly Polarized Risk Score** |
| **Logistic Regression** | 500 | **`0.0028`** | **`0.0116`** | 0.6608 | 0.6640 | Well-calibrated sigmoidal score |
| **Random Forest** | 500 | **`0.0362`** | **`0.0946`** | 0.6651 | 0.6640 | Mid-range overconfidence |

### 5.3 Reliability Bin Audit
From [`reports/post_remediation_validation/ml_calibration_bins.csv`](file:///F:/land%20gurd/reports/post_remediation_validation/ml_calibration_bins.csv):

```
XGBoost Reliability Bins:
  Bin  1 [0.0 - 0.1): Count = 162 | Mean Conf = 0.0124 | Emp Acc = 0.0000 | Gap = 0.0124
  Bin  2 [0.1 - 0.2): Count =   5 | Mean Conf = 0.1368 | Emp Acc = 0.0000 | Gap = 0.1368
  Bin  7 [0.6 - 0.7): Count =   1 | Mean Conf = 0.6516 | Emp Acc = 0.0000 | Gap = 0.6516
  Bin 10 [0.9 - 1.0]: Count = 332 | Mean Conf = 0.9935 | Emp Acc = 1.0000 | Gap = 0.0065
  (Bins 3-6 and 8-9 are empty; predictions are polarized to extremities)

Random Forest Reliability Bins:
  Bin  1 [0.0 - 0.1): Count =  99 | Mean Conf = 0.0094 | Emp Acc = 0.0000 | Gap = 0.0094
  Bin  2 [0.1 - 0.2): Count =  25 | Mean Conf = 0.1389 | Emp Acc = 0.0000 | Gap = 0.1389
  Bin  6 [0.5 - 0.6): Count =  21 | Mean Conf = 0.5252 | Emp Acc = 0.0000 | Gap = 0.5252  <-- OVERCONFIDENT
  Bin  7 [0.6 - 0.7): Count =   7 | Mean Conf = 0.6544 | Emp Acc = 0.0000 | Gap = 0.6544  <-- OVERCONFIDENT
  Bin  8 [0.7 - 0.8): Count =  44 | Mean Conf = 0.7728 | Emp Acc = 0.8864 | Gap = 0.1136
  Bin  9 [0.8 - 0.9): Count =  90 | Mean Conf = 0.8488 | Emp Acc = 1.0000 | Gap = 0.1512
  Bin 10 [0.9 - 1.0]: Count = 203 | Mean Conf = 0.9771 | Emp Acc = 1.0000 | Gap = 0.0229
```

> [!WARNING]
> **Probabilities vs. Uncalibrated Risk Scores:**  
> The XGBoost classifier produces a low ECE ($0.0110$) primarily because its predictions are **polarized to the extreme boundaries** ($98.8\%$ of predictions lie in $[0.0, 0.1)$ or $[0.9, 1.0]$).  
> Random Forest demonstrates that ensemble tree averaging in the mid-range ($[0.5, 0.7]$) suffers from empirical overconfidence (cases given $52-65\%$ fraud probability were actually legitimate).  
> **Operational Rule:** ML model outputs must be presented in the user interface as **probabilistic risk scores**, never as calibrated Bayesian posterior probabilities of fraud.

---

## 6. Unmodified OCR Field Extraction Metrics

Evaluated on the canonical test set images without modifying ground truth. From [`reports/post_remediation_validation/ocr_field_metrics.json`](file:///F:/land%20gurd/reports/post_remediation_validation/ocr_field_metrics.json):

| Legal Field Name | Evaluated Images | Exact Matches | Exact Match Rate | Primary Source of Inexact Match |
| :--- | :---: | :---: | :---: | :--- |
| **`dag_plot_number`** | 48 | 43 | **`89.58%`** | Digit blur on low-resolution / uneven illumination |
| **`transferred_area_decimal`** | 16 | 15 | **`93.75%`** | Decimal point dot dropout on skewed scans |
| **`deed_number`** | 8 | 7 | **`87.50%`** | Missing prefix on unassisted plain scans |
| **`khatian_number`** | 8 | 7 | **`87.50%`** | Baseline rotation on tilted Porcha tables |
| **`execution_date`** | 8 | 0 | **`0.00%`** | Date regex pattern missed; requires UI form review |

### Error Taxonomy Summary
1. **Bengali Digit Normalization:** Digit normalization (`০-৯` $\rightarrow$ `0-9`) successfully rescued 12 additional numbers that would otherwise have failed exact match comparison.
2. **Execution Date Extraction Failure:** Tesseract OCR frequently extracts execution dates as partial character sequences (e.g. `2001-08-21 1 / (SELLER)`). Without assisted bounding-box cropping, regex matching on full-page OCR fails ($0.0\%$).
3. **Mandatory UI Constraint:** In the Phase 2 web application, OCR outputs must pre-fill an **editable intake form** where the user confirms or adjusts extracted numbers prior to triggering verification rules.

---

## 7. Test Suite Execution & Pipeline Validation

All regression and schema validation suites were executed directly on Python 3.11.9:

| Command Executed | Exit Code | Runtime | Actual Output / Result | Status |
| :--- | :---: | :---: | :--- | :---: |
| `python -m pytest -v` | **`0`** | `1.51s` | **`39 passed in 1.51s` (100% pass rate)** across 13 test modules | **PASSED** |
| `python scripts/validate_all.py` | **`0`** | `1.41s` | Schema Validation: PASSED (100 sample entities, 0 errors); Checksums: 600 checked, 0 mismatches; Watermarks: 600 checked, 0 missing | **PASSED** |
| `python scripts/run_post_remediation_verification.py`| **`0`** | `1.30s` | Generated all fresh holdout, CV, calibration, and OCR verification files | **PASSED** |

---

## 8. Final Gate Verdict & Operational Integration Limitations

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│                              OFFICIAL AUDIT GATE DECISION                                        │
│                                                                                                  │
│                   >>> READY WITH LIMITATIONS FOR APP INTEGRATION <<<                             │
│                                                                                                  │
│   All targeted remediations verified on an untouched, deterministic fresh holdout (n=60).        │
│   CV detector generalized to 80 unseen images with continuous physics-based scoring.             │
│   39/39 regression tests passing. Zero target leakage. Checksums and watermarks verified.      │
│                                                                                                  │
│   Phase 2 Web Application development may commence immediately under the 5 mandatory limitations. │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Mandatory Operational Limitations for Phase 2 Integration

1. **Synthetic-Only Research Disclaimer:**  
   The LandGuard system has been developed and evaluated strictly using synthetic data generated under Bangladeshi legal schemas. No authentic operational government land records or confidential citizen NID data were utilized. Benchmark metrics ($F1 = 1.000$) reflect performance under synthetic assumptions and cannot be extrapolated to judicial validity on authentic physical documents without field certification.
2. **Statutory Rule Precedence over ML Probabilities:**  
   The Deterministic Rule Engine must always hold primary veto authority. ML models (XGBoost, Random Forest, Logistic Regression) must serve solely as probabilistic risk advisors. An ML model must never autonomously reject a transaction if statutory verification rules pass.
3. **Mandatory Editable OCR Intake Forms:**  
   OCR field extraction achieves $89.6\%$ accuracy on plot numbers and $93.8\%$ on land areas, but drops on degraded scans and fails on unassisted dates ($0.0\%$). The Phase 2 application must implement an editable intake form with highlighted confidence indicators, allowing users to verify and correct extracted fields before executing verification checks.
4. **Computer Vision Presence vs. Authenticity Boundaries:**  
   The visual anomaly detector identifies mechanical paste-over boundaries, numerical splices, ink overwrites, and missing circular seals. It cannot authenticate ink age, chemical paper composition, or physical sub-registry stamps. Interactive bounding boxes must be rendered on the document canvas for human verification.
5. **Archival Missing Evidence Routing:**  
   Pre-1972 archival deeds citing unindexed or damaged sub-registry volumes must never be classified as fraudulent broken title chains by automated systems. They must be routed to `MISSING_EVIDENCE` for manual field ledger retrieval.

---

**Sign-off:** LandGuard AI Machine Learning & Computer Vision Verification Team  
**Date:** October 13, 2026
