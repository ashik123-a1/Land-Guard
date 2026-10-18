"""Verification Domain Service
Coordinates bilingual OCR field confirmation, cadastral registry lookup,
statutory rule engine evaluation, supplementary XGBoost inference, and CV anomaly detection.
"""

import os
import time
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
from PIL import Image

from src.landguard_models.build_features import (
    extract_inference_features,
    validate_no_leakage,
)
from src.landguard_models.explainable_risk import build_explainable_risk_assessment
from src.landguard_vision.visual_anomaly_baseline import detect_visual_anomalies
from src.landguard_vision.seal_presence import detect_seal_presence
from src.landguard_vision.signature_presence import detect_signature_presence
from src.landguard_data.database import LandGuardDatabase

RULE_METADATA = {
    "RULE_AREA_NOT_ASSESSED": {
        "title": "Holding Capacity Not Assessed",
        "statutory_reference": "Land Reform Ordinance 1984 s.4 / SAT Act 1950",
        "next_step": "Obtain deed schedule or physical inspection to verify transferred area against parcel holding capacity.",
    },
    "RULE_AREA_EXCEEDS_CAPACITY": {
        "title": "Cadastral Holding Capacity Discrepancy",
        "statutory_reference": "Registration Act 1908 s.21 / Land Reform Ordinance 1984",
        "next_step": "Cross-check partition boundaries in mouza map sheet; verify registered CS/RS holding capacity.",
    },
    "RULE_BROKEN_CHAIN_OF_TITLE": {
        "title": "Broken Historical Chain of Title",
        "statutory_reference": "Transfer of Property Act 1882 s.54 / Registration Act 1908 s.47",
        "next_step": "Request Sub-Registry archives to retrieve and cross-reference unindexed historical conveyance volume.",
    },
    "RULE_SELLER_NOT_TITLEHOLDER": {
        "title": "Vendor Lacks Prior Transferee Title Record",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.143 / Registration Act 1908 s.52A",
        "next_step": "Verify vendor's succession certificate (Waris Sanad) or preceding registered conveyance deed with Sub-Registrar.",
    },
    "RULE_CONFLICTING_DOUBLE_DISPOSITION": {
        "title": "Conflicting Prior Disposition (Double-Selling Risk)",
        "statutory_reference": "Registration Act 1908 s.47 / Penal Code 1860 s.420, 468",
        "next_step": "Immediately hold registration docket. Cross-examine Book 1 volume record for prior transfer and notify Sub-Registrar & AC (Land).",
    },
    "RULE_PARTIAL_SUBDIVISION_CAPACITY_CHECK": {
        "title": "Holding Partial Subdivision Review",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.116, 117",
        "next_step": "Inspect field survey partition map (Bonton-nama) to verify remaining plot holding capacity.",
    },
    "RULE_UNVERIFIED_MUTATION_RECORD": {
        "title": "Unverified / Contradictory Namzari Mutation Reference",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.143 / Mutation Manual 1990",
        "next_step": "Query AC (Land) Upazila revenue server to retrieve authenticated Dakhila and approved mutation resolution.",
    },
    "RULE_MUTATION_PENDING_REVIEW": {
        "title": "Mutation Order Pending Administrative Approval",
        "statutory_reference": "State Acquisition and Tenancy Act 1950 s.143",
        "next_step": "Coordinate with Upazila Land Office to ascertain final hearing status before deed execution.",
    },
    "RULE_TAX_ARREARS_INDICATOR": {
        "title": "Land Development Tax Arrears Indicator",
        "statutory_reference": "Land Development Tax Ordinance 1976",
        "next_step": "Require vendor to present updated Land Development Tax (Khajna) payment Dakhila receipt.",
    },
    "RULE_BELOW_MARKET_CONSIDERATION_INDICATOR": {
        "title": "Sub-Mouza Rate Valuation Anomaly",
        "statutory_reference": "Stamp Act 1899 s.27 / Sub-Registry Valuation Gazette",
        "next_step": "Verify valuation against prescribed minimum government mouza rate chart to assess stamp duty compliance.",
    },
    "RULE_PLOT_MISMATCH_WITH_KHATIAN": {
        "title": "Dag Plot Number Contradicts Cadastral Survey Record",
        "statutory_reference": "Survey Act 1875 / SAT Act 1950 s.144",
        "next_step": "Inspect certified RS/BS Khatian copy and compare physical survey boundaries with Mouza sheet.",
    },
    "RULE_MANDATORY_REGISTRAR_SEAL_ABSENT": {
        "title": "Mandatory Sub-Registry Authentication Seal Absent",
        "statutory_reference": "Registration Act 1908 s.58, 60",
        "next_step": "Subject physical parchment to UV lamp examination and verify volume register registry book impressions.",
    },
    "RULE_VISUAL_TAMPERING_DETECTED": {
        "title": "Physical Seam / Optical Text Alteration Detected",
        "statutory_reference": "Evidence Act 1872 s.45, 73 (Forensic Examination)",
        "next_step": "Refer physical instrument to CID Forensic Document Examination Laboratory for microscope and spectral analysis.",
    },
    "RULE_PLOT_NOT_FOUND_IN_REGISTRY": {
        "title": "Dag Plot Not Indexed in Verified Cadastral Survey",
        "statutory_reference": "Cadastral Survey Records Index",
        "next_step": "Search unindexed mouza supplementary field registers and historical village settlement sheets.",
    },
    "ML_ELEVATED_RISK_SCORE": {
        "title": "Elevated Multivariate Machine Learning Risk Signal",
        "statutory_reference": "Algorithmic Risk Prioritization Framework",
        "next_step": "Review contributing transactional feature anomalies with senior registry officer.",
    },
}


