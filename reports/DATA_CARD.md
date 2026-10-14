# Dataset Card: LandGuard Synthetic Land Records & Document Benchmark

## 1. Dataset Summary & Fictional Notice
This dataset contains **100,000 canonical synthetic land records** and **600 high-fidelity rendered document images** (`+60` pilot images) simulating Bangladeshi land administration records (sale deeds, khatians/porchas, mutation orders, tax dakhilas, cadastral parcel maps, and mutation petitions).

> [!IMPORTANT]
> **SAFETY & LEGAL AUTHENTICITY NOTICE**
> All records, owner identities, national identity numbers, plot numbers, cadastral surveys, signatures, and stamps in this dataset are **100% synthetically generated** using deterministic algorithms. No real personal records, official government archives, or genuine government seals were used or reproduced. Every rendered document carries a mandatory prominent watermark:
> **"SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"**

---

## 2. Dataset Structure & Entity Counts

| Entity / Category | Target Count | Actual Generated Count | Primary Identifier Format | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Fictional Owners** | 15,000 | **15,000** | `OWN-XXXXXXXX` | Fictional landholders with bilingual names and synthetic NIDs (`SYN-XXXXXXXXXX`) |
| **Fictional Parcels** | 10,000 | **10,000** | `PAR-XXXXXXXX` | Cadastral plots with area in decimals and polygon coordinates |
| **Historical Khatians** | 30,000 | **30,000** | `REC-XXXXXXXX` | CS, SA, RS, and BS record-of-rights ledgers |
| **Transactions & Deeds** | 25,000 | **25,000** | `TXN-XXXXXXXX` | Registered transfer deeds with consideration & chain references |
| **Mutation Records** | 10,000 | **10,000** | `MUTREC-XXXXXX` | Namzari mutation orders linking old and new khatians (`APPROVED` / `PENDING` / `REJECTED`) |
| **Land Tax Receipts** | 10,000 | **10,000** | `TAX-XXXXXX` | Land Development Tax (Dakhila) payment records |
| **TOTAL STRUCTURED RECORDS** | **100,000** | **100,000** | — | **Full Canonical Relational Database (`data/full/records/canonical_records.json`)** |

### Experimental Scenarios Breakdown
- **Total Designed Scenarios**: **`2,500`**
- **Deliberate Fraud-Risk Scenarios**: **`1,664`** across 8 statutory fraud categories
- **Legitimate Baselines & Edge Cases**: **`836`** across 4 legitimate baseline categories
- **Scenario Categories (`12` Classes)**:
  1. `LEGITIMATE_NORMAL_SALE` (`209` instances)
  2. `LEGITIMATE_INHERITANCE` (`209` instances)
  3. `LEGITIMATE_PARTIAL_SUBDIVISION` (`209` instances)
  4. `LEGITIMATE_CORRECTION_DEED` (`209` instances)
  5. `ALTERED_PLOT_NUMBER` (`208` instances)
  6. `ALTERED_OWNER_NAME` (`208` instances)
  7. `EXAGGERATED_LAND_AREA` (`208` instances)
  8. `BROKEN_CHAIN_OF_TITLE` (`208` instances)
  9. `CONFLICTING_DOUBLE_SALE` (`208` instances)
  10. `UNREGISTERED_MUTATION_MISMATCH` (`208` instances)
  11. `SYNTHETIC_SEAL_ABSENT_SUSPICIOUS` (`208` instances)
  12. `VISUAL_OVERLAY_TAMPERING` (`208` instances)

---

