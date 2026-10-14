# LandGuard Computer Vision Anomaly Detector Robustness Report

> [!IMPORTANT]
> **Synthetic Benchmark Disclosure & Forensic Boundary**:
> The computer vision physical anomaly detector identifies edge discontinuities, seam boundaries, paste-overs,
> erasure halos, and localized overwrites.
> An anomaly score indicates physical irregularity on the document scan, **not conclusive statutory fraud**.
> Statutory decisions are strictly governed by cadastral title validation rules; visual scores serve as corroborating physical evidence.

---

## 1. Executive Summary & Verification Metrics

| Benchmark Evaluation Dimension | Evaluated Samples | Result | Standard Benchmark Target | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Clean False Positive Rate (FPR)** | 90 | **0.0222** (2/90) | $\le 0.0500$ | PASS |
| **Altered Detection Recall** | 90 | **0.9333** (84/90) | $\ge 0.9000$ | PASS |
| **Altered Detection Precision** | 180 | **0.9767** | $\ge 0.9000$ | PASS |
| **Clean Mean Anomaly Score** | 90 | **0.0178** | $\le 0.0500$ | PASS |
| **Altered Mean Anomaly Score** | 90 | **0.7596** | $\ge 0.7000$ | PASS |

---

## 2. Detection Recall Across 6 Physical Alteration Mechanisms

Evaluated across 6 distinct physical and digital modification mechanisms:

| Alteration Mechanism | Evaluated Count | Detected Count | Detection Recall | Mean Continuous Score |
| :--- | :---: | :---: | :---: | :---: |
| `copy_move_clone` | 15 | 12 | **0.8000** | 0.6488 |
| `dark_ink_overwrite` | 15 | 15 | **1.0000** | 0.8183 |
| `faded_chemical_erasure` | 15 | 13 | **0.8667** | 0.6947 |
| `localized_erasure_blur` | 15 | 14 | **0.9333** | 0.7375 |
| `misaligned_numerical_splice` | 15 | 15 | **1.0000** | 0.8255 |
| `paste_over_plot` | 15 | 15 | **1.0000** | 0.8327 |

### Mechanism Analysis:
1. **`paste_over_plot`**: Whiteout or pasted paper patch over cadastral plot identifier exhibits sharp rectangular border contrast and boundary discontinuity.
2. **`copy_move_clone`**: Cloned graphic or numeric block exhibits micro-seam boundary gradients.
3. **`localized_erasure_blur` & `faded_chemical_erasure`**: Localized bleaching or chemical erasure creates boundary variance shifts and halo edges.
4. **`dark_ink_overwrite`**: Dense localized black ink strikeout/redaction bars exceed localized luminance thresholds without aligning to tabular rows.
5. **`misaligned_numerical_splice`**: Spliced numeric digits with non-standard line boundaries trigger boundary energy accumulation.

---

## 3. False Positive Rate Across Degradation Regimes

Evaluated across un-tampered documents under 15 scanning and mobile photography degradations:

| Image Quality / Degradation Class | Clean Scans Evaluated | False Positives | False Positive Rate | Mean Score |
| :--- | :---: | :---: | :---: | :---: |
| `blur` | 5 | 1 | **0.2000** | 0.1606 |
| `clean_digital` | 6 | 0 | **0.0000** | 0.0000 |
| `clean_scan` | 6 | 0 | **0.0000** | 0.0000 |
| `compression_artifacts` | 8 | 0 | **0.0000** | 0.0000 |
| `cropped_edges` | 8 | 0 | **0.0000** | 0.0000 |
| `grayscale_scan` | 3 | 0 | **0.0000** | 0.0000 |
| `light_noise` | 6 | 0 | **0.0000** | 0.0000 |
| `low_contrast` | 6 | 0 | **0.0000** | 0.0000 |
| `low_resolution` | 5 | 0 | **0.0000** | 0.0000 |
| `mild_rotation` | 7 | 0 | **0.0000** | 0.0000 |
| `mild_stains` | 4 | 1 | **0.2500** | 0.1999 |
| `shadow_phone_photo` | 7 | 0 | **0.0000** | 0.0000 |
| `skewed_scan` | 5 | 0 | **0.0000** | 0.0000 |
| `uneven_illumination` | 9 | 0 | **0.0000** | 0.0000 |
| `wrinkled_paper` | 5 | 0 | **0.0000** | 0.0000 |

### Key Safeguard Findings:
- **Tabular Gridline Filtering**: Legitimate tabular deed borders and porcha khatian rows share horizontal/vertical alignments with adjacent cells and are successfully excluded from anomaly candidates.
- **Watermark Chroma Suppression**: Diagonal synthetic demo watermarks do not trigger false positive seam flags.
- **Aged Paper Grain Variance**: Natural fiber paper noise is verified as background grain, preventing false alarms under mobile phone shadows and low contrast scans.
