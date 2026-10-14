# Experimental Results & Benchmark Evaluation Report

## 1. Executive Summary
This document reports the **actual, empirically measured performance metrics** from the execution of the LandGuard Phase 1 research benchmark following oracle leakage removal, multi-feature dataset regeneration, bilingual (`ben+eng`) Tesseract + RapidOCR integration, renderer-to-annotation text alignment, multi-alteration computer vision upgrades, and explainable risk scoring. All figures, tables, and statistics were produced by running the local pipeline in `F:\land gurd`.

---

## 2. Dataset Release Statistics

| Attribute | Canonical Dataset Metric | Verification Status |
| :--- | :--- | :--- |
| **Total Structured Records** | **100,000** | Verified on disk (`data/full/records/canonical_records.json`) |
| **Fictional Owners** | 15,000 | Verified (disjoint 6-owner cohorts across 2,500 scenarios) |
| **Fictional Land Parcels** | 10,000 | Verified |
| **Historical Khatians (CS, SA, RS, BS)** | 30,000 | Verified |
| **Transactions / Deeds** | 25,000 | Verified (`schemas/transaction.schema.json` enforces zero oracle fields) |
| **Mutation Records** | 10,000 | Verified (`APPROVED` / `PENDING` / `REJECTED`) |
| **Tax Clearance Receipts** | 10,000 | Verified |
| **Designed Experimental Scenarios** | 2,500 | Verified (`1,664` fraud-risk across 8 categories vs `836` legitimate across 4 categories) |
| **Document Images Rendered on Disk** | **600** | Verified in `data/full/images/` (Scalable to 10,000 via CLI; `600` vs `10,000` target explicitly distinguished) |
| **Pilot Document Images** | 60 | Verified in `data/pilot/images/` |
| **Document Categories Represented** | 6 | `SALE_DEED` (150), `KHATIAN_PORCHA` (120), `MUTATION_RECORD` (120), `TAX_RECEIPT` (90), `PARCEL_MAP` (60), `APPLICATION_COMPLAINT` (60) |
| **Prominent Synthetic Watermarks** | 100% Present (`600/600`) | `SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT` on all variants |
| **SHA-256 Checksum Integrity** | 100% Verified (`600/600`) | 0 mismatches across all 600 canonical annotations and 602 manifest entries |
| **JSON Schema Compliance** | 100% Passed (`0` errors) | Verified across all entity schemas (`additionalProperties: false` on transactions) |
| **Multi-Entity Group-Disjoint Split** | Leakage-Free (`0` overlap) | `Train = 1,700`, `Val = 300`, `Test = 500` (`0` overlap across `template_cohort`, `parcel_id`, `primary_seller_id`, and `scenario_id`) |

---

## 3. Bilingual Optical Character Recognition (OCR) Benchmark (`n = 48` Stratified Images)

### 3.1 Four-Stage Progression (`reports/ocr_metrics.json`)
By discovering and activating local `Tesseract v5.4.0.20240606` (`ben.traineddata` + `eng.traineddata`), implementing unshaped Bengali pre-base vowel-matra (`ি`, `ে`, `ৈ`) Unicode order realignment, combining DBNet cell-isolated `RapidOCR` structured ID extraction, and aligning `render_documents.py` / `render_maps.py` ground-truth annotations with the actual rendered canvas text:

| Evaluation Stage | Overall CER | Overall WER | English CER | English WER | Bangla CER (`n=40`) | Bangla WER (`n=40`) | Exact Field Match (`n=80`) | Field Precision / F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Initial Baseline (`ocr_evaluation_report.json`)** | `0.8143` | `0.9389` | `0.8868` | `0.9736` | `1.0000` | `1.0000` | `0.4750` (`38/80`) | N/A |
| **2. RapidOCR English-Only Repair** | `0.7185` | `0.9099` | `0.6021` | `0.9025` | `1.0000` | `1.0000` | `0.8750` (`70/80`) | N/A |
| **3. Bilingual (`ben+eng`) on Original Unaligned GT** | `0.5195` | `0.6572` | `0.5376` | `0.7165` | `0.4719` | `0.6151` | `0.7875` (`63/80`) | `0.8514` / `0.8182` |
| **4. Bilingual (`ben+eng`) on Renderer-Verified GT** | **`0.3702`** | **`0.4955`** | **`0.3598`** | **`0.5086`** | **`0.4435`** | **`0.5641`** | **`0.9000` (`72/80`)** | **`0.9730` / `0.9351`** |

