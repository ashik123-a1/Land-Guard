# LandGuard Phase 5 — Multi-Alteration Computer Vision Audit & Validation Report

## 1. Executive Summary

This report documents the independent audit, algorithmic enhancement, and benchmark evaluation of the LandGuard Computer Vision (CV) document inspection modules across the full **`n = 600` canonical synthetic image benchmark** (`data/full/images/`) and **`n = 50` multi-alteration tampered document samples** spanning **4 distinct alteration mechanisms** (`paste_over_plot`, `copy_move_clone`, `localized_erasure_blur`, and `dark_ink_overwrite`) at varied spatial coordinates.

All detectors in [`src/landguard_vision/signature_presence.py`](file:///F:/land%20gurd/src/landguard_vision/signature_presence.py), [`src/landguard_vision/seal_presence.py`](file:///F:/land%20gurd/src/landguard_vision/seal_presence.py), and [`src/landguard_vision/visual_anomaly_baseline.py`](file:///F:/land%20gurd/src/landguard_vision/visual_anomaly_baseline.py) operate strictly on image pixel intensities and contours. **Zero document category metadata, filename shortcuts, or ground-truth flags are passed to the vision detectors at inference time.**

| Vision Subsystem | Metric | Pre-Mission Baseline | Current Verified Benchmark | Absolute Improvement |
| :--- | :--- | :---: | :---: | :---: |
| **Signature Presence (Assisted Box, `n=600`)** | Accuracy | `0.6900` | **`0.9817`** | **`+29.17 pp`** |
| **Signature Presence (Assisted Box, `n=600`)** | Precision | `0.6017` | **`0.9623`** | **`+36.06 pp`** |
| **Signature Presence (Assisted Box, `n=600`)** | Recall | `1.0000` (`281/281`) | **`1.0000` (`281/281`)** | `0.00 pp` (100% preserved) |
| **Signature Presence (Assisted Box, `n=600`)** | F1 Score | `0.7513` | **`0.9808`** | **`+22.95 pp`** |
| **Signature Presence (Assisted Box, `n=600`)** | False Positives (`FP`) | `186` | **`11`** | **`-175 FPs` (`-94.1%`)** |
| **Signature Presence (Unassisted Quadrant, `n=600`)** | Accuracy | `0.3783` | **`0.6533`** | **`+27.50 pp`** |
| **Signature Presence (Unassisted Quadrant, `n=600`)** | Precision | `0.2830` | **`0.7704`** | **`+48.74 pp`** |
| **Signature Presence (Unassisted Quadrant, `n=600`)** | Recall | `0.2135` | **`0.3701`** | **`+15.66 pp`** |
| **Signature Presence (Unassisted Quadrant, `n=600`)** | F1 Score | `0.2434` | **`0.5000`** | **`+25.66 pp`** |
| **Official Seal Presence (`n=600`)** | Accuracy / F1 | `0.9967` / `0.9980` | **`0.9950` / `0.9971`** | Verified (`TP=510, FP=0, TN=87, FN=3`) |
| **Visual Anomaly (Multi-Alteration Recall, `n=50`)** | Detection Recall | `0.6400` (`32/50`) | **`0.9600` (`48/50`)** | **`+32.00 pp`** |
| **Visual Anomaly (Clean Dataset FPR, `n=600`)** | False Positive Rate | `0.0167` (`10/600`) | **`0.0083` (`5/600`)** | **`-0.84 pp` (`-50.0%` FPs)** |
| **Visual Anomaly (Clean Digital FPR, `n=40`)** | False Positive Rate | `0.0000` (`0/40`) | **`0.0000` (`0/40`)** | `0.00 pp` (`0%` FPR preserved) |

---

## 2. Mandatory Legal & Technical Distinction: Presence vs. Authenticity

> [!IMPORTANT]
> **Presence Detection $\neq$ Authenticity Verification**:
> - **Signature Presence Detection** evaluates only whether cursive/handwritten ink strokes of sufficient contrast, bounding geometry, and stroke continuity exist inside the signature block region. It **does NOT** verify handwriting biometric authenticity, signatory identity, or legal execution validity.
> - **Seal Presence Detection** evaluates only circular/emblematic stamp boundary contour geometry and ink distribution. It **does NOT** verify official government issuance, seal registration, or legal authorization.
> - **Visual Anomaly Detection** identifies rectangular paste-over edges, copy-move cloned patches, localized erasure/whitening patches, and heavy dark-ink overwrites. It is a triage aid for human document examiners, not standalone proof of forgery.

---

## 3. Detailed Benchmark Results (`reports/vision_validation_metrics.json`)

### 3.1 Signature Presence Detection — Assisted vs. Unassisted (`n = 600`)

| Mode | TP | FP | TN | FN | Accuracy | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Assisted Candidate Region (Before)** | `281` | `186` | `133` | `0` | `0.6900` | `0.6017` | `1.0000` | `0.7513` |
| **Assisted Candidate Region (After)** | **`281`** | **`11`** | **`308`** | **`0`** | **`0.9817`** | **`0.9623`** | **`1.0000`** | **`0.9808`** |
| **Unassisted Bottom Quadrant (Before)** | `60` | `152` | `167` | `221` | `0.3783` | `0.2830` | `0.2135` | `0.2434` |
| **Unassisted Bottom Quadrant (After)** | **`104`** | **`31`** | **`288`** | **`177`** | **`0.6533`** | **`0.7704`** | **`0.3701`** | **`0.5000`** |

#### Breakdown by Document Category (Assisted Candidate Region, After Repair)

| Document Category | Total (`n`) | TP | FP | TN | FN | Accuracy | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `SALE_DEED` | `150` | `128` | `3` | `19` | `0` | `0.9800` | `0.9771` | `1.0000` | `0.9884` |
| `KHATIAN_PORCHA` | `120` | `0` | `0` | `120` | `0` | `1.0000` | `0.0000`* | `0.0000`* | `0.0000`* |
| `MUTATION_RECORD` | `120` | `102` | `2` | `16` | `0` | `0.9833` | `0.9808` | `1.0000` | `0.9903` |
| `TAX_RECEIPT` | `90` | `0` | `0` | `90` | `0` | `1.0000` | `0.0000`* | `0.0000`* | `0.0000`* |
| `PARCEL_MAP` | `60` | `0` | `4` | `56` | `0` | `0.9333` | `0.0000`* | `0.0000`* | `0.0000`* |
| `APPLICATION_COMPLAINT` | `60` | `51` | `2` | `7` | `0` | `0.9667` | `0.9623` | `1.0000` | `0.9808` |
| **Total / Overall** | **`600`** | **`281`** | **`11`** | **`308`** | **`0`** | **`0.9817`** | **`0.9623`** | **`1.0000`** | **`0.9808`** |

---

### 3.2 Official Seal Presence Detection (`n = 600`)

| Document Category | Total (`n`) | TP | FP | TN | FN | Accuracy | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `SALE_DEED` | `150` | `135` | `0` | `15` | `0` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `KHATIAN_PORCHA` | `120` | `120` | `0` | `0` | `0` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `MUTATION_RECORD` | `120` | `108` | `0` | `12` | `0` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `TAX_RECEIPT` | `90` | `90` | `0` | `0` | `0` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `PARCEL_MAP` | `60` | `57` | `0` | `0` | `3` | `0.9500` | `1.0000` | `0.9500` | `0.9744` |
| `APPLICATION_COMPLAINT` | `60` | `0` | `0` | `60` | `0` | `1.0000` | `0.0000`* | `0.0000`* | `0.0000`* |
| **Total / Overall** | **`600`** | **`510`** | **`0`** | **`87`** | **`3`** | **`0.9950`** | **`1.0000`** | **`0.9942`** | **`0.9971`** |

---

### 3.3 Multi-Alteration Visual Anomaly Detection (`n = 50` Altered Across 4 Mechanisms, `n = 600` Clean)

#### Breakdown by Alteration Mechanism (`n = 50`)
| Alteration Mechanism | Description | Tested | Detected | Detection Recall |
| :--- | :--- | :---: | :---: | :---: |
| `paste_over_plot` | Rectangular bright patch pasted over plot/area schedule with overwritten digits | `13` | `13` | **`1.0000` (`100.0%`)** |
| `copy_move_clone` | Cloned rectangular paper patch copied from upper-right margin to overwrite schedule | `13` | `11` | **`0.8462` (`84.6%`)** |
| `localized_erasure_blur` | Localized chemical/abrasion whitening + blur patch with re-typed digits | `12` | `12` | **`1.0000` (`100.0%`)** |
| `dark_ink_overwrite` | Heavy solid dark-ink redaction/strike-over bar (`fill=(18,18,18)`) over text | `12` | `12` | **`1.0000` (`100.0%`)** |
| **Total Multi-Alteration Recall** | **4 Alteration Mechanisms at Varied Coordinates** | **`50`** | **`48`** | **`0.9600` (`96.0%`)** |

#### Breakdown by Document Category (`n = 50` Altered, `n = 600` Clean)
| Evaluation Split / Category | Tested | Detected | Recall / False Positive Rate |
| :--- | :---: | :---: | :---: |
| **Altered: `SALE_DEED`** | `10` | `10` | **`1.0000` (`100.0%` Recall)** |
| **Altered: `KHATIAN_PORCHA`** | `10` | `9` | **`0.9000` (`90.0%` Recall)** |
| **Altered: `MUTATION_RECORD`** | `10` | `10` | **`1.0000` (`100.0%` Recall)** |
| **Altered: `TAX_RECEIPT`** | `10` | `10` | **`1.0000` (`100.0%` Recall)** |
| **Altered: `PARCEL_MAP`** | `8` | `8` | **`1.0000` (`100.0%` Recall)** |
| **Altered: `APPLICATION_COMPLAINT`** | `2` | `1` | `0.5000` (`50.0%` Recall) |
| **Clean Digital Subset (`n=40`)** | `40` | `0` FPs | **`0.0000` (`0.00%` FPR)** |
| **All Canonical Clean (`n=600`)** | `600` | `5` FPs | **`0.0083` (`0.83%` FPR)** |