class VerificationService:
    """Domain service managing title verification workflows and dossiers."""

    def __init__(
        self,
        db: Optional[LandGuardDatabase] = None,
        parcels_by_plot: Optional[Dict[str, Dict[str, Any]]] = None,
        history_by_parcel: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        mutations_by_parcel: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        audit_history: Optional[List[Dict[str, Any]]] = None,
        seeded_dossiers: Optional[Dict[str, Dict[str, Any]]] = None,
        xgb_model: Any = None,
    ):
        self.db = db or LandGuardDatabase()
        self.parcels_by_plot = parcels_by_plot if parcels_by_plot is not None else {}
        self.history_by_parcel = history_by_parcel if history_by_parcel is not None else {}
        self.mutations_by_parcel = mutations_by_parcel if mutations_by_parcel is not None else {}
        self.audit_history = audit_history if audit_history is not None else []
        self._seeded_dossiers = seeded_dossiers if seeded_dossiers is not None else {}
        self.xgb_model = xgb_model

    def verify_transaction(
        self,
        confirmed_fields: Dict[str, Any],
        image_path: Optional[str] = None,
        original_ocr_fields: Optional[Dict[str, Any]] = None,
        evidence_source: Optional[str] = "UPLOAD",
    ) -> Dict[str, Any]:
        """Executes the end-to-end statutory verification workflow."""
        t_start = time.time()
        verification_id = f"VRF-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        doc_type = str(confirmed_fields.get("document_type") or "SALE_DEED").upper()
        raw_deed = confirmed_fields.get("deed_number")
        if raw_deed and str(raw_deed).strip() not in ("None", "null", ""):
            deed_no = str(raw_deed).strip()
        else:
            deed_no = "UNSPECIFIED" if doc_type == "SALE_DEED" else "N/A"

        dag_plot_str = str(confirmed_fields.get("dag_plot_number", "") or "").strip()
        
        raw_area = confirmed_fields.get("transferred_area_decimal")
        if raw_area is not None and str(raw_area).strip() not in ("None", "null", ""):
            try:
                area_val = float(raw_area)
            except (ValueError, TypeError):
                area_val = None
        else:
            area_val = None

        raw_exec = confirmed_fields.get("execution_date")
        exec_date = str(raw_exec).strip() if raw_exec and str(raw_exec).strip() not in ("None", "null", "") else None

        raw_seller = confirmed_fields.get("seller_nid")
        seller_nid = str(raw_seller).strip() if raw_seller and str(raw_seller).strip() not in ("None", "null", "") else None

        raw_buyer = confirmed_fields.get("buyer_nid")
        buyer_nid = str(raw_buyer).strip() if raw_buyer and str(raw_buyer).strip() not in ("None", "null", "") else None

        raw_prev = confirmed_fields.get("previous_deed_ref")
        prev_ref = str(raw_prev).strip() if raw_prev and str(raw_prev).strip() not in ("None", "null", "") else None

        raw_mut = confirmed_fields.get("mutation_case_no")
        mut_case = str(raw_mut).strip() if raw_mut and str(raw_mut).strip() not in ("None", "null", "") else None

        raw_cons = confirmed_fields.get("consideration_bdt")
        if raw_cons is not None and str(raw_cons).strip() not in ("None", "null", ""):
            try:
                consideration = float(raw_cons)
            except (ValueError, TypeError):
                consideration = None
        else:
            consideration = None

        parcel_record = self.parcels_by_plot.get(dag_plot_str)
        history_txns: List[Dict[str, Any]] = []
        mutations: List[Dict[str, Any]] = []

        if parcel_record:
            cadastral_found = True
            parcel = dict(parcel_record)
            history_txns = list(self.history_by_parcel.get(dag_plot_str, []))
            mutations = list(self.mutations_by_parcel.get(dag_plot_str, []))
        else:
            cadastral_found = False
            parcel = {
                "parcel_id": f"PAR-UNVERIFIED-{dag_plot_str or 'NONE'}",
                "dag_plot_number": int(dag_plot_str) if dag_plot_str and dag_plot_str.isdigit() else 9999,
                "khatian_number": str(confirmed_fields.get("khatian_number", "UNVERIFIED")),
                "total_area_decimal": 0.0,
                "mouza": "Unindexed Mouza",
                "upazila": "Unknown",
                "district": "Unknown",
                "recorded_land_class": "Unindexed Cadastral Holding",
            }
            history_txns = None
            mutations = None

        tax_year = None
        if exec_date and len(exec_date) >= 4 and exec_date[:4].isdigit():
            tax_year = int(exec_date[:4])

        txn = {
            "transaction_id": f"TXN-{verification_id}",
            "document_type": doc_type,
            "deed_number": deed_no,
            "execution_date": exec_date or "2024-01-01",
            "seller_ids": [seller_nid] if seller_nid else [],
            "buyer_ids": [buyer_nid] if buyer_nid else [],
            "transferred_area_decimal": area_val if area_val is not None else 0.0,
            "has_transferred_area_specified": area_val is not None,
            "previous_deed_ref": prev_ref or "",
            "mutation_case_no": mut_case or "",
            "khatian_number": str(confirmed_fields.get("khatian_number", "") or ""),
            "consideration_bdt": consideration if consideration is not None else 0.0,
            "tax_clearance_year": tax_year or 2024,
        }
        validate_no_leakage(txn)

        cv_anom_score = 0.0
        cv_anom_detected = False
        seal_detected = None
        sig_detected = None
        detected_patches = []
        cv_checked = False
        cv_status = "NOT_CHECKED"
        cv_error_reason = None

        if image_path:
            if not os.path.exists(image_path):
                cv_status = "NOT_CHECKED"
                cv_error_reason = f"Image path '{image_path}' not found on disk."
            else:
                cv_checked = True
                try:
                    img = Image.open(image_path).convert("RGB")
                    anom_res = detect_visual_anomalies(img)
                    cv_anom_detected = bool(anom_res.get("has_visual_anomaly", False))
                    cv_anom_score = float(anom_res.get("visual_anomaly_score", 0.0))
                    detected_patches = anom_res.get("detected_patches", [])

                    seal_res = detect_seal_presence(img)
                    seal_detected = bool(seal_res.get("presence_detected", False))

                    sig_res = detect_signature_presence(img)
                    sig_detected = bool(sig_res.get("presence_detected", False))
                    cv_status = "EVALUATED"
                except Exception as e:
                    cv_status = "INCONCLUSIVE"
                    cv_error_reason = f"Visual inspection processing error: {str(e)}"
                    print(f"Warning: CV inspection error: {e}")

        doc_ev = {
            "doc_dag_plot_number": int(dag_plot_str) if dag_plot_str and dag_plot_str.isdigit() else 9999,
            "doc_transferred_area_decimal": area_val if area_val is not None else 0.0,
            "cv_seal_present": seal_detected if cv_checked and seal_detected is not None else True,
            "cv_signature_present": sig_detected if cv_checked and sig_detected is not None else True,
            "cv_visual_anomaly_detected": cv_anom_detected,
            "cv_visual_anomaly_score": cv_anom_score,
        }

        has_essential_evidence = (
            cadastral_found
            and bool(seller_nid)
            and area_val is not None
            and area_val > 0.0
        )

        ml_prob = None
        if cadastral_found and has_essential_evidence and self.xgb_model is not None:
            try:
                feat_df = extract_inference_features(
                    txn=txn,
                    parcel=parcel,
                    history_txns=history_txns or [],
                    mutations=mutations or [],
                    document_evidence=doc_ev,
                    include_document_evidence=True,
                )
                ml_prob = float(self.xgb_model.predict_proba(feat_df)[0, 1])
            except Exception as e:
                print(f"Warning: ML scoring failed: {e}")
                ml_prob = None

        assessment = build_explainable_risk_assessment(
            txn=txn,
            parcel=parcel,
            history_txns=history_txns,
            mutations=mutations,
            document_evidence=doc_ev,
            ml_risk_probability=ml_prob,
            ml_threshold=0.50,
            include_document_evidence=True,
            cadastral_found=cadastral_found,
        )

        for r in assessment["rules_triggered"]:
            if not r.get("explanation"):
                r["explanation"] = r.get("reason") or "Statutory condition flagged for review."
            if not r.get("reason"):
                r["reason"] = r["explanation"]
            if not r.get("title"):
                r["title"] = r.get("rule_code", "RULE_CHECK").replace("RULE_", "").replace("_", " ").title()
            if not r.get("statutory_reference"):
                r["statutory_reference"] = "Registration Act 1908 / SAT Act 1950"

        field_edits = []
        if original_ocr_fields:
            for k, conf_v in confirmed_fields.items():
                ocr_v = original_ocr_fields.get(k, "")
                if str(ocr_v).strip() != str(conf_v).strip():
                    field_edits.append({
                        "field": k,
                        "ocr_raw_value": str(ocr_v),
                        "confirmed_value": str(conf_v),
                    })

        duration_ms = round((time.time() - t_start) * 1000, 1)

        result = {
            "verification_id": verification_id,
            "user_id": confirmed_fields.get("user_id") or "USR-CITIZEN-001",
            "timestamp": datetime.datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "evidence_source": evidence_source or "UPLOAD",
            "document_type": doc_type,
            "deed_number": deed_no,
            "dag_plot_number": dag_plot_str,
            "transferred_area_decimal": area_val,
            "execution_date": exec_date,
            "seller_nid": seller_nid,
            "buyer_nid": buyer_nid,
            "previous_deed_ref": prev_ref,
            "mutation_case_no": mut_case,
            "consideration_bdt": consideration,
            "khatian_number": str(confirmed_fields.get("khatian_number", parcel.get("khatian_number", "812"))),
            "overall_status": assessment["overall_assessment_category"],
            "recommended_action": assessment["recommended_human_action"],
            "rule_engine_flagged": assessment["rule_engine_flagged"],
            "rule_score": assessment["rule_engine_score"],
            "rules_triggered": assessment["rules_triggered"],
            "ml_risk_score": float(assessment["ml_model_score"]) if assessment.get("ml_model_score") is not None else None,
            "ml_threshold": assessment["ml_threshold_used"],
            "ml_model_fallback": assessment.get("ml_model_score") is None,
            "ml_calibration": (
                "NOT_ASSESSABLE" if not cadastral_found
                else ("INSUFFICIENT_EVIDENCE" if not has_essential_evidence
                else ("LOW_RISK" if (assessment["ml_model_score"] is not None and assessment["ml_model_score"] < 0.25)
                else ("MODERATE_RISK" if (assessment["ml_model_score"] is not None and assessment["ml_model_score"] < 0.65)
                else ("ELEVATED_RISK" if assessment["ml_model_score"] is not None else "STATUTORY_FALLBACK"))))
            ),
            "cadastral_parcel": parcel,
            "cadastral_found": cadastral_found,
            "cv_evidence": {
                "cv_checked": cv_checked,
                "cv_status": cv_status,
                "cv_error_reason": cv_error_reason,
                "visual_anomaly_detected": cv_anom_detected,
                "visual_anomaly_score": cv_anom_score,
                "seal_present": seal_detected,
                "seal_status": "NOT_CHECKED" if seal_detected is None else ("DETECTED" if seal_detected else "NOT_DETECTED"),
                "signature_present": sig_detected,
                "signature_status": "NOT_CHECKED" if sig_detected is None else ("DETECTED" if sig_detected else "NOT_DETECTED"),
                "authenticity_verified": False,
                "authenticity_note": "Visual detector confirms presence of physical impression only; forensic authenticity is unverified.",
                "detected_patches": detected_patches,
            },
            "field_edits_by_user": field_edits,
            "explanation_summary": assessment["explanation_summary"],
            "disclaimer": assessment["decision_support_disclaimer"],
            "synthetic_disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT. All records, names, plots, and seals are synthetically generated.",
        }

        import hashlib
        payload = json.dumps({
            "verification_id": verification_id,
            "timestamp": result["timestamp"],
            "deed_number": deed_no,
            "dag_plot_number": dag_plot_str,
            "overall_status": result["overall_status"],
            "rules_triggered": result["rules_triggered"],
            "ml_risk_score": result["ml_risk_score"],
        }, sort_keys=True)
        result["sha256_hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        self.audit_history.insert(0, result)
        if len(self.audit_history) > 200:
            self.audit_history.pop()

        try:
            self.db.save_verification_run(result, result.get("rules_triggered", []))
        except Exception as e:
            print(f"[VerificationService] Warning: Failed to persist verification run to SQLite: {e}")

        return result

    def get_verification_record(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Finds a verification record by ID, enriches rule metadata, and restores SQLite determinations."""
        import hashlib
        target_list = list(self.audit_history)
        if hasattr(self, "_seeded_dossiers") and verification_id in self._seeded_dossiers:
            if not any(r.get("verification_id") == verification_id for r in target_list):
                target_list.append(dict(self._seeded_dossiers[verification_id]))

        for r in target_list:
            if r.get("verification_id") == verification_id:
                if "sha256_hash" not in r:
                    evidence_payload = json.dumps({
                        "verification_id": r.get("verification_id"),
                        "timestamp": r.get("timestamp"),
                        "deed_number": r.get("deed_number"),
                        "dag_plot_number": r.get("dag_plot_number"),
                        "overall_status": r.get("overall_status"),
                        "rules_triggered": r.get("rules_triggered", []),
                        "ml_risk_score": r.get("ml_risk_score"),
                    }, sort_keys=True)
                    r["sha256_hash"] = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()

                if not r.get("cadastral_parcel"):
                    plot_str = str(r.get("dag_plot_number", "")).strip()
                    if plot_str in self.parcels_by_plot:
                        r["cadastral_parcel"] = dict(self.parcels_by_plot[plot_str])
                        r["cadastral_found"] = True

                cv_ev = r.get("cv_evidence") or {}
                seal_val = cv_ev.get("seal_present")
                if seal_val is True:
                    cv_ev["seal_status"] = "DETECTED"
                elif seal_val is False:
                    cv_ev["seal_status"] = "NOT_DETECTED"
                elif str(seal_val).upper() == "INCONCLUSIVE":
                    cv_ev["seal_status"] = "INCONCLUSIVE"
                else:
                    cv_ev["seal_status"] = "NOT_CHECKED"

                sig_val = cv_ev.get("signature_present")
                if sig_val is True:
                    cv_ev["signature_status"] = "DETECTED"
                elif sig_val is False:
                    cv_ev["signature_status"] = "NOT_DETECTED"
                elif str(sig_val).upper() == "INCONCLUSIVE":
                    cv_ev["signature_status"] = "INCONCLUSIVE"
                else:
                    cv_ev["signature_status"] = "NOT_CHECKED"
                r["cv_evidence"] = cv_ev

                for rule in r.get("rules_triggered", []):
                    code = rule.get("rule_code", "")
                    meta = RULE_METADATA.get(code, {})
                    if "title" not in rule:
                        rule["title"] = meta.get("title", code.replace("RULE_", "").replace("_", " ").title())
                    if not rule.get("title_bn"):
                        rule["title_bn"] = meta.get("title_bn") or rule.get("title")
                    if not rule.get("statutory_reference") or rule.get("statutory_reference") == "N/A":
                        rule["statutory_reference"] = meta.get("statutory_reference", "Registration Act 1908 / SAT Act 1950")
                    if "next_step" not in rule:
                        rule["next_step"] = meta.get("next_step", "Inspect physical volume register and verify field cadastral survey.")
                    if "explanation" not in rule and "reason" in rule:
                        rule["explanation"] = rule["reason"]
                    if not rule.get("explanation_bn"):
                        rule["explanation_bn"] = meta.get("default_explanation_bn") or rule.get("explanation")

                try:
                    db_events = self.db.get_audit_events_for_target("VERIFICATION", verification_id)
                    persisted_history = []
                    for ev in reversed(db_events):
                        if ev.get("action_type") == "VERIFICATION_DETERMINATION_RECORDED":
                            dtls = ev.get("details") or {}
                            persisted_history.append({
                                "decision": dtls.get("decision"),
                                "reason": dtls.get("reason"),
                                "officer_name": dtls.get("officer_name"),
                                "user_id": ev.get("actor_id"),
                                "timestamp": ev.get("created_at"),
                                "event_id": ev.get("event_id"),
                            })
                    if persisted_history:
                        r["determination_history"] = persisted_history
                        r["human_determination"] = persisted_history[-1]
                except Exception as e:
                    print(f"[VerificationService] Note: Could not query SQLite determination history: {e}")

                return r

        try:
            db_run = self.db.get_verification_run(verification_id)
            if db_run:
                plot_str = str(db_run.get("dag_plot_number", "")).strip()
                parcel_match = self.parcels_by_plot.get(plot_str)
                rules_list = []
                for f in db_run.get("findings", []):
                    rcode = f.get("finding_code")
                    rmeta = RULE_METADATA.get(rcode, {})
                    rules_list.append({
                        "rule_code": rcode,
                        "title": rmeta.get("title", f.get("category", "Statutory Rule")),
                        "title_bn": rmeta.get("title_bn", f.get("category", "Statutory Rule")),
                        "category": f.get("category", "CONFIRMED_INCONSISTENCY"),
                        "severity": f.get("severity", "HIGH"),
                        "statutory_reference": f.get("statutory_reference") or rmeta.get("statutory_reference", "Registration Act 1908"),
                        "explanation": f.get("explanation", "") or rmeta.get("default_explanation", ""),
                        "explanation_bn": rmeta.get("default_explanation_bn") or f.get("explanation", ""),
                        "next_step": rmeta.get("next_step", "Inspect physical volume register and verify survey."),
                    })
                r = {
                    "verification_id": db_run["verification_id"],
                    "timestamp": db_run.get("created_at"),
                    "user_id": db_run.get("user_id", "USR-CITIZEN-001"),
                    "deed_number": db_run.get("deed_number"),
                    "dag_plot_number": plot_str,
                    "transferred_area_decimal": float(db_run.get("transferred_area_decimal") or 0.0),
                    "overall_status": db_run.get("overall_status"),
                    "rule_engine_flagged": db_run.get("rule_engine_flagged"),
                    "rules_triggered": rules_list,
                    "ml_risk_score": float(db_run.get("ml_risk_score") or 0.0),
                    "ml_threshold": 0.35,
                    "sha256_hash": db_run.get("sha256_report_hash"),
                    "recommended_action": db_run.get("recommended_action"),
                    "cadastral_parcel": parcel_match,
                    "cadastral_found": parcel_match is not None,
                    "cv_evidence": {
                        "visual_anomaly_detected": False,
                        "visual_anomaly_score": 0.0,
                        "seal_status": "NOT_CHECKED",
                        "signature_status": "NOT_CHECKED",
                    },
                    "disclaimer": "This assessment is algorithmic decision support under statutory verification rules.",
                    "synthetic_disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
                }
                db_events = self.db.get_audit_events_for_target("VERIFICATION", verification_id)
                persisted_history = []
                for ev in reversed(db_events):
                    if ev.get("action_type") == "VERIFICATION_DETERMINATION_RECORDED":
                        dtls = ev.get("details") or {}
                        persisted_history.append({
                            "decision": dtls.get("decision"),
                            "reason": dtls.get("reason"),
                            "officer_name": dtls.get("officer_name"),
                            "user_id": ev.get("actor_id"),
                            "timestamp": ev.get("created_at"),
                            "event_id": ev.get("event_id"),
                        })
                if persisted_history:
                    r["determination_history"] = persisted_history
                    r["human_determination"] = persisted_history[-1]
                return r
        except Exception as e:
            print(f"[VerificationService] Warning: SQLite verification lookup error: {e}")

        return None

    def record_verification_decision(
        self,
        verification_id: str,
        decision: str,
        reason: str,
        user_id: str,
        officer_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Records an official administrative determination onto the verification record and SQLite audit log."""
        rec = self.get_verification_record(verification_id)
        if not rec:
            return None

        valid_decisions = [
            "APPROVE_STANDARD",
            "REQUEST_ARCHIVES",
            "FLAG_FOR_FIELD_INSPECTION",
            "REFER_TO_AC_LAND",
        ]
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of: {', '.join(valid_decisions)}")

        now_iso = datetime.datetime.now().isoformat()
        determination_entry = {
            "decision": decision,
            "reason": (reason or "").strip(),
            "officer_name": officer_name,
            "user_id": user_id,
            "timestamp": now_iso,
        }

        rec["human_determination"] = determination_entry
        if "determination_history" not in rec:
            rec["determination_history"] = []
        rec["determination_history"].append(determination_entry)

        try:
            self.db.log_audit_event(
                actor_id=user_id,
                action_type="VERIFICATION_DETERMINATION_RECORDED",
                target_entity="VERIFICATION",
                target_id=verification_id,
                details={
                    "verification_id": verification_id,
                    "decision": decision,
                    "reason": reason.strip(),
                    "deed_number": rec.get("deed_number"),
                    "dag_plot_number": rec.get("dag_plot_number"),
                    "officer_name": officer_name,
                },
                ip_address=None,
            )
        except Exception as e:
            print(f"[VerificationService] Warning: Failed to log audit event to SQLite: {e}")

        return determination_entry

    def get_sample_cases(self) -> List[Dict[str, Any]]:
        """Returns pre-configured demonstration cases for one-click testing."""
        return [
            {
                "case_id": "DEMO-CLEAN",
                "title": "Clean Legitimate Sale Deed",
                "category": "LEGITIMATE_NORMAL_SALE",
                "badge": "LEGITIMATE",
                "badge_color": "green",
                "description": "Standard conveyance with verified ancestral chain-of-title, matching cadastral plot, and transferred area within parcel holding capacity.",
                "image_filename": "IMG-24DCC9AE.png",
                "image_path": "data/full/images/IMG-24DCC9AE.png",
                "expected_category": "CLEAR_FOR_STANDARD_PROCESSING",
                "preset_fields": {
                    "deed_number": "DEED-2006-18946",
                    "dag_plot_number": "9044",
                    "transferred_area_decimal": "8.38",
                    "execution_date": "2006-11-11",
                    "seller_nid": "OWN-11CE5DD2",
                    "buyer_nid": "OWN-CE177B4E",
                    "previous_deed_ref": "DEED-2001-35323",
                    "mutation_case_no": "MUT-2006-5364/Rupsha",
                    "consideration_bdt": "955246.39",
                    "khatian_number": "1420",
                },
            },
            {
                "case_id": "DEMO-MUTATION-MISMATCH",
                "title": "Registration–Mutation Mismatch / Unverified Namzari",
                "category": "UNREGISTERED_MUTATION_MISMATCH",
                "badge": "MUTATION CONTRADICTION",
                "badge_color": "red",
                "description": "Deed claims mutation case MUT-2017-5331/Paba, but registered AC Land records show approved mutation was MUT-2017-7980/Paba. Mutation holding unverified under SAT Act s.143.",
                "image_filename": "IMG-9D7B4A76.png",
                "image_path": "data/full/images/IMG-9D7B4A76.png",
                "expected_category": "CONFIRMED_INCONSISTENCY",
                "preset_fields": {
                    "deed_number": "DEED-2017-55696",
                    "dag_plot_number": "7025",
                    "transferred_area_decimal": "47.94",
                    "execution_date": "2017-09-21",
                    "seller_nid": "OWN-C5CE099C",
                    "buyer_nid": "OWN-7C16128D",
                    "previous_deed_ref": "DEED-2011-17890",
                    "mutation_case_no": "MUT-2017-5331/Paba",
                    "consideration_bdt": "3221507.33",
                    "khatian_number": "384",
                },
            },
            {
                "case_id": "DEMO-AREA-EXCESS",
                "title": "Cadastral Area Excess Fraud",
                "category": "EXAGGERATED_LAND_AREA",
                "badge": "STATUTORY CONTRADICTION",
                "badge_color": "red",
                "description": "Claimed transferred area (203.89 decimal) exceeds recorded cadastral parcel capacity (87.25 decimal). Violates Land Reform statutory limit.",
                "image_filename": "IMG-8B4D3063.png",
                "image_path": "data/full/images/IMG-8B4D3063.png",
                "expected_category": "CONFIRMED_INCONSISTENCY",
                "preset_fields": {
                    "deed_number": "DEED-2012-85693",
                    "dag_plot_number": "9262",
                    "transferred_area_decimal": "203.89",
                    "execution_date": "2012-05-18",
                    "seller_nid": "OWN-8B4D3063",
                    "buyer_nid": "OWN-BUYER-02",
                    "previous_deed_ref": "DEED-2005-20185",
                    "mutation_case_no": "MUT-2012-2083/Sitakunda",
                    "consideration_bdt": "15500000.00",
                    "khatian_number": "812",
                },
            },
            {
                "case_id": "DEMO-DOUBLE-SALE",
                "title": "Conflicting Prior Disposition (Double Sale)",
                "category": "DOUBLE_SELLING_DISPUTE",
                "badge": "CRITICAL DISPUTE",
                "badge_color": "red",
                "description": "Vendor already conveyed full registered holding to previous buyer under Book 1 volume. Second conveyance is invalid under Registration Act s.47.",
                "image_filename": "IMG-025DAECA.png",
                "image_path": "data/full/images/IMG-025DAECA.png",
                "expected_category": "CONFIRMED_INCONSISTENCY",
                "preset_fields": {
                    "deed_number": "DEED-2005-23539",
                    "dag_plot_number": "6792",
                    "transferred_area_decimal": "31.82",
                    "execution_date": "2005-09-30",
                    "seller_nid": "OWN-025DAECA",
                    "buyer_nid": "OWN-BUYER-04",
                    "previous_deed_ref": "DEED-2000-41374",
                    "mutation_case_no": "MUT-2005-9264/Paba",
                    "consideration_bdt": "2800000.00",
                    "khatian_number": "1123",
                },
            },
            {
                "case_id": "DEMO-VISUAL-TAMPERING",
                "title": "Physical / Optical Document Alteration",
                "category": "TAMPERED_DEED_IMAGE",
                "badge": "FORENSIC ANOMALY",
                "badge_color": "pink",
                "description": "Synthetic deed injected with pixel-level local variance tampering and optical seam artifacts on transferred area coordinates.",
                "image_filename": "IMG-EXP-0013.png",
                "image_path": "data/targeted_expansion/images/IMG-EXP-0013.png",
                "expected_category": "CONFIRMED_INCONSISTENCY",
                "preset_fields": {
                    "deed_number": "DEED-2021-65260",
                    "dag_plot_number": "5235",
                    "transferred_area_decimal": "49.50",
                    "execution_date": "2021-08-28",
                    "seller_nid": "OWN-ADC08EC2",
                    "buyer_nid": "OWN-C796273C",
                    "previous_deed_ref": "DEED-2017-81623",
                    "mutation_case_no": "MUT-2021-7367/Hathazari",
                    "consideration_bdt": "6649816.61",
                    "khatian_number": "76",
                },
            },
            {
                "case_id": "DEMO-ALTERED-PLOT",
                "title": "Altered Dag Plot Discrepancy",
                "category": "ALTERED_PLOT_NUMBER",
                "badge": "STATUTORY CONTRADICTION",
                "badge_color": "red",
                "description": "Deed specifies Dag Plot #6274, which is absent from certified cadastral survey records for Savar Upazila.",
                "image_filename": "IMG-9A9BB83D.png",
                "image_path": "data/full/images/IMG-9A9BB83D.png",
                "expected_category": "CONFIRMED_INCONSISTENCY",
                "preset_fields": {
                    "deed_number": "DEED-2011-19951",
                    "dag_plot_number": "6274",
                    "transferred_area_decimal": "51.96",
                    "execution_date": "2011-08-19",
                    "seller_nid": "OWN-9A9BB83D",
                    "buyer_nid": "OWN-BUYER-03",
                    "previous_deed_ref": "DEED-2003-50160",
                    "mutation_case_no": "MUT-2011-540/Savar",
                    "consideration_bdt": "4200000.00",
                    "khatian_number": "905",
                },
            },
            {
                "case_id": "DEMO-MISSING-ARCHIVE",
                "title": "Unindexed Pre-1972 Archival Reference",
                "category": "AMBIGUOUS_UNTRACED_PRE1972_DEED",
                "badge": "MISSING EVIDENCE",
                "badge_color": "amber",
                "description": "Pre-1972 unregistered historical partition volume. Requires physical sub-registry archive retrieval before registration approval.",
                "image_filename": "IMG-EXP-0001.png",
                "image_path": "data/targeted_expansion/images/IMG-EXP-0001.png",
                "expected_category": "MISSING_EVIDENCE",
                "preset_fields": {
                    "deed_number": "DEED-1968-04192",
                    "dag_plot_number": "5510",
                    "transferred_area_decimal": "65.00",
                    "execution_date": "1968-12-05",
                    "seller_nid": "OWN-ARCH-001",
                    "buyer_nid": "OWN-ARCH-002",
                    "previous_deed_ref": "CS-RECORD-1920-UNINDEXED",
                    "mutation_case_no": "MUT-HISTORICAL-PENDING",
                    "consideration_bdt": "45000.00",
                    "khatian_number": "102",
                },
            },
            {
                "case_id": "DEMO-MISSING-EVIDENCE",
                "title": "Unindexed Historical Archive (Missing Evidence)",
                "category": "INCOMPLETE_CHAIN_UNINDEXED",
                "badge": "MISSING EVIDENCE",
                "badge_color": "amber",
                "description": "Pre-1972 unregistered historical partition volume. Requires physical sub-registry archive retrieval before registration approval.",
                "image_filename": "IMG-EXP-0001.png",
                "image_path": "data/targeted_expansion/images/IMG-EXP-0001.png",
                "expected_category": "MISSING_EVIDENCE",
                "preset_fields": {
                    "deed_number": "DEED-1968-04192",
                    "dag_plot_number": "5510",
                    "transferred_area_decimal": "65.00",
                    "execution_date": "1968-12-05",
                    "seller_nid": "OWN-ARCH-001",
                    "buyer_nid": "OWN-ARCH-002",
                    "previous_deed_ref": "CS-RECORD-1920-UNINDEXED",
                    "mutation_case_no": "MUT-HISTORICAL-PENDING",
                    "consideration_bdt": "45000.00",
                    "khatian_number": "102",
                },
            },
        ]
