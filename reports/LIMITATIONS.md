# System Limitations & Methodological Boundaries

## 1. Synthetic-to-Real Domain Gap
- **Typeset Typography & Unshaped Pillow Glyphs vs. Historical Handwriting**: The synthetic pipeline uses deterministic Pillow typesetting with local fonts (`Nirmala.ttf`, `NirmalaB.ttf`). Because the local Pillow build does not bundle `libraqm`/`HarfBuzz` OpenType shaping, pre-base Bengali vowel matras (`ি`, `ে`, `ৈ`) and conjunct ligatures render in logical code-point order rather than complex shaped calligraphs. Furthermore, real historical Bangladeshi registry records from the British colonial (`CS`, 1940) or Pakistan (`SA`, 1962) eras frequently feature handwritten cursive Bengali script, fading iron-gall ink, and physical insect damage that synthetic filters only approximate.
- **Micro-Artifacts**: Real paper degradation exhibits complex non-linear fiber decay, yellowing, and humidity staining that simulated Gaussian noise or linear perspective transforms do not replicate fully.
- **Rendered Benchmark Scale (`600` Images vs. `10,000` Target)**: While the structured database contains all `100,000` canonical records (`2,500` scenarios), the active rendered image benchmark on disk contains `600` multi-template PNG images in `data/full/images/` (plus `60` pilot images in `data/pilot/images/`). Full `10,000`-image rendering is supported via `python scripts/generate_all.py --num-images 10000`.

---

## 2. Bilingual Optical Character Recognition (OCR) Error Analysis (`reports/ocr_repair_report.md`)
- **Empirical Language-Separated Results (`n = 48` Stratified Benchmark)**:
  - **Overall CER / WER**: Improved from `0.8143` $\rightarrow$ **`0.3702` CER** (`0.9389` $\rightarrow$ **`0.4955` WER**) by combining `Tesseract v5.4.0.20240606 (ben+eng)`, Bengali pre-base vowel-matra realignment, `RapidOCR` DBNet cell isolation, and renderer-verified ground-truth text alignment.
  - **Bangla Script Recognition (`Bangla CER = 0.4435`, `WER = 0.5641`)**: Repaired from `1.0000` CER (`0%` recognition under RapidOCR-only) to **`0.4435` CER** overall (`0.2399–0.3143` on clean/rotated/low-contrast scans). Remaining Bengali errors stem from unshaped consonant conjuncts (`ক্ষ`, `জ্ঞ`, `্র`) in Pillow without `libraqm` and vertical table grid borders in `KHATIAN_PORCHA` (`0.6630` Bangla CER).
  - **English / Alphanumeric Recognition (`English CER = 0.3598`, `Exact Field Match = 90.00%`)**: Repaired from `0.8868` initial CER (`0.6021` RapidOCR-only) to **`0.3598` CER**, achieving **`90.00%` Exact Field Match Accuracy (`72 / 80` fields)**, **`97.30%` Field Precision (`72 / 74`)**, and **`0.9351` Field F1**.
  - **Degraded Scan Vulnerability**: On `low_resolution` (`0.5625` CER) and `uneven_illumination` (`0.7991` CER) scans, heavy shadow gradients and downsampled stroke merging degrade full-page transcription and account for the `8 / 80` missed structured fields.

---

## 3. Signature, Seal & Visual Anomaly Detection Boundaries (`reports/vision_validation_report.md`)
> [!WARNING]
> **PRESENCE DETECTION IS NOT LEGAL AUTHENTICITY**
> Visual presence of a seal or signature flourish merely confirms that the document contains ink strokes in the expected coordinate zone. It does NOT establish human identity, handwriting authenticity, or official legal validity under the Evidence Act 1872 or Registration Act 1908.

- **Signature Detector Performance (`n = 600`)**:
  - **Assisted Candidate Region Detection**: Achieves **`98.17%` accuracy**, **`96.23%` precision**, **`100.0%` recall**, and **`0.9808` F1** (`TP=281, FP=11, TN=308, FN=0`).
  - **Unassisted Quadrant Baseline**: Achieves **`65.33%` accuracy**, **`77.04%` precision**, **`37.01%` recall**, and **`0.5000` F1** (`TP=104, FP=31, TN=288, FN=177`). Without template bounding-box registration, printed body text and witness blocks dilute stroke metrics—confirming that layout registration is required in production.
- **Seal Detector Accuracy (`n = 600`)**: Circular contour geometry and color ratio analysis achieves **`99.50%` accuracy**, **`100.0%` precision**, **`99.42%` recall**, and **`0.9971` F1** (`TP=510, FP=0, TN=87, FN=3`). However, a visually circular stamp does not guarantee genuine sub-registry authorization.
- **Visual Anomaly Detection (`n = 50` Multi-Alteration, `n = 600` Clean)**:
  - **Clean Digital False Positive Rate**: **`0.00%`** (`0 / 40` flagged).
  - **Overall Clean Dataset False Positive Rate**: **`0.83%`** (`5 / 600` flagged across all 15 scan degradations).
  - **Multi-Alteration Detection Recall**: **`96.00%`** (`48 / 50` detected across 4 distinct alteration mechanisms: `13/13` `paste_over_plot`, `11/13` `copy_move_clone`, `12/12` `localized_erasure_blur`, and `12/12` `dark_ink_overwrite`). The `2` missed samples are subtle `copy_move_clone` patches whose cloned background texture closely matches the surrounding paper grain.

---

## 4. Machine Learning Generalization & Legal Boundaries (`reports/independent_ml_validation.md`)
- **Non-Trivial Error Rates Under Realistic Ambiguity**: After removing all oracle simulator flags from transaction records and introducing realistic administrative lag (pending mutations, tax payment deltas, family/distress inheritance pricing, legitimate partial subdivisions), group-disjoint test accuracy (`n = 500`) is **`98.20%` (`F1 = 0.9865`, `FP = 7`, `FN = 2`) for XGBoost**, **`97.60%` (`F1 = 0.9821`) for Logistic Regression**, **`96.00%` (`F1 = 0.9705`) for Random Forest**, and **`94.80%` (`F1 = 0.9623`, `Recall = 1.0000`, `FP = 26`) for the Deterministic Rule Engine**.
- **Unseen Fraud Family Generalization (LOFFO CV, Regime D)**: When an entire fraud category (`n = 208`) is held out from training, supervised ML models achieve **`54.57%` (XGBoost) to `83.83%` (Random Forest) mean unseen-fraud recall** by leveraging shared economic/tax correlates, whereas the **Deterministic Statutory Rule Engine achieves `100.0%` recall across all 8 unseen fraud families**. Supervised ML must never replace deterministic statutory rules.
- **Human-in-the-Loop Mandate**: No transaction or land title may be automatically invalidated; all risk alerts require human registrar review.
