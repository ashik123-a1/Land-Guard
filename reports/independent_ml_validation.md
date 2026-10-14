# Independent Machine Learning Validation, Anti-Leakage Remediation & Five-Regime Benchmark Report

> **Safety & Scope Notice:** All data, records, and scenarios evaluated in this report are 100% synthetic (`SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT`). Benchmark scores on synthetic scenarios do **not** prove real-world fraud detection accuracy.

---

## 1. Root-Cause Audit & Structural Remediation of the Prior `1.0000` Benchmark

In the pre-remediation baseline (`reports/baseline_snapshot/model_comparison.json`), the Deterministic Rule Engine, Logistic Regression, Random Forest, and XGBoost all reported `1.0000` Accuracy, Precision, Recall, and F1, while Leave-One-Fraud-Family-Out (LOFFO) cross-validation achieved only `4.27%` mean recall across 8 fraud families (`0.00%` on 7 of 8 families).

We remediated all three structural causes in [`src/landguard_data/generate_transactions.py`](file:///F:/land%20gurd/src/landguard_data/generate_transactions.py), [`src/landguard_data/generate_scenarios.py`](file:///F:/land%20gurd/src/landguard_data/generate_scenarios.py), [`scripts/generate_all.py`](file:///F:/land%20gurd/scripts/generate_all.py), and [`src/landguard_models/build_features.py`](file:///F:/land%20gurd/src/landguard_models/build_features.py):

1. **Complete Removal of Oracle Simulator Flags from Transaction Schema**:
   - Removed `claimed_dag_plot_number`, `has_seal`, `has_signature`, `has_visual_anomaly`, and `visual_anomaly_score` from base transaction records and [`schemas/transaction.schema.json`](file:///F:/land%20gurd/schemas/transaction.schema.json) (`additionalProperties: false`).
   - Added 18 forbidden simulator/oracle keys to `FORBIDDEN_LEAKAGE_KEYS` in `build_features.py`.
   - Stored simulator injection provenance exclusively in `data/full/records/simulator_audit_metadata.json`, completely separate from `canonical_records.json`.
2. **Multi-Feature Realistic Ambiguity & Correlated Risk Signals**:
   - Introduced realistic administrative lag on legitimate scenario families (pending Namzari mutations, 1–2 year tax payment deltas, family/distress below-market inheritance transfers, and legitimate multi-part subdivision conveyances within parcel capacity).
   - Introduced realistic secondary behavioral/economic correlates on fraud scenario families (rush below-market consideration, 2–5 year tax arrears, unapproved mutation status, and cumulative seller area transfers exceeding parcel capacity).
3. **Multi-Entity Group-Disjoint Split (`Train = 1,700`, `Val = 300`, `Test = 500`)**:
   - Assigned a dedicated disjoint cohort of 6 owners per scenario (`15,000` owners across `2,500` scenarios) and 25 `template_cohort` buckets.
   - Verified **zero overlap (`0`)** across `template_cohort`, `parcel_id`, `primary_seller_id`, and `scenario_id` between Train, Validation, and Test splits.

---

## 2. Feature Availability & Leakage Audit (`reports/feature_availability_audit.csv`)

| Feature Name | Source Entity | Production Availability | Oracle Shortcut? | Audit Assessment |
| :--- | :--- | :--- | :---: | :--- |
| `transferred_area_decimal` | `transaction` | `AVAILABLE_TABULAR_DEED` | No | `SAFE_OBSERVABLE_FACT` |
| `parcel_total_area_decimal` | `parcel` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_OBSERVABLE_FACT` |
| `area_ratio` | `transaction + parcel` | `AVAILABLE_RELATIONAL_JOIN` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `area_excess_flag` | `transaction + parcel` | `AVAILABLE_RELATIONAL_JOIN` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `cumulative_seller_area_ratio` | `transaction + history + parcel` | `AVAILABLE_RELATIONAL_JOIN` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `price_per_decimal` | `transaction` | `AVAILABLE_TABULAR_DEED` | No | `SAFE_OBSERVABLE_FACT` |
| `has_previous_deed_ref` | `transaction` | `AVAILABLE_TABULAR_DEED` | No | `SAFE_OBSERVABLE_FACT` |
| `is_ancestral_ref` | `transaction` | `AVAILABLE_TABULAR_DEED` | No | `SAFE_OBSERVABLE_FACT` |
| `previous_deed_verified_flag` | `transaction + history` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `chain_length` | `history_transactions` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_OBSERVABLE_FACT` |
| `seller_was_previous_buyer` | `transaction + history` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `mutation_present` | `transaction + mutations` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `mutation_pending_flag` | `transaction + mutations` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `tax_year_delta` | `transaction` | `AVAILABLE_TABULAR_DEED` | No | `SAFE_OBSERVABLE_FACT` |
| `conflicting_sale_flag` | `transaction + history + parcel` | `AVAILABLE_REGISTRY_LOOKUP` | No | `SAFE_RELATIONAL_VERIFICATION` |
| `doc_plot_discrepancy_flag` | `document_evidence + parcel` | `REQUIRES_OCR_ON_DEED_IMAGE` | No | `COUPLED_OCR_EVIDENCE` |
| `doc_area_discrepancy_flag` | `document_evidence + transaction` | `REQUIRES_OCR_ON_DEED_IMAGE` | No | `COUPLED_OCR_EVIDENCE` |
| `cv_seal_absent_flag` | `document_evidence` | `REQUIRES_CV_DETECTOR_ON_IMAGE` | No | `COUPLED_CV_EVIDENCE` |
| `cv_visual_anomaly_score` | `document_evidence` | `REQUIRES_CV_DETECTOR_ON_IMAGE` | No | `COUPLED_CV_EVIDENCE` |

---

## 3. Empirical Results Across Five Validation Regimes (`reports/independent_ml_metrics.json`)

### Regime A & C — Multi-Entity Group-Disjoint Split + Coupled OCR/CV Document Evidence (`19 Features`, `n_test = 500`)
Evaluated on `500` held-out scenarios (`332` fraud-risk, `168` legitimate) with thresholds tuned strictly on the `300`-scenario validation split:

| Model (Regime A & C: 19 Features) | Threshold | Accuracy (95% CI) | Precision | Recall | F1-Score (95% CI) | ROC-AUC | PR-AUC | Brier | ECE | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | `0.50` | `0.6640` (`0.624–0.704`) | `0.6640` | `1.0000` | `0.7981` (`0.769–0.826`) | `0.5000` | `0.6640` | `0.3360` | `0.3360` | 0 | 168 | 0 | 332 |
| **Deterministic Rule Baseline** | N/A | `0.9480` | `0.9274` | **`1.0000`** | `0.9623` | N/A | N/A | N/A | N/A | 142 | 26 | 0 | 332 |
| **Logistic Regression** | `0.28` | `0.9760` (`0.964–0.988`) | `0.9706` | `0.9940` | `0.9821` (`0.974–0.991`) | `0.9985` | `0.9993` | `0.0152` | `0.0188` | 158 | 10 | 2 | 330 |
| **Random Forest** | `0.67` | `0.9600` (`0.940–0.976`) | `0.9509` | `0.9910` | `0.9705` (`0.956–0.983`) | `0.9963` | `0.9982` | `0.0447` | `0.0847` | 151 | 17 | 3 | 329 |
| **XGBoost Classifier** | `0.41` | **`0.9820`** (`0.972–0.992`) | **`0.9792`** | `0.9940` | **`0.9865`** (`0.979–0.994`) | **`0.9994`** | **`0.9997`** | **`0.0104`** | **`0.0185`** | 161 | 7 | 2 | 330 |

---

### Regime B — Strict Registry-Only Tabular Features (`15 Features`, Zero OCR/CV Features, `n_test = 500`)
When all 4 document-image features (`doc_plot_discrepancy_flag`, `doc_area_discrepancy_flag`, `cv_seal_absent_flag`, `cv_visual_anomaly_score`) are withheld:

| Model (Regime B: Registry-Only 15 Features) | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Brier | ECE | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline** | `0.50` | `0.6640` | `0.6640` | `1.0000` | `0.7981` | `0.5000` | `0.6640` | `0.3360` | `0.3360` | 0 | 168 | 0 | 332 |
| **Deterministic Rule Baseline (Registry-Only)** | N/A | `0.8100` | **`0.9100`** | `0.7922` | `0.8470` | N/A | N/A | N/A | N/A | 142 | 26 | 69 | 263 |
| **Logistic Regression** | `0.32` | `0.9000` | `0.8832` | `0.9789` | `0.9286` | `0.9571` | `0.9776` | `0.0799` | `0.0688` | 125 | 43 | 7 | 325 |
| **Random Forest** | `0.60` | `0.9200` | `0.9033` | `0.9849` | `0.9424` | `0.9651` | `0.9812` | `0.0624` | **`0.0384`** | 133 | 35 | 5 | 327 |
| **XGBoost Classifier** | `0.22` | **`0.9220`** | `0.8949` | **`1.0000`** | **`0.9445`** | **`0.9682`** | **`0.9837`** | **`0.0611`** | `0.0458` | 129 | 39 | 0 | 332 |

---

### Regime D — Leave-One-Fraud-Family-Out (LOFFO) Cross-Validation (`8 Folds`)
Holding out all `208` instances of one fraud scenario category from training per fold (`208` unseen fraud cases + `126` held-out legitimate cases):

| Held-Out Unseen Fraud Category (`n=208`) | Rule Engine Recall (`19 Feats`) | Logistic Reg. Recall (`19 Feats`) | Random Forest Recall (`19 Feats`) | XGBoost Recall (`19 Feats`) | Random Forest Recall (`15 Reg-Only`) | XGBoost Recall (`15 Reg-Only`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ALTERED_OWNER_NAME` | **`1.0000`** | `0.8702` | `0.9231` | `0.5721` | `0.9712` | `0.9615` |
| `ALTERED_PLOT_NUMBER` | **`1.0000`** | `0.3510` | `0.6923` | `0.3365` | `1.0000` | `0.8702` |
| `BROKEN_CHAIN_OF_TITLE` | **`1.0000`** | `0.5288` | `0.7644` | `0.4760` | `0.9904` | `0.9327` |
| `CONFLICTING_DOUBLE_SALE` | **`1.0000`** | `0.7308` | `0.9952` | `0.8125` | `1.0000` | `0.9567` |
| `EXAGGERATED_LAND_AREA` | **`1.0000`** | `0.9519` | `0.9904` | `0.8942` | `1.0000` | `0.9663` |
| `SYNTHETIC_SEAL_ABSENT_SUSPICIOUS` | **`1.0000`** | `0.3894` | `0.7548` | `0.4087` | `1.0000` | `0.8942` |
| `UNREGISTERED_MUTATION_MISMATCH` | **`1.0000`** | `0.7885` | `1.0000` | `0.4952` | `1.0000` | `1.0000` |
| `VISUAL_OVERLAY_TAMPERING` | **`1.0000`** | `0.3558` | `0.5865` | `0.3702` | `0.9904` | `0.8702` |
| **Mean Recall on Unseen Fraud Family** | **`1.0000`** | **`0.6208`** | **`0.8383`** | **`0.5457`** | **`0.9940`** | **`0.9315`** |

- **Scientific Insight**: Compared to the pre-remediation dataset (`0.0427` mean LOFFO recall), multi-feature correlated signals increase unseen-fraud ML recall to **`54.57%–83.83%`** (`88.10%–99.40%` on registry-only features). However, when a specific document-level anomaly (`ALTERED_PLOT_NUMBER`, `VISUAL_OVERLAY_TAMPERING`, `SYNTHETIC_SEAL_ABSENT_SUSPICIOUS`) is absent from training data, supervised 19-feature models still miss `25%–66%` of cases without a secondary correlate, whereas the **Deterministic Statutory Rule Engine achieves `100.0%` recall across all 8 unseen fraud families**.

---

### Regime E — Noisy Operational Simulation (`n_test = 500`)
Simulating heightened administrative lag (delayed mutations, pre-digital partition deeds) and degraded scan OCR/CV noise:

| Model (Regime E: Noisy Operational) | Threshold | Accuracy (95% CI) | Precision | Recall | F1-Score (95% CI) | ROC-AUC | PR-AUC | Brier | ECE | TN | FP | FN | TP |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Rule Baseline** | N/A | `0.9020` | `0.8794` | `0.9880` | `0.9305` | N/A | N/A | N/A | N/A | 123 | 45 | 4 | 328 |
| **Logistic Regression** | `0.36` | `0.9300` (`0.904–0.950`) | `0.9183` | `0.9819` | `0.9491` (`0.931–0.965`) | `0.9811` | `0.9897` | `0.0469` | `0.0310` | 139 | 29 | 6 | 326 |
| **Random Forest** | `0.64` | `0.9420` (`0.920–0.960`) | `0.9268` | `0.9910` | `0.9578` (`0.942–0.971`) | `0.9753` | `0.9858` | `0.0584` | `0.0618` | 142 | 26 | 3 | 329 |
| **XGBoost Classifier** | `0.46` | **`0.9600`** (`0.942–0.976`) | **`0.9483`** | **`0.9940`** | **`0.9706`** (`0.958–0.982`) | **`0.9904`** | **`0.9944`** | **`0.0298`** | **`0.0278`** | 150 | 18 | 2 | 330 |

#### Per-Scenario Category Accuracy Breakdown Across Regimes (`n_test = 500`)

| Scenario Category | Ground Truth | Test Count | Regime A&C Rule Engine | Regime A&C XGBoost | Regime B Reg-Only Rule | Regime B Reg-Only XGB | Regime E Noisy Rule | Regime E Noisy LR | Regime E Noisy RF | Regime E Noisy XGB |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `LEGITIMATE_CORRECTION_DEED` | `0` (Legit) | 42 | `0.9048` | `1.0000` | `0.9048` | `0.9762` | `0.8095` | `0.9524` | `1.0000` | `1.0000` |
| `LEGITIMATE_INHERITANCE` | `0` (Legit) | 42 | `0.8810` | `0.9762` | `0.8810` | `1.0000` | `0.8095` | `0.9762` | `1.0000` | `0.9762` |
| `LEGITIMATE_NORMAL_SALE` | `0` (Legit) | 42 | `0.7381` | `0.8571` | `0.7381` | `0.0952` | `0.6429` | `0.5000` | `0.3810` | `0.5952` |
| `LEGITIMATE_PARTIAL_SUBDIVISION` | `0` (Legit) | 42 | `0.8571` | `1.0000` | `0.8571` | `1.0000` | `0.6667` | `0.8810` | `1.0000` | `1.0000` |
| `ALTERED_OWNER_NAME` | `1` (Fraud) | 41 | `1.0000` | `0.9512` | `1.0000` | `1.0000` | `1.0000` | `0.9756` | `0.9756` | `1.0000` |
| `ALTERED_PLOT_NUMBER` | `1` (Fraud) | 41 | `1.0000` | `1.0000` | `0.4390` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `BROKEN_CHAIN_OF_TITLE` | `1` (Fraud) | 41 | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `CONFLICTING_DOUBLE_SALE` | `1` (Fraud) | 42 | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `0.9762` | `0.9762` | `0.9762` |
| `EXAGGERATED_LAND_AREA` | `1` (Fraud) | 41 | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `0.9268` | `1.0000` | `1.0000` | `1.0000` |
| `SYNTHETIC_SEAL_ABSENT_SUSPICIOUS` | `1` (Fraud) | 42 | `1.0000` | `1.0000` | `0.4524` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `UNREGISTERED_MUTATION_MISMATCH` | `1` (Fraud) | 42 | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `0.9762` | `0.9524` | `0.9762` | `0.9762` |
| `VISUAL_OVERLAY_TAMPERING` | `1` (Fraud) | 42 | `1.0000` | `1.0000` | `0.4524` | `1.0000` | `1.0000` | `0.9524` | `1.0000` | `1.0000` |
