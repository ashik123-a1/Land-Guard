# Evaluation Plan: LandGuard Benchmark Protocol

## 1. Objectives & Benchmark Scope
The LandGuard evaluation framework establishes an objective, transparent, and reproducible empirical benchmark for assessing:
1. **Bilingual Document Vision & OCR Readability**: Character Error Rate (CER), Word Error Rate (WER), and structured field extraction Accuracy, Precision, Recall, and F1 across Bengali (`U+0980..U+09FF`) and English land documents.
2. **Visual Region Presence & Multi-Alteration Tampering**: Detection Accuracy, Precision, Recall, F1, and False Positive Rate for official seals, signature placeholders (assisted vs. unassisted), and four distinct document alteration mechanisms (`paste_over_plot`, `copy_move_clone`, `localized_erasure_blur`, `dark_ink_overwrite`).
3. **Structured & Coupled Machine Learning Risk Classification**: Binary fraud-risk discrimination capability, probability calibration (Brier Score, ECE), and 95% bootstrap confidence intervals across XGBoost, Random Forest, Logistic Regression, Majority Baseline, and the Deterministic Statutory Rule Engine.
4. **Leakage & Generalization Resistance Across Five Validation Regimes**: Strict multi-entity group-disjoint partitioning and Leave-One-Fraud-Family-Out (LOFFO) cross-validation.

---

## 2. Predefined Metrics

### 2.1 Optical Character Recognition (OCR)
- **Character Error Rate (CER)**: Levenshtein distance between ground-truth character string and OCR output divided by ground-truth character length, computed separately for Overall, English (`ASCII`), and Bangla (`U+0980..U+09FF`):
  $$\text{CER} = \frac{\text{Levenshtein}(T_{\text{ref}}, T_{\text{hyp}})}{|T_{\text{ref}}|}$$
- **Word Error Rate (WER)**: Word-level edit distance normalized by word count:
  $$\text{WER} = \frac{\text{EditDistance}_{\text{words}}(W_{\text{ref}}, W_{\text{hyp}})}{|W_{\text{ref}}|}$$
- **Structured Field Extraction Metrics**: Exact Match Accuracy, Precision, Recall, and F1-Score for key legal identifiers (`deed_number`, `dag_plot_number`, `khatian_number`, `transferred_area_decimal`).
- **Breakdown Dimensions**: Stratified across 6 document categories (`8` per category) and 8 evaluated image quality degradation classes (`6` per class).

### 2.2 Fraud-Risk Machine Learning & Calibration
- **Precision, Recall, F1-Score, Accuracy**: Evaluated at the optimal F1 decision threshold selected strictly on the held-out Validation split (`n_val = 300`).
- **ROC-AUC & PR-AUC**: Area under the ROC and Precision-Recall curves.
- **Probability Calibration**:
  - **Brier Score**: Mean squared error between predicted probability $\hat{p}_i$ and binary outcome $y_i$.
  - **Expected Calibration Error (ECE)**: Weighted average absolute difference between empirical accuracy and mean confidence across 10 probability bins.
- **95% Bootstrap Confidence Intervals**: 400-iteration stratified bootstrap intervals for Accuracy, Precision, Recall, F1-Score, and PR-AUC on the held-out test set (`n_test = 500`).

### 2.3 Visual Region Presence & Tampering
- **Signature Presence (`Assisted Candidate Box` vs. `Unassisted Quadrant`)**: Accuracy, Precision, Recall, F1, and Confusion Matrix (`TP, FP, TN, FN`) across `600` canonical images.
- **Seal Presence**: Circular contour geometry and ink hue verification across `600` canonical images.
- **Visual Anomaly Detection**: False Positive Rate on `40` `clean_digital` images and all `600` unaltered images; Detection Recall across `50` altered samples spanning 4 alteration mechanisms (`paste_over_plot`, `copy_move_clone`, `localized_erasure_blur`, `dark_ink_overwrite`) at varied spatial coordinates.

---

## 3. Five-Regime ML Validation Protocol & Leakage Safeguards

### 3.1 Multi-Entity Group-Disjoint Partitioning (`n = 2,500` Scenarios)
- **Train Split (`68%`, `n = 1,700`)** — 17 disjoint `template_cohort` groups (`10,200` disjoint owners).
- **Validation Split (`12%`, `n = 300`)** — 3 disjoint `template_cohort` groups (`1,800` disjoint owners), used strictly for early stopping and decision threshold selection.
- **Test Split (`20%`, `n = 500`)** — 5 disjoint `template_cohort` groups (`3,000` disjoint owners; `332` fraud-risk, `168` legitimate).
- **Verified Zero Overlap (`0`)**: `assert_disjoint_scenarios` verifies `0` overlap across `template_cohort`, `parcel_id`, `primary_seller_id`, and `scenario_id`.

### 3.2 Five Validation Regimes
1. **Regime A & C — Multi-Entity Group-Disjoint + Coupled OCR/CV Document Evidence (`19` Features)**: Evaluates all 15 registry features plus 4 observable OCR/CV document evidence features (`doc_plot_discrepancy_flag`, `doc_area_discrepancy_flag`, `cv_seal_absent_flag`, `cv_visual_anomaly_score`).
2. **Regime B — Strict Registry-Only Tabular Features (`15` Features)**: Withholds all 4 document-image features to measure detection performance from structured registry records alone.
3. **Regime D — Leave-One-Fraud-Family-Out (LOFFO) Generalization (`8` Folds)**: Holds out all `208` instances of one fraud scenario category from training per fold to evaluate unseen fraud family generalization.
4. **Regime E — Noisy Operational Simulation (`n_test = 500`)**: Simulates heavy administrative lag (delayed mutations, pre-digital partition deeds) and degraded scan OCR/CV noise.
