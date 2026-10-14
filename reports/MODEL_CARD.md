# Model Card: LandGuard Fraud-Risk Machine Learning & Explainable Verification Engine

## 1. Model Overview & Purpose
The LandGuard research pipeline evaluates five complementary detection approaches for identifying transaction inconsistencies and fraud risks in land administration records, integrated through an explainable hybrid risk scoring engine ([`src/landguard_models/explainable_risk.py`](file:///F:/land%20gurd/src/landguard_models/explainable_risk.py)):
1. **Majority-Class Baseline**: Dummy baseline predicting the majority class (`fraud_risk = 1`) on the test set (`66.4%`) for honest calibration.
2. **Deterministic Statutory Rule Engine**: Explainable statutory legal logic ([`src/landguard_models/verification_rules.py`](file:///F:/land%20gurd/src/landguard_models/verification_rules.py)) validating parcel capacity, cumulative multi-sale disposition, chain of title continuity, mutation register status, and document evidence, categorizing findings into `CONFIRMED_INCONSISTENCY`, `REVIEW_REQUIRED`, `MISSING_EVIDENCE`, and `RISK_INDICATOR`.
3. **Logistic Regression Baseline**: L2-regularized linear classification benchmark with `StandardScaler` fitted strictly on the training split and validation-tuned decision threshold.
4. **Random Forest Classifier**: Ensemble of 200 depth-constrained decision trees modeling non-linear feature interactions.
5. **Gradient Boosted Decision Trees (XGBoost)**: Primary probability-ranking benchmark model optimized with log-loss, early stopping on the validation split, and validation-tuned threshold selection.

> [!NOTE]
> **Intended Use**: Screening decision-support tool for land registrars, Assistant Commissioners (Land), and property buyers. A high fraud-risk score flags a transaction for manual legal review; it does not constitute judicial proof of fraud or forgery.

---

## 2. Input Features & Availability Classification (`reports/feature_availability_audit.csv`)

Models support two explicit feature sets in [`src/landguard_models/build_features.py`](file:///F:/land%20gurd/src/landguard_models/build_features.py):
- **Mode 1 (`include_document_evidence=True`, 19 Features)**: Combines 15 Registry-Only Tabular/Relational Features with 4 Coupled OCR/CV Document Evidence Features.
- **Mode 2 (`include_document_evidence=False`, 15 Features)**: Uses strictly the 15 Registry-Only Tabular/Relational Features (zero OCR/CV features).

### A. Registry-Only Tabular & Relational Features (15 Features)
1. `transferred_area_decimal`: Land area conveyed in the deed (decimals).
2. `parcel_total_area_decimal`: Cadastral plot capacity from the registered khatian.
3. `area_ratio`: Proportion of parcel transferred (`transferred_area / parcel_area`).
4. `area_excess_flag`: Binary indicator (`1.0` if conveyed area exceeds `1.0001x` parcel capacity).
5. `cumulative_seller_area_ratio`: Cumulative ratio of all conveyances executed by the same seller on the parcel relative to total parcel capacity.
6. `price_per_decimal`: Consideration BDT divided by transferred area.
7. `has_previous_deed_ref`: Indicator of documented link to an antecedent deed.
8. `is_ancestral_ref`: Indicator of inheritance from an ancestral survey khatian (`CS`/`SA`/`RS`).
9. `previous_deed_verified_flag`: Relational lookup verifying the cited antecedent deed in registration volumes.
10. `chain_length`: Number of preceding transactions in the parcel's chronological title chain.
11. `seller_was_previous_buyer`: Relational verification that the current transferor acquired title in an antecedent conveyance.
12. `mutation_present`: Relational verification of an `APPROVED` mutation order in Land Revenue registers.
13. `mutation_pending_flag`: Relational indicator that a mutation case exists in `PENDING` administrative status.
14. `tax_year_delta`: Elapsed years between deed execution year and last paid Land Development Tax (Dakhila) year.
15. `conflicting_sale_flag`: Relational lookup detecting competing conveyances by the same seller or cumulative transfers exceeding parcel capacity.

### B. Coupled Document Image Inspection Features (4 OCR/CV Features)
16. `doc_plot_discrepancy_flag`: Discrepancy between OCR-extracted deed plot number and registered cadastral survey dag.
17. `doc_area_discrepancy_flag`: Discrepancy (`> 0.25` dec) between OCR-extracted deed area and structured register area.
18. `cv_seal_absent_flag`: Derived from official seal contour presence detection (`detect_seal_presence`).
19. `cv_visual_anomaly_score`: Continuous visual splice/tampering confidence (`0.0–1.0`) derived from `detect_visual_anomalies`.

### Strict Anti-Leakage Architecture
- **18 Forbidden Oracle/Simulator Keys**: `validate_no_leakage()` inspects all input records and raises a `ValueError` if any forbidden simulator or oracle key (`claimed_dag_plot_number`, `has_seal`, `has_visual_anomaly`, `visual_anomaly_score`, `injected_tampering`, `visual_tampering_overlay`, `seal_omitted`, `scenario_category`, `fraud_category`, `is_fraud_risk`, `ground_truth_label`, `expected_rule_violations`, `explanation`, `injected_modifications`, `simulator_audit_metadata`, `plot_discrepancy_flag`, `seal_omitted_flag`, `visual_tampering_flag`) appears anywhere in transaction inputs.
- **Multi-Entity Group-Disjoint Split (`Train = 1,700`, `Val = 300`, `Test = 500`)**: Zero overlap (`0`) verified across `template_cohort`, `parcel_id`, `primary_seller_id`, and `scenario_id`.

---

## 3. Benchmark Performance Across Five Validation Regimes (`reports/independent_ml_validation.md`)

### 3.1 Regime A & C — Multi-Entity Group-Disjoint Split + Coupled OCR/CV Document Evidence (`19 Features`, `n_test = 500`)
Held-out test set: `500` scenarios (`332` fraud-risk vs. `168` legitimate), with decision thresholds selected solely on the `300`-scenario validation split:

| Model (Regime A & C: 19 Features) | Threshold | Accuracy (95% CI) | Precision | Recall | F1-Score (95% CI) | ROC-AUC | PR-AUC | Brier | ECE | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | `0.50` | `0.6640` (`0.624–0.704`) | `0.6640` | `1.0000` | `0.7981` (`0.769–0.826`) | `0.5000` | `0.6640` | `0.3360` | `0.3360` | 0 | 168 | 0 | 332 |
| **Deterministic Rule Baseline** | N/A | `0.9480` | `0.9274` | **`1.0000`** | `0.9623` | N/A | N/A | N/A | N/A | 142 | 26 | 0 | 332 |
| **Logistic Regression** | `0.28` | `0.9760` (`0.964–0.988`) | `0.9706` | `0.9940` | `0.9821` (`0.974–0.991`) | `0.9985` | `0.9993` | `0.0152` | `0.0188` | 158 | 10 | 2 | 330 |
| **Random Forest** | `0.67` | `0.9600` (`0.940–0.976`) | `0.9509` | `0.9910` | `0.9705` (`0.956–0.983`) | `0.9963` | `0.9982` | `0.0447` | `0.0847` | 151 | 17 | 3 | 329 |
| **XGBoost Classifier** | `0.41` | **`0.9820`** (`0.972–0.992`) | **`0.9792`** | `0.9940` | **`0.9865`** (`0.979–0.994`) | **`0.9994`** | **`0.9997`** | **`0.0104`** | **`0.0185`** | 161 | 7 | 2 | 330 |

### 3.2 Regime B — Strict Registry-Only Tabular Features (`15 Features`, Zero OCR/CV Features, `n_test = 500`)
When all 4 document-image features are withheld, models rely solely on structured registry tables and secondary behavioral/economic correlates:

| Model (Regime B: Registry-Only 15 Features) | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier | ECE | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Rule Baseline (Registry-Only)** | N/A | `0.8100` | **`0.9100`** | `0.7922` | `0.8470` | N/A | N/A | N/A | N/A | 142 | 26 | 69 | 263 |
| **Logistic Regression** | `0.32` | `0.9000` | `0.8832` | `0.9789` | `0.9286` | `0.9571` | `0.9776` | `0.0799` | `0.0688` | 125 | 43 | 7 | 325 |
| **Random Forest** | `0.60` | `0.9200` | `0.9033` | `0.9849` | `0.9424` | `0.9651` | `0.9812` | `0.0624` | `0.0384` | 133 | 35 | 5 | 327 |
| **XGBoost Classifier** | `0.22` | **`0.9220`** | `0.8949` | **`1.0000`** | **`0.9445`** | **`0.9682`** | **`0.9837`** | **`0.0611`** | `0.0458` | 129 | 39 | 0 | 332 |

### 3.3 Regime D — Leave-One-Fraud-Family-Out (LOFFO) Generalization (`8 Folds`)
Holding out each of the 8 fraud scenario families completely from training (`n = 208` unseen fraud cases per fold):
- **Statutory Rule Engine Mean Recall**: **`1.0000` (`100.0%` across all 8 unseen fraud families)**.
- **Random Forest Mean Recall**: **`0.8383`** (`0.9940` on registry-only features) due to shared multi-feature economic/administrative correlates (`tax_year_delta`, `price_per_decimal`, `mutation_present`).
- **Logistic Regression Mean Recall**: **`0.6208`** (`0.8810` on registry-only features).
- **XGBoost Mean Recall**: **`0.5457`** (`0.9315` on registry-only features; lower on full 19-feature set when a held-out document feature is absent from training splits).
- **Architectural Conclusion**: Supervised ML models alone miss `16%–45%` of unseen document-specific fraud mechanisms when that mechanism is absent from training data; the **Deterministic Statutory Rule Engine (`100.0%` LOFFO recall) is mandatory** as a first-pass safety gate.

### 3.4 Regime E — Noisy Operational Simulation (Heavy Administrative Lag + Degraded Scan OCR/CV Noise, `n_test = 500`)
Evaluating under heightened administrative lag (delayed mutations, pre-digital partition deeds) and degraded scan OCR/CV noise:

| Model (Regime E: Noisy Operational) | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier | ECE | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Rule Baseline** | N/A | `0.9020` | `0.8794` | `0.9880` | `0.9305` | N/A | N/A | N/A | N/A | 123 | 45 | 4 | 328 |
| **Logistic Regression** | `0.36` | `0.9300` | `0.9183` | `0.9819` | `0.9491` | `0.9811` | `0.9897` | `0.0469` | `0.0310` | 139 | 29 | 6 | 326 |
| **Random Forest** | `0.64` | `0.9420` | `0.9268` | `0.9910` | `0.9578` | `0.9753` | `0.9858` | `0.0584` | `0.0618` | 142 | 26 | 3 | 329 |
| **XGBoost Classifier** | `0.46` | **`0.9600`** | **`0.9483`** | **`0.9940`** | **`0.9706`** | **`0.9904`** | **`0.9944`** | **`0.0298`** | **`0.0278`** | 150 | 18 | 2 | 330 |

---

## 4. Explainable Hybrid Risk Engine (`src/landguard_models/explainable_risk.py`)
`build_explainable_risk_assessment()` combines:
1. **Statutory Rule Findings** (`CONFIRMED_INCONSISTENCY`, `REVIEW_REQUIRED`, `MISSING_EVIDENCE`, `RISK_INDICATOR`),
2. **Calibrated ML Risk Probability** (`0–100` score from XGBoost / Logistic Regression),
3. **Top Contributing Feature Drivers** (human-readable explanations of the active risk factors),
4. **OCR & Computer Vision Confidence Signals** (`ocr_confidence`, `vision_seal_present`, `vision_signature_present`, `vision_anomaly_score`), and
5. **Recommended Next Verification Action** (`CRITICAL_RISK` / `HIGH_RISK` / `MODERATE_RISK_REVIEW` / `LOW_RISK`).
