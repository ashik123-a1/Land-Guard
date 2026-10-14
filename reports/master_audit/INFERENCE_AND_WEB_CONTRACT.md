# LandGuard Inference Contract & Web Integration Specification

> [!IMPORTANT]
> **API Stability & Synthetic Boundary Contract**:
> This document specifies the authoritative API contracts, schemas, error codes, and audit mechanisms for the LandGuard Verification Service.
> All endpoints adhere to strict data-validation boundaries to ensure that synthetic benchmarks remain strictly separated from operational registries.

---

## 1. System Endpoints Architecture Overview

The LandGuard engine exposes a RESTful interface over HTTP/JSON (FastAPI 2.0.0), backed by an in-memory cadastral index, deterministic rule engine, serialized XGBoost model, and OpenCV forensic detector.

| HTTP Method | Route | Purpose | Payload Type | Response Type |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Web Demonstration UI | None | `text/html` |
| `GET` | `/api/health` | Service & Model Liveness | None | `application/json` |
| `GET` | `/api/samples` | Pre-configured Demo Test Cases | None | `application/json` |
| `POST` | `/api/upload` | Multipart File Upload + OCR/CV | `multipart/form-data` | `application/json` |
| `POST` | `/api/verify` | Statutory Adjudication & Scoring | `application/json` | `application/json` |
| `GET` | `/api/history` | Auditable Verification Log | None | `application/json` |

---

## 2. Endpoint Specifications

### 2.1 Health Check (`GET /api/health`)
Returns service operational state, loaded parcel count, model readiness, and mandatory synthetic watermark disclaimer.

#### Response Schema (JSON):
```json
{
  "status": "HEALTHY",
  "service": "LandGuard AI Land Record Verification",
  "version": "2.0.0",
  "xgb_model_ready": true,
  "indexed_parcels": 2600,
  "disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT. All records are synthetically generated."
}
```

---

### 2.2 Upload & OCR Ingestion (`POST /api/upload`)
Accepts document image (`.png`, `.jpg`, `.jpeg`, `.pdf`), enforces file size limits ($\le 15$ MB), executes OpenCV document anomaly screening, and runs bilingual Tesseract OCR.

#### Request Parameters:
- `file`: Binary file upload (`multipart/form-data`).

#### Response Schema (JSON):
```json
{
  "filename": "IMG-24DCC9AE.png",
  "saved_path": "data/uploads/20261014_IMG-24DCC9AE.png",
  "preview_url": "/uploads/20261014_IMG-24DCC9AE.png",
  "extracted_fields": {
    "deed_number": {
      "label": "Deed Number",
      "value": "DEED-2006-18946",
      "status": "VERIFIED_OCR",
      "level": "green",
      "confidence": 0.95,
      "note": "Standard deed number pattern matched."
    },
    "dag_plot_number": {
      "label": "Dag (Plot) Number",
      "value": "9044",
      "status": "VERIFIED_OCR",
      "level": "green",
      "confidence": 0.92,
      "note": "Plot number matched."
    },
    "transferred_area_decimal": {
      "label": "Transferred Area (Decimal)",
      "value": "8.38",
      "status": "VERIFIED_OCR",
      "level": "green",
      "confidence": 0.88,
      "note": "Valid decimal land area format."
    },
    "execution_date": {
      "label": "Execution Date",
      "value": "2006-11-11",
      "status": "VERIFIED_OCR",
      "level": "green",
      "confidence": 0.85,
      "note": "Standard ISO execution date parsed."
    }
  },
  "cv_anomalies": {
    "has_visual_anomaly": false,
    "visual_anomaly_score": 0.0,
    "seal_presence_detected": true,
    "signature_presence_detected": true,
    "detected_patches": []
  }
}
```

#### Error Responses:
- `400 Bad Request`: File extension not allowed (must be `.png`, `.jpg`, `.jpeg`, `.pdf`).
- `413 Payload Too Large`: Upload exceeds 15 MB.
- `422 Unprocessable Entity`: Corrupt image bytes cannot be decoded by PIL/OpenCV.

---

### 2.3 Statutory Verification Workflow (`POST /api/verify`)
Executes cadastral registry relational lookup, runs deterministic statutory rule evaluation, supplementary XGBoost scoring, and records officer field diffs.