## 3. Multi-Feature Realistic Ambiguity & Anti-Leakage Design
To eliminate trivial 1-to-1 single-feature shortcuts and prevent oracle target leakage:
1. **Strict Removal of Oracle Fields from Transaction Schema**:
   - Base transaction records in `data/full/records/canonical_records.json` and [`schemas/transaction.schema.json`](file:///F:/land%20gurd/schemas/transaction.schema.json) (`additionalProperties: false`) strictly exclude simulator oracle flags (`has_visual_anomaly`, `has_seal`, `claimed_dag_plot_number`, `visual_anomaly_score`, `has_signature`).
   - Simulator injection provenance is stored exclusively in an external audit file (`data/full/records/simulator_audit_metadata.json`) and never enters `canonical_records.json` or `build_features.py`.
2. **Realistic Administrative & Clerical Ambiguity on Legitimate Scenarios**:
   - Legitimate transfers include realistic administrative lag (`PENDING` Namzari mutations, 1–2 year tax payment deltas, family/distress below-market consideration on inheritance transfers, and legitimate multi-part subdivision sales within parcel capacity).
3. **Multi-Signal Behavioral & Economic Correlates on Fraud Scenarios**:
   - Fraudulent scenarios exhibit realistic secondary behavioral anomalies (e.g., rush below-market pricing, 2–5 year tax arrears, unapproved mutation status, or prior partial conveyances exceeding cumulative parcel capacity) alongside primary statutory or document discrepancies.
4. **Multi-Entity Group-Disjoint Partitioning (`Train = 1,700`, `Val = 300`, `Test = 500`)**:
   - Each of the 2,500 scenarios is assigned a dedicated disjoint cohort of 6 owners (`15,000` owners / `2,500` scenarios) and grouped into 25 `template_cohort` buckets (`17` train cohorts = `1,700` scenarios, `3` val cohorts = `300` scenarios, `5` test cohorts = `500` scenarios).
   - Verified **zero overlap (`0`)** across `template_cohort`, `parcel_id`, `primary_seller_id`, and `scenario_id` between Train, Validation, and Test splits.

---

## 4. Document Image Categories & Renderer-Verified Annotations
The benchmark provides multi-template rendered document images across 6 legal categories:
1. **Sale Deeds (`SALE_DEED`, `150` images)**: Detailed conveyance deeds with bilingual seller/buyer schedules, consideration, boundaries, revenue stamp box, registrar seal, and seller signature mark.
2. **Khatian / Porcha Tables (`KHATIAN_PORCHA`, `120` images)**: Multi-row tabular survey records (`CS`, `SA`, `RS`, `BS`) with owner co-shares, plot numbers, land classification, and settlement officer seal.
3. **Mutation Records (`MUTATION_RECORD`, `120` images)**: Assistant Commissioner (Land) order sheets showing mutation case number, effective date, and status.
4. **Land Tax Receipts (`TAX_RECEIPT`, `90` images)**: Union land office tax clearance vouchers with assessed and paid BDT amounts.
5. **Cadastral Parcel Maps (`PARCEL_MAP`, `60` images)**: Vector-rendered plot boundary maps with adjacent plot labels, cadastral north arrow, scale bar, and legend.
6. **Mutation Petitions / Applications (`APPLICATION_COMPLAINT`, `60` images)**: Narrative citizen applications with applicant NID, Mouza/Dag schedule, and signature.

### Renderer-Verified Ground-Truth Text
In [`src/landguard_data/render_documents.py`](file:///F:/land%20gurd/src/landguard_data/render_documents.py) and [`src/landguard_data/render_maps.py`](file:///F:/land%20gurd/src/landguard_data/render_maps.py), every text line drawn onto the image canvas (including section headers, Khatian Row-2 co-heirs, applicant Mouza/Dag lines, and map neighbor plot labels) is appended directly to `rendered_text` at draw time, eliminating renderer-vs-annotation text drift.

---

## 5. Controlled Image Quality Variants (`15` Classes)
Every clean source document is rendered and degraded according to a deterministic schedule:
`clean_digital`, `clean_scan`, `grayscale_scan`, `low_resolution`, `mild_rotation`, `skewed_scan`, `low_contrast`, `uneven_illumination`, `blur`, `compression_artifacts`, `light_noise`, `wrinkled_paper`, `mild_stains`, `shadow_phone_photo`, and `cropped_edges`.

---

## 6. Image Count Reconciliation & Production Scalability
- **Verified Structured Records on Disk**: Exactly **`100,000`** records (`data/full/records/canonical_records.json`).
- **Verified Benchmark Images on Disk**: **`600`** multi-template PNG images in `data/full/images/` (`602` SHA-256 verified manifest entries) and **`60`** pilot images in `data/pilot/images/`.
- **Honest Target Distinction**: This repository explicitly distinguishes the **`600` rendered and evaluated benchmark images on disk** from the **`10,000`-image CLI scaling target capacity** (`python scripts/generate_all.py --num-images 10000 --output-dir data/full`).
