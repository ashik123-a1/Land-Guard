"""LandGuard Web Verification Service Facade
Coordinates bilingual OCR, human-in-the-loop field confirmation,
cadastral registry lookup, deterministic statutory rule evaluation,
supplementary XGBoost risk scoring, and CV anomaly detection.

Refactored into a layered facade delegating to specialized domain services in src.landguard_services.
"""

import os
import json
import threading
import datetime
from typing import Dict, Any, List, Optional
import joblib

from src.landguard_data.build_splits import assign_grouped_splits
from src.landguard_data.database import LandGuardDatabase
from src.landguard_services import (
    AuthService,
    ComplaintService,
    CaseService,
    NotificationService,
    DocumentService,
    ParcelService,
    ReportService,
    AnalyticsService,
    VerificationService,
    VoiceService,
    RuleGovernanceService,
    ScenarioService,
    RULE_METADATA,
)



class LandGuardVerificationService:
    """Unified facade coordinating domain services, persistence, and shared registry state."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, records_path: str = "data/full/records/canonical_records.json"):
        if getattr(self, "_initialized", False):
            return

        self.records_path = records_path
        uploads_env = os.environ.get("LANDGUARD_UPLOADS_PATH")
        if uploads_env and uploads_env.strip():
            self.upload_dir = os.path.abspath(uploads_env.strip())
        else:
            self.upload_dir = os.path.abspath("data/uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

        self.records_by_scenario: Dict[str, Dict[str, Any]] = {}
        self.records_by_txn_id: Dict[str, Dict[str, Any]] = {}
        self.parcels_by_plot: Dict[str, Dict[str, Any]] = {}
        self.history_by_parcel: Dict[str, List[Dict[str, Any]]] = {}
        self.mutations_by_parcel: Dict[str, List[Dict[str, Any]]] = {}

        self.metadata: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Any] = {}
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.complaints: Dict[str, Dict[str, Any]] = {}
        self.notifications: List[Dict[str, Any]] = []

        self._xgb_model = None
        self.audit_history: List[Dict[str, Any]] = []
        self._seeded_dossiers: Dict[str, Dict[str, Any]] = {}
        self._id_lock = threading.Lock()
        self.db = LandGuardDatabase()

        # Load registry data and models
        self._load_registry_and_model()
        self._init_demo_users()

        # Instantiate specialized domain services
        self.auth = AuthService(db=self.db, fallback_users=self.users)
        self.notifications_svc = NotificationService(db=self.db, notifications_cache=self.notifications)
        self.cases_svc = CaseService(
            db=self.db,
            cases_cache=self.cases,
            id_lock=self._id_lock,
            create_notification_fn=self.create_notification,
        )
        self.complaints_svc = ComplaintService(
            db=self.db,
            complaints_cache=self.complaints,
            cases_cache=self.cases,
            id_lock=self._id_lock,
            get_user_profile_fn=self.get_user_profile,
            create_case_fn=self.create_case,
            update_case_fn=self.update_case,
            create_notification_fn=self.create_notification,
        )
        self.documents_svc = DocumentService(db=self.db, upload_dir=self.upload_dir)
        self.parcels_svc = ParcelService(
            parcels_by_plot=self.parcels_by_plot,
            history_by_parcel=self.history_by_parcel,
            mutations_by_parcel=self.mutations_by_parcel,
            complaint_repo=self.db.complaints,
            parcel_repo=self.db.parcels,
            audit_repo=self.db.audit,
        )
        self.verification_svc = VerificationService(
            db=self.db,
            parcels_by_plot=self.parcels_by_plot,
            history_by_parcel=self.history_by_parcel,
            mutations_by_parcel=self.mutations_by_parcel,
            audit_history=self.audit_history,
            seeded_dossiers=self._seeded_dossiers,
            xgb_model=self.xgb_model,
        )
        self.reports_svc = ReportService(
            db=self.db,
            get_verification_record_fn=self.get_verification_record,
            seeded_dossiers=self._seeded_dossiers,
        )
        self.analytics_svc = AnalyticsService(
            db=self.db,
            metadata=self.metadata,
            model_metadata=self.model_metadata,
            records_by_scenario=self.records_by_scenario,
            parcels_by_plot=self.parcels_by_plot,
            cases=self.cases,
            complaints=self.complaints,
            audit_history=self.audit_history,
            get_user_profile_fn=self.get_user_profile,
            get_overdue_cases_fn=self.get_overdue_cases,
            xgb_model=self.xgb_model,
        )
        self.voice_svc = VoiceService()
        self.rule_gov = RuleGovernanceService(db=self.db)
        self.scenario_svc = ScenarioService(db=self.db)

        # Seed initial demo state

        self._seed_complaints_and_notifications()
        self._seed_sample_verifications()
        self._load_persisted_parcels()

        self._initialized = True

    def rebind_database(self, db_path: Optional[str] = None):
        """Rebinds database and all domain services to a specified database path.
        Used to guarantee that tests point to an isolated disposable database."""
        self.db = LandGuardDatabase(db_path=db_path)
        if hasattr(self, "auth"):
            self.auth.db = self.db
        if hasattr(self, "notifications_svc"):
            self.notifications_svc.db = self.db
        if hasattr(self, "cases_svc"):
            self.cases_svc.db = self.db
        if hasattr(self, "complaints_svc"):
            self.complaints_svc.db = self.db
        if hasattr(self, "documents_svc"):
            self.documents_svc.db = self.db
        if hasattr(self, "verification_svc"):
            self.verification_svc.db = self.db
        if hasattr(self, "reports_svc"):
            self.reports_svc.db = self.db
        if hasattr(self, "analytics_svc"):
            self.analytics_svc.db = self.db
        if hasattr(self, "rule_gov"):
            self.rule_gov.db = self.db
        if hasattr(self, "scenario_svc"):
            self.scenario_svc.db = self.db
        if hasattr(self, "parcels_svc"):
            self.parcels_svc.complaint_repo = self.db.complaints
            self.parcels_svc.parcel_repo = self.db.parcels
            self.parcels_svc.audit_repo = self.db.audit
        self._load_persisted_parcels()
        return self.db

    def _load_persisted_parcels(self):
        """Loads any custom cadastral parcels registered in database into memory cache."""
        try:
            if hasattr(self.db, "parcels"):
                db_parcels = self.db.parcels.list_parcels(limit=5000)
                for p in db_parcels:
                    plot_str = str(p.get("dag_plot_number", "")).strip()
                    if plot_str and plot_str not in self.parcels_by_plot:
                        self.parcels_by_plot[plot_str] = dict(p)
                        if plot_str not in self.history_by_parcel:
                            self.history_by_parcel[plot_str] = []
                        if plot_str not in self.mutations_by_parcel:
                            self.mutations_by_parcel[plot_str] = []
        except Exception as e:
            print(f"[LandGuard Service] Warning: Failed to load persisted parcels: {e}")

    @property
    def xgb_model(self):
        if hasattr(self, "verification_svc"):
            return self.verification_svc.xgb_model
        return getattr(self, "_xgb_model", None)

    @xgb_model.setter
    def xgb_model(self, val):
        self._xgb_model = val
        if hasattr(self, "verification_svc"):
            self.verification_svc.xgb_model = val
        if hasattr(self, "analytics_svc"):
            self.analytics_svc.xgb_model = val

    def _load_registry_and_model(self):
        """Loads canonical registry data into fast in-memory indices and initializes XGBoost."""
        if not os.path.exists(self.records_path):
            print(f"Warning: {self.records_path} not found. Running in degraded mock mode.")
            return

        with open(self.records_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.metadata = data.get("metadata", {})

        dataset_records = data.get("dataset_records", [])
        for i, r in enumerate(dataset_records):
            p = r["parcel"]
            pid = p["parcel_id"]
            plot_str = str(p["dag_plot_number"]).strip()

            r["parcel_id"] = pid
            if "primary_seller_id" not in r:
                r["primary_seller_id"] = r["transaction"]["seller_ids"][0]
            if "template_cohort" not in r:
                r["template_cohort"] = f"TMPL-COHORT-{(i // 100) + 1:02d}"

            scen_id = r.get("scenario_id")
            if scen_id:
                self.records_by_scenario[scen_id] = r

            txn_id = r["transaction"].get("transaction_id")
            if txn_id:
                self.records_by_txn_id[txn_id] = r

            if plot_str not in self.parcels_by_plot:
                self.parcels_by_plot[plot_str] = p
                self.history_by_parcel[plot_str] = r.get("history_transactions", [])
                self.mutations_by_parcel[plot_str] = r.get("mutations", [])

        targeted_path = "data/targeted_expansion/records/targeted_records.json"
        if os.path.exists(targeted_path):
            try:
                with open(targeted_path, "r", encoding="utf-8") as f_t:
                    t_data = json.load(f_t)
                for r in t_data.get("dataset_records", []):
                    p = r.get("parcel")
                    if p:
                        plot_str = str(p.get("dag_plot_number")).strip()
                        if plot_str not in self.parcels_by_plot:
                            self.parcels_by_plot[plot_str] = p
                            self.history_by_parcel[plot_str] = r.get("history_transactions", [])
                            self.mutations_by_parcel[plot_str] = r.get("mutations", [])
            except Exception as e:
                print(f"Warning: Failed to load targeted records: {e}")

        pilot_path = "data/pilot/records/pilot_records.json"
        if os.path.exists(pilot_path):
            try:
                with open(pilot_path, "r", encoding="utf-8") as f_p:
                    p_data = json.load(f_p)
                for r in p_data.get("dataset_records", []):
                    p = r.get("parcel")
                    if p:
                        plot_str = str(p.get("dag_plot_number")).strip()
                        if plot_str not in self.parcels_by_plot:
                            self.parcels_by_plot[plot_str] = p
                            self.history_by_parcel[plot_str] = r.get("history_transactions", [])
                            self.mutations_by_parcel[plot_str] = r.get("mutations", [])
            except Exception as e:
                print(f"Warning: Failed to load pilot records: {e}")

        frozen_model_path = os.path.abspath("models/xgboost_risk_model.joblib")
        if os.path.exists(frozen_model_path):
            try:
                self.xgb_model = joblib.load(frozen_model_path)
                print(f"[LandGuard Service] Loaded frozen XGBoost risk model from {frozen_model_path}")
            except Exception as e:
                print(f"Warning: Failed to load frozen model from disk: {e}")
                self.xgb_model = None

        meta_path = os.path.abspath("models/model_metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f_m:
                    self.model_metadata = json.load(f_m)
            except Exception as e:
                print(f"Warning: Failed to load model metadata: {e}")

        self._seed_default_cases()

    def _seed_default_cases(self):
        """Seeds realistic demonstration investigation cases."""
        now = datetime.datetime.now().isoformat()
        self.cases["CASE-2026-001"] = {
            "case_id": "CASE-2026-001",
            "created_at": now,
            "updated_at": now,
            "title": "Double Disposition & Broken Ancestral Chain on Dag #6792",
            "deed_number": "DEED-2005-23539",
            "dag_plot_number": "6792",
            "verification_id": "VRF-SEED-001",
            "status": "UNDER_REVIEW",
            "priority": "HIGH",
            "assigned_officer": "Senior Registrar M. Rahman",
            "statutory_finding": "CONFIRMED_INCONSISTENCY",
            "ml_risk_score": 0.945,
            "evidence_summary": "Seller previously conveyed entire holding capacity to an earlier buyer. Prior conveyance verified in Book 1.",
            "officer_notes": [
                {
                    "timestamp": now,
                    "author": "System",
                    "note": "Case opened following statutory verification failure: RULE_CONFLICTING_DOUBLE_DISPOSITION triggered.",
                },
                {
                    "timestamp": now,
                    "author": "Senior Registrar M. Rahman",
                    "note": "Requested physical Volume 12-A from Paba sub-registry archives to verify vendor signature against 2000 sale deed.",
                },
            ],
        }
        self.cases["CASE-2026-002"] = {
            "case_id": "CASE-2026-002",
            "created_at": now,
            "updated_at": now,
            "title": "Suspected Physical Paste-Over Patch on Plot #5235",
            "deed_number": "DEED-2021-65260",
            "dag_plot_number": "5235",
            "verification_id": "VRF-SEED-002",
            "status": "OPEN",
            "priority": "CRITICAL",
            "assigned_officer": "Inspector S. Karim",
            "statutory_finding": "CONFIRMED_INCONSISTENCY",
            "ml_risk_score": 0.982,
            "evidence_summary": "Computer Vision detected 1 isolated rectangular paste-over seam (96% anomaly confidence) over plot schedule.",
            "officer_notes": [
                {
                    "timestamp": now,
                    "author": "System",
                    "note": "Case opened automatically due to high visual anomaly score (>0.85).",
                }
            ],
        }

    def _init_demo_users(self):
        """Initializes seeded demo identities for Citizen, Investigator, and Admin roles."""
        self.users = {
            "citizen@landguard.gov.bd": {
                "user_id": "USR-CITIZEN-001",
                "email": "citizen@landguard.gov.bd",
                "password": "demo123",
                "full_name": "Nakib Md Ashik",
                "role": "CITIZEN",
                "national_id": "19882691234567890",
                "digital_identity_id": "CIT-BD-884920",
                "phone": "+880 1712-345678",
                "division": "Dhaka",
                "district": "Dhaka",
                "upazila": "Savar",
                "card_valid_thru": "12/28",
                "registered_parcels": ["9044", "7025"],
                "created_at": "2025-01-15T09:00:00Z",
            },
            "investigator@landguard.gov.bd": {
                "user_id": "USR-INVESTIGATOR-001",
                "email": "investigator@landguard.gov.bd",
                "password": "demo123",
                "full_name": "Inspector S. Karim",
                "role": "INVESTIGATOR",
                "staff_id": "OFF-INV-2041",
                "department": "Land Fraud Investigation Unit",
                "division": "Dhaka",
                "clearance_level": "LEVEL-3 SPECIAL INVESTIGATOR",
                "created_at": "2024-06-10T10:00:00Z",
            },
            "admin@landguard.gov.bd": {
                "user_id": "USR-ADMIN-001",
                "email": "admin@landguard.gov.bd",
                "password": "admin123",
                "full_name": "Hasin Ishruq Nabil",
                "role": "ADMIN",
                "staff_id": "ADM-REG-1001",
                "department": "Office of the Inspector General of Registration",
                "division": "National Secretariat",
                "clearance_level": "LEVEL-5 CHIEF REGISTRAR",
                "created_at": "2024-01-01T08:00:00Z",
            },
        }

    def _seed_complaints_and_notifications(self):
        """Seeds realistic citizen complaints and system notifications."""
        now = datetime.datetime.now()
        iso_now = now.isoformat()
        iso_prev_day = (now - datetime.timedelta(days=1)).isoformat()
        iso_prev_week = (now - datetime.timedelta(days=6)).isoformat()

        self.complaints["CMP-2026-001"] = {
            "complaint_id": "CMP-2026-001",
            "citizen_user_id": "USR-CITIZEN-001",
            "citizen_name": "Nakib Md Ashik",
            "title": "Double Disposition Claim on Dag Plot #6792 (Paba Upazila)",
            "category": "SUSPECTED_DOUBLE_SALE",
            "dag_plot_number": "6792",
            "deed_number": "DEED-2005-23539",
            "narrative_description": "I entered into a preliminary agreement to purchase Plot #6792. However, local AC Land records indicate vendor previously executed deed DEED-2000-41374 conveying full holding capacity. Vendor claims deed was cancelled but no court decree is presented.",
            "status": "UNDER_REVIEW",
            "is_expedited": True,
            "expedite_reason": "Vendor demands earnest money deposit within 48 hours or threatens forfeiture.",
            "expedite_status": "APPROVED",
            "assigned_officer": "Senior Registrar M. Rahman",
            "linked_case_id": "CASE-2026-001",
            "created_at": iso_prev_day,
            "updated_at": iso_now,
            "timeline": [
                {
                    "timestamp": iso_prev_day,
                    "title": "Complaint Lodged",
                    "description": "Citizen filed formal grievance via LandGuard portal with verified NID hash.",
                    "actor": "Nakib Md Ashik (Citizen)",
                },
                {
                    "timestamp": iso_prev_day,
                    "title": "Expedited Review Requested",
                    "description": "Justification: Imminent vendor earnest money ultimatum.",
                    "actor": "Nakib Md Ashik (Citizen)",
                },
                {
                    "timestamp": iso_now,
                    "title": "Expedite Approved & Investigator Assigned",
                    "description": "Assigned to Senior Registrar M. Rahman. Expedite criteria met under Urgent Impending Transaction clause.",
                    "actor": "Admin Operations",
                },
            ],
        }

        self.complaints["CMP-2026-002"] = {
            "complaint_id": "CMP-2026-002",
            "citizen_user_id": "USR-CITIZEN-001",
            "citizen_name": "Nakib Md Ashik",
            "title": "Suspicious Patch / Whiteout Seam on Plot #5235 Schedule",
            "category": "DOCUMENT_INTEGRITY_CONCERN",
            "dag_plot_number": "5235",
            "deed_number": "DEED-2021-65260",
            "narrative_description": "The certified copy presented by broker shows abnormal rectangular discoloration over the Dag number area. Computer Vision inspection flagged 96% anomaly confidence.",
            "status": "OPEN",
            "is_expedited": False,
            "expedite_reason": None,
            "expedite_status": "NONE",
            "assigned_officer": "Inspector S. Karim",
            "linked_case_id": "CASE-2026-002",
            "created_at": iso_prev_week,
            "updated_at": iso_prev_week,
            "timeline": [
                {
                    "timestamp": iso_prev_week,
                    "title": "Complaint Lodged",
                    "description": "Citizen flagged visual seam anomaly in deed schedule.",
                    "actor": "Nakib Md Ashik (Citizen)",
                }
            ],
        }

        self.notifications = [
            {
                "notification_id": "NOTIF-001",
                "recipient_user_id": "USR-CITIZEN-001",
                "title": "Expedited Review Approved",
                "message": "Your expedited review request for Complaint CMP-2026-001 has been approved by the Senior Registrar.",
                "link_url": "/user/complaints/CMP-2026-001",
                "type": "SUCCESS",
                "is_read": False,
                "created_at": iso_now,
            },
            {
                "notification_id": "NOTIF-002",
                "recipient_user_id": "USR-CITIZEN-001",
                "title": "Verification Completed: Clean Title",
                "message": "Verification VRF-CLEAN-001 for Plot #9044 passed all statutory rules with 0.04% ML risk.",
                "link_url": "/user/verify/VRF-CLEAN-001",
                "type": "INFO",
                "is_read": True,
                "created_at": iso_prev_day,
            },
            {
                "notification_id": "NOTIF-003",
                "recipient_user_id": "USR-INVESTIGATOR-001",
                "title": "Critical Priority Case Assigned",
                "message": "You have been assigned to investigate suspected physical alteration on Plot #5235.",
                "link_url": "/admin/cases/CASE-2026-002",
                "type": "WARNING",
                "is_read": False,
                "created_at": iso_now,
            },
            {
                "notification_id": "NOTIF-004",
                "recipient_user_id": "USR-ADMIN-001",
                "title": "Expedite Queue Alert",
                "message": "Citizen Nakib Md Ashik requested expedited review on double disposition complaint CMP-2026-001.",
                "link_url": "/admin/cases/CASE-2026-001",
                "type": "INFO",
                "is_read": False,
                "created_at": iso_now,
            },
        ]

    def _seed_sample_verifications(self):
        """Pre-populates audit history with verified benchmark scenarios."""
        samples = self.get_sample_cases()
        now = datetime.datetime.now()

        for idx, sample in enumerate(samples[:4]):
            v_id = f"VRF-HIST-{idx+1:03d}"
            fields = sample.get("preset_fields", {})
            cat = sample.get("expected_category", "CLEAR_FOR_STANDARD_PROCESSING")
            is_flagged = cat != "CLEAR_FOR_STANDARD_PROCESSING"
            ts = (now - datetime.timedelta(hours=(idx + 1) * 6)).isoformat()

            plot_no = fields.get("dag_plot_number", "9044")
            parcel_match = self.parcels_by_plot.get(plot_no)
            if not parcel_match and self.parcels_by_plot:
                parcel_match = next(iter(self.parcels_by_plot.values()))

            rules_list = []
            if is_flagged:
                rcode = "RULE_CONFLICTING_DOUBLE_DISPOSITION" if "DOUBLE" in sample["case_id"] else "RULE_AREA_EXCEEDS_CAPACITY"
                rmeta = RULE_METADATA.get(rcode, {})
                rules_list.append({
                    "rule_code": rcode,
                    "title": rmeta.get("title", "Statutory Contradiction"),
                    "category": "CONFIRMED_INCONSISTENCY",
                    "severity": "CRITICAL" if "DOUBLE" in sample["case_id"] else "HIGH",
                    "statutory_reference": rmeta.get("statutory_reference", "Registration Act 1908 s.47 / SAT Act s.143"),
                    "explanation": sample.get("description", ""),
                    "next_step": rmeta.get("next_step", "Inspect physical volume register and verify field cadastral survey."),
                })

            import hashlib
            payload = json.dumps({
                "verification_id": v_id,
                "timestamp": ts,
                "deed_number": fields.get("deed_number", f"DEED-2020-{1000+idx}"),
                "dag_plot_number": plot_no,
                "overall_status": cat,
                "rules_triggered": rules_list,
                "ml_risk_score": 0.945 if is_flagged else 0.042,
            }, sort_keys=True)
            sha_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            rec = {
                "verification_id": v_id,
                "timestamp": ts,
                "user_id": "USR-CITIZEN-001",
                "deed_number": fields.get("deed_number", f"DEED-2020-{1000+idx}"),
                "dag_plot_number": plot_no,
                "transferred_area_decimal": float(fields.get("transferred_area_decimal", 10.0)),
                "execution_date": fields.get("execution_date", "2020-01-01"),
                "seller_nid": fields.get("seller_nid", "OWN-DEMO-01"),
                "buyer_nid": fields.get("buyer_nid", "OWN-DEMO-02"),
                "previous_deed_ref": fields.get("previous_deed_ref", "INHERITED_ANCESTRAL_CS_RECORD"),
                "mutation_case_no": fields.get("mutation_case_no", f"MUT-2020-{plot_no}/Savar"),
                "consideration_bdt": float(fields.get("consideration_bdt", 1500000.0)),
                "khatian_number": fields.get("khatian_number", str(parcel_match.get("khatian_number", "812") if parcel_match else "812")),
                "overall_status": cat,
                "rule_engine_flagged": is_flagged,
                "rules_triggered": rules_list,
                "ml_risk_score": 0.945 if is_flagged else 0.042,
                "ml_threshold": 0.35,
                "sha256_hash": sha_digest,
                "recommended_action": "HOLD_FOR_STATUTORY_VERIFICATION" if is_flagged else "PROCEED_WITH_STANDARD_REVIEW",
                "cadastral_parcel": parcel_match,
                "cadastral_found": parcel_match is not None,
                "cv_evidence": {
                    "visual_anomaly_detected": "TAMPERING" in sample["case_id"],
                    "visual_anomaly_score": 0.96 if "TAMPERING" in sample["case_id"] else 0.02,
                    "seal_present": True,
                    "signature_present": True,
                    "detected_patches": 1 if "TAMPERING" in sample["case_id"] else 0,
                },
                "field_edits_by_user": {},
                "explanation_summary": f"Verification completed under benchmark scenario {sample['case_id']}.",
                "disclaimer": "This assessment is algorithmic decision support under statutory verification rules.",
                "synthetic_disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
            }
            self.audit_history.append(rec)
            self._seeded_dossiers[v_id] = dict(rec)
            try:
                self.db.save_verification_run(rec, rules_list)
            except Exception:
                pass

    # ---------------------------------------------------------
    # Delegated Domain Service Methods
    # ---------------------------------------------------------

    # Verification Service
    def get_sample_cases(self) -> List[Dict[str, Any]]:
        return self.verification_svc.get_sample_cases()

    def verify_transaction(
        self,
        confirmed_fields: Dict[str, Any],
        image_path: Optional[str] = None,
        original_ocr_fields: Optional[Dict[str, Any]] = None,
        evidence_source: Optional[str] = "UPLOAD",
    ) -> Dict[str, Any]:
        return self.verification_svc.verify_transaction(
            confirmed_fields=confirmed_fields,
            image_path=image_path,
            original_ocr_fields=original_ocr_fields,
            evidence_source=evidence_source,
        )

    def get_verification_record(self, verification_id: str) -> Optional[Dict[str, Any]]:
        return self.verification_svc.get_verification_record(verification_id=verification_id)

    def lookup_deed(self, deed_number: str) -> Optional[Dict[str, Any]]:
        """Finds a deed and associated verification/transaction records across in-memory dossiers and database."""
        if not deed_number:
            return None
        clean = str(deed_number).strip().upper()
        clean_core = clean[5:] if clean.startswith("DEED-") else clean

        # 1. Search in verification dossiers (audit_history and _seeded_dossiers)
        for r in list(self.audit_history):
            d_num = str(r.get("deed_number", "")).strip().upper()
            if d_num == clean or (clean_core and (d_num == f"DEED-{clean_core}" or d_num.endswith(f"-{clean_core}"))):
                return dict(r)

        if hasattr(self, "_seeded_dossiers"):
            for r in self._seeded_dossiers.values():
                d_num = str(r.get("deed_number", "")).strip().upper()
                if d_num == clean or (clean_core and (d_num == f"DEED-{clean_core}" or d_num.endswith(f"-{clean_core}"))):
                    return dict(r)

        # 2. Search in verification_runs table in SQLite
        if hasattr(self, "db") and self.db:
            try:
                conn = self.db._get_connection()
                cur = conn.execute(
                    """
                    SELECT * FROM verification_runs
                    WHERE UPPER(deed_number) = ? OR UPPER(deed_number) = ? OR deed_number LIKE ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (clean, f"DEED-{clean}", f"%-{clean_core}"),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
            except Exception:
                pass

        # 3. Search in canonical dataset records / transactions
        for r in getattr(self, "records_by_scenario", {}).values():
            txn = r.get("transaction", {})
            d_num = str(txn.get("deed_number", "")).strip().upper()
            if d_num == clean or (clean_core and (d_num == f"DEED-{clean_core}" or d_num.endswith(f"-{clean_core}"))):
                return {
                    "deed_number": txn.get("deed_number"),
                    "dag_plot_number": r.get("parcel", {}).get("dag_plot_number"),
                    "transaction_id": txn.get("transaction_id"),
                    "execution_date": txn.get("execution_date"),
                    "transferred_area_decimal": txn.get("transferred_area_decimal"),
                    "deed_type": txn.get("deed_type"),
                }
            for ht in r.get("history_transactions", []):
                d_num = str(ht.get("deed_number", "")).strip().upper()
                if d_num == clean or (clean_core and (d_num == f"DEED-{clean_core}" or d_num.endswith(f"-{clean_core}"))):
                    return {
                        "deed_number": ht.get("deed_number"),
                        "dag_plot_number": r.get("parcel", {}).get("dag_plot_number"),
                        "transaction_id": ht.get("transaction_id"),
                        "execution_date": ht.get("execution_date"),
                        "transferred_area_decimal": ht.get("transferred_area_decimal"),
                        "deed_type": ht.get("deed_type"),
                    }

        return None

    def record_verification_decision(
        self,
        verification_id: str,
        decision: str,
        reason: str,
        user_id: str,
        officer_name: str,
    ) -> Optional[Dict[str, Any]]:
        return self.verification_svc.record_verification_decision(
            verification_id=verification_id,
            decision=decision,
            reason=reason,
            user_id=user_id,
            officer_name=officer_name,
        )

    # Document Service
    def process_document_upload(
        self,
        file_bytes: bytes,
        filename: str,
        uploaded_by: str = "USR-CITIZEN-001",
    ) -> Dict[str, Any]:
        return self.documents_svc.process_document_upload(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=uploaded_by,
        )

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self.documents_svc.get_document(document_id=document_id)

    def reanalyze_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self.documents_svc.reanalyze_document(document_id=document_id)

    def delete_document(
        self,
        document_id: str,
        user_id: str = "USR-CITIZEN-001",
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        return self.documents_svc.delete_document(
            document_id=document_id,
            user_id=user_id,
            is_admin=is_admin,
        )

    def _compute_field_uncertainties(self, extracted: Dict[str, Any], lines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return self.documents_svc._compute_field_uncertainties(extracted=extracted, lines=lines)


    # Report Service
    def generate_report(self, verification_id: str) -> Optional[Dict[str, Any]]:
        return self.reports_svc.generate_report(verification_id=verification_id)

    def update_report_status(
        self,
        verification_id: str,
        new_status: str,
        reason: Optional[str] = None,
        user_id: str = "USR-ADMIN-001",
    ) -> Optional[Dict[str, Any]]:
        return self.reports_svc.update_report_status(
            verification_id=verification_id,
            new_status=new_status,
            reason=reason,
            user_id=user_id,
        )

    def get_sanitized_public_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        return self.reports_svc.get_sanitized_public_verification(verification_id=verification_id)

    def generate_pdf_report(self, verification_id: str, base_url: str = "http://localhost:8000", lang: str = "bn") -> Optional[bytes]:
        return self.reports_svc.generate_pdf_report(verification_id=verification_id, base_url=base_url, lang=lang)

    # Parcel Service
    def search_parcels(self, query: str = "", limit: int = 15) -> List[Dict[str, Any]]:
        return self.parcels_svc.search_parcels(query=query, limit=limit)

    def get_parcel_details(self, plot_or_id: str) -> Optional[Dict[str, Any]]:
        return self.parcels_svc.get_parcel_details(plot_or_id=plot_or_id)

    def get_cadastral_graph(self, plot_or_id: str) -> Optional[Dict[str, Any]]:
        return self.parcels_svc.get_cadastral_graph(plot_or_id=plot_or_id)

    def simulate_what_if_transaction(self, sim_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.parcels_svc.simulate_what_if_transaction(sim_data=sim_data)

    def analyze_cross_parcel_patterns(self, query_identifier: str) -> Dict[str, Any]:
        return self.parcels_svc.analyze_cross_parcel_patterns(query_identifier=query_identifier)

    def create_parcel(self, data: Dict[str, Any], actor_id: str = "USR-ADMIN-001") -> Dict[str, Any]:
        return self.parcels_svc.create_parcel(data=data, actor_id=actor_id)

    # Case Service
    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.cases_svc.create_case(case_data=case_data)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self.cases_svc.get_case(case_id=case_id)

    def list_cases(self, status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.cases_svc.list_cases(status=status, priority=priority)

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.cases_svc.update_case(case_id=case_id, updates=updates)

    def add_case_note(self, case_id: str, note_text: str, author: str = "Officer") -> Optional[Dict[str, Any]]:
        return self.cases_svc.add_case_note(case_id=case_id, note_text=note_text, author=author)

    def compute_case_sla(self, case_or_id: Any) -> Dict[str, Any]:
        return self.cases_svc.compute_case_sla(case_or_id=case_or_id)

    def get_overdue_cases(self) -> List[Dict[str, Any]]:
        return self.cases_svc.get_overdue_cases()

    def process_sla_escalations(self) -> List[Dict[str, Any]]:
        return self.cases_svc.process_sla_escalations()

    def request_case_clarification(
        self,
        case_id: str,
        question: str,
        officer_id: str = "USR-ADMIN-001",
        officer_name: str = "Senior Registrar M. Rahman",
    ) -> Optional[Dict[str, Any]]:
        return self.cases_svc.request_case_clarification(
            case_id=case_id,
            question=question,
            officer_id=officer_id,
            officer_name=officer_name,
        )

    def respond_case_clarification(
        self,
        case_id: str,
        response_text: str,
        user_id: str = "USR-CITIZEN-001",
        user_name: str = "Nakib Md Ashik",
        user_role: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.cases_svc.respond_case_clarification(
            case_id=case_id,
            response_text=response_text,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
        )

    def get_case_for_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        return self.cases_svc.get_case_for_verification(verification_id=verification_id)

    # Complaint Service
    def create_complaint(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.complaints_svc.create_complaint(user_id=user_id, data=data)

    def get_complaint(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        return self.complaints_svc.get_complaint(complaint_id=complaint_id)

    def list_complaints(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.complaints_svc.list_complaints(user_id=user_id, status=status, category=category)

    def request_expedited_review(self, complaint_id: str, user_id: str, reason: str, reason_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.complaints_svc.request_expedited_review(complaint_id=complaint_id, user_id=user_id, reason=reason, reason_category=reason_category)

    def decide_expedite(
        self,
        complaint_id: str,
        decision: str,
        reason: str,
        officer: str = "Admin",
    ) -> Optional[Dict[str, Any]]:
        return self.complaints_svc.decide_expedite(
            complaint_id=complaint_id,
            decision=decision,
            reason=reason,
            officer=officer,
        )

    def analyze_complaint_ai(
        self,
        complaint_id: str,
        viewer_user_id: Optional[str] = None,
        is_staff: bool = False,
    ) -> Optional[Dict[str, Any]]:
        return self.complaints_svc.analyze_complaint_ai(
            complaint_id=complaint_id,
            viewer_user_id=viewer_user_id,
            is_staff=is_staff,
        )

    # Auth & Sessions
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        return self.auth.authenticate_user(email=email, password=password)

    def create_session(self, user_dict: Dict[str, Any]) -> str:
        return self.auth.create_session(user_dict=user_dict)

    def get_user_by_session(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        return self.auth.get_user_by_session(session_id=session_id)

    def destroy_session(self, session_id: Optional[str]):
        return self.auth.destroy_session(session_id=session_id)

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.auth.get_user_profile(user_id=user_id)

    def list_users(self) -> List[Dict[str, Any]]:
        return self.auth.list_users()

    def update_user_preference(self, user_id: str, preferred_language: str) -> bool:
        return self.auth.update_user_preference(user_id=user_id, preferred_language=preferred_language)

    # Notifications
    def create_notification(
        self,
        recipient_user_id: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        notif_type: str = "INFO",
    ) -> Dict[str, Any]:
        return self.notifications_svc.create_notification(
            recipient_user_id=recipient_user_id,
            title=title,
            message=message,
            link_url=link_url,
            notif_type=notif_type,
        )

    def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        return self.notifications_svc.get_notifications(user_id=user_id)

    def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        return self.notifications_svc.mark_notification_read(notification_id=notification_id, user_id=user_id)

    def mark_all_notifications_read(self, user_id: str) -> int:
        return self.notifications_svc.mark_all_read(user_id=user_id)

    # Analytics & Audit
    def get_dashboard_stats(self) -> Dict[str, Any]:
        return self.analytics_svc.get_dashboard_stats()

    def get_model_evaluation_metrics(self) -> Dict[str, Any]:
        return self.analytics_svc.get_model_evaluation_metrics()

    def get_admin_dashboard_analytics(self, year: Optional[str] = "2026") -> Dict[str, Any]:
        return self.analytics_svc.get_admin_dashboard_analytics(year=year)

    def get_citizen_dashboard(self, user_id: str) -> Dict[str, Any]:
        return self.analytics_svc.get_citizen_dashboard(user_id=user_id)

    def get_audit_trail(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.analytics_svc.get_audit_trail(limit=limit)

    def get_audit_history(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        return self.analytics_svc.get_audit_history(user_id=user_id, limit=limit)

    def clear_audit_history(self):
        return self.analytics_svc.clear_audit_history()

    # Rule Governance & Versioning
    def get_active_ruleset(self) -> Dict[str, Any]:
        return self.rule_gov.get_active_ruleset()

    def get_ruleset_history(self) -> List[Dict[str, Any]]:
        return self.rule_gov.get_ruleset_history()

    def update_ruleset(
        self,
        new_rules: Optional[Dict[str, Any]] = None,
        new_thresholds: Optional[Dict[str, Any]] = None,
        officer: str = "Admin",
        justification: str = "",
    ) -> Dict[str, Any]:
        return self.rule_gov.update_ruleset(
            new_rules=new_rules,
            new_thresholds=new_thresholds,
            officer=officer,
            justification=justification,
        )

    # Seeded Synthetic Scenario Generator
    def get_scenario_catalog(self) -> List[Dict[str, Any]]:
        return self.scenario_svc.get_catalog()

    def generate_reproducible_scenario(
        self,
        scenario_type: str,
        seed: Optional[int] = 42,
    ) -> Dict[str, Any]:
        return self.scenario_svc.generate_reproducible_scenario(
            scenario_type=scenario_type,
            seed=seed,
        )


service = LandGuardVerificationService()