#### Request Schema (`VerifyRequest`):
```json
{
  "confirmed_fields": {
    "deed_number": "DEED-2006-18946",
    "dag_plot_number": "9044",
    "transferred_area_decimal": "8.38",
    "execution_date": "2006-11-11",
    "seller_nid": "OWN-11CE5DD2",
    "buyer_nid": "OWN-CE177B4E",
    "previous_deed_ref": "DEED-2001-35323",
    "mutation_case_no": "MUT-2006-5364/Rupsha",
    "consideration_bdt": "955246.39",
    "khatian_number": "1420"
  },
  "image_path": "data/uploads/20261014_IMG-24DCC9AE.png",
  "original_ocr_fields": {
    "deed_number": "DEED-2006-18946",
    "dag_plot_number": "9044",
    "transferred_area_decimal": "8.38",
    "execution_date": "2006-11-11"
  }
}
```

#### Response Schema (JSON):
```json
{
  "verification_id": "VRF-20261014-A1B2C3",
  "timestamp": "2026-10-14T02:15:00.123456",
  "deed_number": "DEED-2006-18946",
  "dag_plot_number": "9044",
  "transferred_area_decimal": 8.38,
  "execution_date": "2006-11-11",
  "cadastral_registry_match": true,
  "parcel_details": {
    "parcel_id": "PAR-RUPSHA-9044",
    "dag_plot_number": 9044,
    "khatian_number": "1420",
    "total_area_decimal": 87.25,
    "mouza": "Rupsha Mouza",
    "upazila": "Rupsha",
    "district": "Khulna"
  },
  "overall_status": "CLEAR_FOR_STANDARD_PROCESSING",
  "overall_badge": "VERIFIED CLEAR",
  "overall_badge_color": "green",
  "recommended_action": "PROCEED_WITH_STANDARD_REVIEW: No statutory contradictions or risk indicators observed.",
  "rule_engine_score": 0.05,
  "rule_engine_flagged": false,
  "ml_model_score": 0.0018,
  "cv_anomaly_score": 0.0,
  "cv_visual_anomaly_detected": false,
  "rules_triggered": [],
  "observed_evidence": { ... },
  "missing_or_uncertain_evidence": [],
  "officer_diff_tracking": {
    "total_fields_reviewed": 10,
    "modified_fields_count": 0,
    "modifications": []
  },
  "processing_time_ms": 42.5,
  "synthetic_disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"
}
```

---

## 3. Human-in-the-Loop Diff Audit Contract

When registration officers edit an extracted OCR field in the UI prior to clicking "Run Statutory Verification", the backend explicitly computes an audit diff between `original_ocr_fields` and `confirmed_fields`.

#### Diff Tracking Structure:
```json
{
  "officer_diff_tracking": {
    "total_fields_reviewed": 10,
    "modified_fields_count": 1,
    "modifications": [
      {
        "field_key": "dag_plot_number",
        "ocr_extracted_value": "9041",
        "officer_confirmed_value": "9044",
        "change_type": "OFFICER_CORRECTION"
      }
    ]
  }
}
```
All diff events are immutably logged to the verification audit history log (`/api/history`), ensuring non-repudiation and transparency during subsequent administrative reviews.

---

## 4. Statutory Rule & Risk Explanation Contract

Each entry in `rules_triggered` complies with the four-category evidence standard:

```json
{
  "rule_code": "RULE_AREA_EXCEEDS_CAPACITY",
  "category": "CONFIRMED_INCONSISTENCY",
  "severity": "CRITICAL",
  "evidence_source": "REGISTRY_RECORD",
  "reason": "Transferred area (203.89 dec) exceeds recorded cadastral parcel capacity (87.25 dec)."
}
```

Categories and their UI representations:
1. `CONFIRMED_INCONSISTENCY`: Red badge (`bg-red-500`), Critical alert, holds processing.
2. `MISSING_EVIDENCE`: Amber badge (`bg-amber-500`), Requests document archive search.
3. `REVIEW_REQUIRED`: Blue/Yellow badge (`bg-yellow-500`), Flags for AC (Land) hearing.
4. `RISK_INDICATOR`: Purple/Amber badge (`bg-purple-500`), Secondary screening recommendation.
5. `CLEAR_FOR_STANDARD_PROCESSING`: Green badge (`bg-green-500`), Standard processing authorized.