### 3.2 Breakdown by Document Category (`8` Images per Category)
| Document Category | Overall CER (RapidOCR $\rightarrow$ Bilingual) | English CER (RapidOCR $\rightarrow$ Bilingual) | Bangla CER (RapidOCR $\rightarrow$ Bilingual) | Bilingual WER | Key Observation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **PARCEL_MAP** | `0.9227` $\rightarrow$ **`0.2208`** | `0.9227` $\rightarrow$ **`0.2202`** | `0.0000` (No BN) | **`0.3523`** | Renderer-aligned GT + target plot & area extraction |
| **MUTATION_RECORD** | `0.6043` $\rightarrow$ **`0.3261`** | `0.3539` $\rightarrow$ **`0.2641`** | `1.0000` $\rightarrow$ **`0.4311`** | **`0.4386`** | Bilingual AC Land order sheets & case numbers |
| **TAX_RECEIPT** | `0.6873` $\rightarrow$ **`0.3293`** | `0.4959` $\rightarrow$ **`0.3090`** | `1.0000` $\rightarrow$ **`0.3734`** | **`0.4942`** | Union Land Office dakhila amounts & plot IDs |
| **APPLICATION_COMPLAINT** | `0.7997` $\rightarrow$ **`0.3334`** | `0.6777` $\rightarrow$ **`0.3688`** | `1.0000` $\rightarrow$ **`0.3917`** | **`0.5093`** | Dense Bengali narrative petition + applicant NID |
| **SALE_DEED** | `0.5669` $\rightarrow$ **`0.3778`** | `0.5103` $\rightarrow$ **`0.3772`** | `1.0000` $\rightarrow$ **`0.3581`** | **`0.4784`** | Bilingual seller/buyer schedules, deed & plot numbers |
| **KHATIAN_PORCHA** | `0.7303` $\rightarrow$ **`0.6338`** | `0.6523` $\rightarrow$ **`0.6197`** | `1.0000` $\rightarrow$ **`0.6630`** | **`0.7004`** | 6-column tabular grid; DBNet cell isolation extracts `7/8` Khatian IDs & plots |

### 3.3 Breakdown by Image Quality Variant (`6` Images per Quality Class)
| Degradation Variant | Overall CER (RapidOCR $\rightarrow$ Bilingual) | English CER (RapidOCR $\rightarrow$ Bilingual) | Bangla CER (RapidOCR $\rightarrow$ Bilingual) | Bilingual WER |
| :--- | :---: | :---: | :---: | :---: |
| `low_contrast` | `0.6661` $\rightarrow$ **`0.2412`** | `0.4839` $\rightarrow$ **`0.2171`** | `0.8333` $\rightarrow$ **`0.2671`** | **`0.3658`** |
| `mild_rotation` | `0.7273` $\rightarrow$ **`0.2609`** | `0.5465` $\rightarrow$ **`0.2421`** | `0.8333` $\rightarrow$ **`0.2399`** | **`0.3750`** |
| `grayscale_scan` | `0.7757` $\rightarrow$ **`0.2641`** | `0.7011` $\rightarrow$ **`0.2685`** | `0.8333` $\rightarrow$ **`0.2676`** | **`0.3636`** |
| `skewed_scan` | `0.7053` $\rightarrow$ **`0.2703`** | `0.5401` $\rightarrow$ **`0.2568`** | `0.8333` $\rightarrow$ **`0.2549`** | **`0.3847`** |
| `clean_digital` | `0.6704` $\rightarrow$ **`0.2731`** | `0.4630` $\rightarrow$ **`0.2350`** | `0.8333` $\rightarrow$ **`0.3143`** | **`0.3700`** |
| `clean_scan` | `0.6984` $\rightarrow$ **`0.2905`** | `0.5393` $\rightarrow$ **`0.2567`** | `0.8333` $\rightarrow$ **`0.3061`** | **`0.3896`** |
| `low_resolution` | `0.7311` $\rightarrow$ **`0.5625`** | `0.7684` $\rightarrow$ **`0.6338`** | `0.8333` $\rightarrow$ **`0.5778`** | `0.8059` |
| `uneven_illumination` | `0.7740` $\rightarrow$ **`0.7991`** | `0.7747` $\rightarrow$ **`0.7686`** | `0.8333` $\rightarrow$ **`0.7288`** | `0.9095` |

---

## 4. Computer Vision: Signature, Seal & Multi-Alteration Anomaly Detection (`n = 600` Clean, `n = 50` Altered)

