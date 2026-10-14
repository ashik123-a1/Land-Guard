# Evidence Index: LandGuard Hackathon Verification Matrix

This index maps every major engineering claim and benchmark result to its concrete, reproducible artifact in the repository.

---

## 1. Safety, Privacy & Synthetic Data Provenance

| Judge Claim | Concrete Evidence Artifact | Verification Link / Location |
| :--- | :--- | :--- |
| **All entities are fictional; zero real PII or oracle fields** | Canonical Dataset & Schemas | [DATA_CARD.md](file:///F:/land%20gurd/DATA_CARD.md), [transaction.schema.json](file:///F:/land%20gurd/schemas/transaction.schema.json) |
| **Mandatory watermark on every image (`600/600`)** | Validation Report & Images | [dataset_validation_report.json](file:///F:/land%20gurd/evidence/metrics/dataset_validation_report.json), [evidence/examples](file:///F:/land%20gurd/evidence/examples) |
| **SHA-256 Checksums for all `602` tracked files (`600/600` images)** | Dataset Manifest | [dataset_manifest.json](file:///F:/land%20gurd/data/manifests/dataset_manifest.json) |

---

## 2. Dataset Scale & Canonical Entity Structure

| Judge Claim | Concrete Evidence Artifact | Verification Link / Location |
| :--- | :--- | :--- |
| **100,000 structured land records generated** | Canonical Records Register | [canonical_records.json](file:///F:/land%20gurd/data/full/records/canonical_records.json), [DATA_CARD.md](file:///F:/land%20gurd/DATA_CARD.md) |
| **2,500 designed scenarios (`1,664` fraud, `836` legit)** | Scenario Counts Register | [canonical_records.json](file:///F:/land%20gurd/data/full/records/canonical_records.json) |
| **Disjoint 6-owner cohorts & 25 template cohorts (`Train=1,700, Val=300, Test=500`, `0` overlap)** | Independent ML Metrics | [independent_ml_metrics.json](file:///F:/land%20gurd/evidence/metrics/independent_ml_metrics.json) |
| **600 rendered benchmark images (`10,000` scalable capacity)** | Image Directory & Manifest | [dataset_manifest_summary.json](file:///F:/land%20gurd/evidence/metrics/dataset_manifest_summary.json) |

---

## 3. Bilingual Optical Character Recognition (OCR) Benchmark (`n = 48`)

| Judge Claim | Concrete Evidence Artifact | Verification Link / Location |
| :--- | :--- | :--- |
| **Overall CER `0.8143` $\rightarrow$ `0.3702`; English CER `0.8868` $\rightarrow$ `0.3598`; Bangla CER `1.0000` $\rightarrow$ `0.4435`** | OCR Repair Report & Metrics | [ocr_repair_report.md](file:///F:/land%20gurd/reports/ocr_repair_report.md), [ocr_metrics.json](file:///F:/land%20gurd/evidence/metrics/ocr_metrics.json) |
| **Structured Field Extraction: `90.00%` Exact Match (`72/80`), `97.30%` Precision (`72/74`), `0.9351` F1** | OCR Evaluation Report | [ocr_evaluation_report.json](file:///F:/land%20gurd/evidence/metrics/ocr_evaluation_report.json) |
| **Per-image OCR ground truth, output & extracted fields** | OCR Predictions CSV & JSON | [ocr_predictions.csv](file:///F:/land%20gurd/evidence/metrics/ocr_predictions.csv), [ocr_side_by_side_examples.json](file:///F:/land%20gurd/evidence/metrics/ocr_side_by_side_examples.json) |
| **OCR breakdown charts by Category & Quality** | Comparison Charts | [ocr_metrics_by_category.png](file:///F:/land%20gurd/evidence/figures/ocr_metrics_by_category.png), [ocr_metrics_by_quality.png](file:///F:/land%20gurd/evidence/figures/ocr_metrics_by_quality.png) |

---

## 4. Visual Verification & Multi-Alteration Tampering (`n = 600` Clean, `n = 50` Altered)

| Judge Claim | Concrete Evidence Artifact | Verification Link / Location |
| :--- | :--- | :--- |
| **Seal Presence Detection: `99.50%` Accuracy, `100.0%` Precision, `99.42%` Recall, `0.9971` F1 (`TP=510, FP=0, TN=87, FN=3`)** | Vision Validation Report & JSON | [vision_validation_report.md](file:///F:/land%20gurd/reports/vision_validation_report.md), [signature_seal_evaluation.json](file:///F:/land%20gurd/evidence/metrics/signature_seal_evaluation.json) |
| **Signature Detection (Assisted): `98.17%` Accuracy, `96.23%` Precision, `100.0%` Recall, `0.9808` F1 (`FP: 186` $\rightarrow$ `11`)** | Vision Validation Metrics | [vision_validation_metrics.json](file:///F:/land%20gurd/evidence/metrics/vision_validation_metrics.json) |
| **Signature Detection (Unassisted): `65.33%` Accuracy, `77.04%` Precision, `0.5000` F1 (was `37.83%` Acc)** | Vision Validation Metrics | [vision_validation_metrics.json](file:///F:/land%20gurd/evidence/metrics/vision_validation_metrics.json) |
| **Multi-Alteration Visual Tampering: `96.00%` Recall (`48/50` across 4 mechanisms), `0.00%` Clean Digital FPR (`0/40`), `0.83%` Overall FPR (`5/600`)** | Anomaly Evaluation Metrics | [vision_validation_report.md](file:///F:/land%20gurd/reports/vision_validation_report.md), [vision_detection_examples.json](file:///F:/land%20gurd/evidence/metrics/vision_detection_examples.json) |
| **Vision Performance Chart** | Matplotlib Bar Chart | [signature_seal_anomaly_performance.png](file:///F:/land%20gurd/evidence/figures/signature_seal_anomaly_performance.png) |

---

## 5. Machine Learning Fraud-Risk Models & Five-Regime Validation (`n_test = 500`)

| Judge Claim | Concrete Evidence Artifact | Verification Link / Location |
| :--- | :--- | :--- |
| **5-Regime Independent Validation (Group-Disjoint 19-Feat, Registry-Only 15-Feat, LOFFO 8-Fold, Noisy Operational)** | Independent ML Validation Report | [independent_ml_validation.md](file:///F:/land%20gurd/reports/independent_ml_validation.md), [independent_ml_metrics.json](file:///F:/land%20gurd/evidence/metrics/independent_ml_metrics.json) |
| **19-Feature Production Availability & Anti-Leakage Audit** | Feature Availability & Leakage JSON | [feature_availability_audit.csv](file:///F:/land%20gurd/evidence/metrics/feature_availability_audit.csv), [leakage_audit_report.json](file:///F:/land%20gurd/evidence/metrics/leakage_audit_report.json) |
| **Scenario-Level Predictions & Calibration Metrics (`Brier`, `ECE`, `95% CI`)** | Predictions CSV & Model Comparison | [independent_ml_predictions.csv](file:///F:/land%20gurd/evidence/metrics/independent_ml_predictions.csv), [model_comparison.json](file:///F:/land%20gurd/evidence/metrics/model_comparison.json) |
| **Explainable Hybrid Risk Scoring Engine** | Source Module & Unit Tests | [explainable_risk.py](file:///F:/land%20gurd/src/landguard_models/explainable_risk.py), [test_explainable_risk_and_leakage.py](file:///F:/land%20gurd/tests/test_explainable_risk_and_leakage.py) |

---

## 6. Reproducibility, Readiness & Test Suite

| Judge Claim | Concrete Evidence Artifact | Verification Link / Location |
| :--- | :--- | :--- |
| **`35 / 35` Unit & Regression Tests Passing (`100%` Pass Rate)** | Pytest Test Suite & Execution Log | [tests/](file:///F:/land%20gurd/tests), [reproducible_execution_log.json](file:///F:/land%20gurd/evidence/metrics/reproducible_execution_log.json) |
| **Final AI & Main Application Readiness (`READY`)** | Readiness Reports | [FINAL_AI_READINESS.md](file:///F:/land%20gurd/reports/FINAL_AI_READINESS.md), [MAIN_APP_READINESS.md](file:///F:/land%20gurd/reports/MAIN_APP_READINESS.md) |
| **Immutable Pre-Mission Baseline Snapshot** | Baseline Snapshot Directory | [BASELINE_AUDIT.md](file:///F:/land%20gurd/reports/BASELINE_AUDIT.md), [reports/baseline_snapshot/](file:///F:/land%20gurd/reports/baseline_snapshot) |