| Evaluation Module | Accuracy (Before $\rightarrow$ After) | Precision (Before $\rightarrow$ After) | Recall (Before $\rightarrow$ After) | F1-Score (Before $\rightarrow$ After) | Confusion Matrix After (`TP / FP / TN / FN`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Official Seal Presence (`n=600`)** | **`99.50%`** | **`100.0%`** | **`99.42%`** | **`0.9971`** | `TP=510, FP=0, TN=87, FN=3` |
| **Signature Presence (Assisted Box, `n=600`)** | `69.00%` $\rightarrow$ **`98.17%`** | `60.17%` $\rightarrow$ **`96.23%`** | `100.0%` $\rightarrow$ **`100.0%`** | `0.7513` $\rightarrow$ **`0.9808`** | `TP=281, FP=11, TN=308, FN=0` |
| **Signature Presence (Unassisted Quad, `n=600`)** | `37.83%` $\rightarrow$ **`65.33%`** | `28.30%` $\rightarrow$ **`77.04%`** | `21.35%` $\rightarrow$ **`37.01%`** | `0.2434` $\rightarrow$ **`0.5000`** | `TP=104, FP=31, TN=288, FN=177` |
| **Visual Anomaly (4-Mechanism Recall, `n=50`)** | N/A | N/A | `64.00%` $\rightarrow$ **`96.00%` (`48/50`)** | N/A | `13/13` paste-over, `11/13` clone, `12/12` erasure, `12/12` ink |
| **Visual Anomaly (Clean Dataset FPR, `n=600`)** | **`99.17%` Spec.** | N/A | **`0.83%` FPR** (was `1.67%`) | N/A | `5 / 600` FPs overall (`0 / 40` on `clean_digital`) |

---

## 5. Machine Learning Fraud-Risk Model Benchmark Across Five Validation Regimes (`n_test = 500`)

| Validation Regime (`Test n = 500`, `332` Fraud / `168` Legit) | Rule Engine Acc / F1 (`Rec`) | Logistic Reg. Acc / F1 (`PR-AUC`) | Random Forest Acc / F1 (`PR-AUC`) | XGBoost Acc / F1 (`PR-AUC`, `ECE`) | Key Scientific Finding |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Regime A & C: Group-Disjoint + Coupled Doc Evidence (`19 Feats`)** | `0.9480` / `0.9623` (`1.0000`) | `0.9760` / `0.9821` (`0.9993`) | `0.9600` / `0.9705` (`0.9982`) | **`0.9820` / `0.9865`** (`0.9997`, `ECE=0.0185`) | Zero oracle flags; realistic administrative ambiguity yields non-trivial `0.96–0.986` F1 |
| **Regime B: Strict Registry-Only (`15 Feats`, Zero OCR/CV)** | `0.8100` / `0.8470` (`0.7922`) | `0.9000` / `0.9286` (`0.9776`) | `0.9200` / `0.9424` (`0.9812`) | **`0.9220` / `0.9445`** (`0.9837`, `ECE=0.0458`) | Secondary economic/tax correlates allow ML to flag `97.9%–100%` of risks when doc features are absent |
| **Regime D: Leave-One-Fraud-Family-Out (`8 Folds`)** | **`1.0000` Mean Rec** | `0.6208` Mean Rec | `0.8383` Mean Rec | `0.5457` Mean Rec (`0.9315` Reg-Only) | Multi-feature correlates raise ML unseen recall from `4.27%` $\rightarrow$ `54.6%–83.8%`, while Rule Engine achieves `100.0%` |
| **Regime E: Noisy Operational Simulation (`n=500`)** | `0.9020` / `0.9305` (`0.9880`) | `0.9300` / `0.9491` (`0.9897`) | `0.9420` / `0.9578` (`0.9858`) | **`0.9600` / `0.9706`** (`0.9944`, `ECE=0.0278`) | High resilience under heavy administrative lag + degraded scan OCR/CV noise |

---

## 6. Automated Unit & Regression Tests Summary
The test suite consists of **`35` automated unit and regression tests** across `12` test modules in `tests/`:
- `test_data_splits.py` (2 PASSED)
- `test_explainable_risk_and_leakage.py` (6 PASSED)
- `test_ground_truth.py` (1 PASSED)
- `test_image_generation.py` (1 PASSED)
- `test_linked_records.py` (1 PASSED)
- `test_model_pipeline.py` (2 PASSED)
- `test_ocr.py` (4 PASSED)
- `test_schemas.py` (2 PASSED)
- `test_signature_seal.py` (4 PASSED)
- `test_tampering_scenarios.py` (1 PASSED)
- `test_verification_rules.py` (10 PASSED)
- `test_watermarks.py` (1 PASSED)

**Overall Test Result**: **`35 passed in 1.43s` (`100%` pass rate)**.
