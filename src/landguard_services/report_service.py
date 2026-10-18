"""Report Domain Service
Handles generation of evidence reports, PDF dossiers, QR codes, report lifecycle transitions, and sanitized public inspection.
"""

import json
import hashlib
import datetime
from typing import Dict, Any, Optional, Callable
from src.landguard_data.database import LandGuardDatabase


class ReportService:
    """Domain service managing verification certificates, report lifecycle, and public exports."""

    def __init__(
        self,
        db: Optional[LandGuardDatabase] = None,
        get_verification_record_fn: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        seeded_dossiers: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.db = db or LandGuardDatabase()
        self._get_verification_record = get_verification_record_fn
        self._seeded_dossiers = seeded_dossiers if seeded_dossiers is not None else {}

    def generate_report(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Generates an evidence dossier certificate with SHA-256 integrity hash."""
        if not self._get_verification_record:
            return None
        target_rec = self._get_verification_record(verification_id)
        if not target_rec:
            return None

        sha256_cert = target_rec.get("sha256_hash")
        if not sha256_cert:
            evidence_payload = json.dumps({
                "verification_id": target_rec["verification_id"],
                "timestamp": target_rec["timestamp"],
                "deed_number": target_rec["deed_number"],
                "dag_plot_number": target_rec["dag_plot_number"],
                "overall_status": target_rec["overall_status"],
                "rules_triggered": target_rec["rules_triggered"],
                "ml_risk_score": target_rec["ml_risk_score"],
            }, sort_keys=True)
            sha256_cert = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()
            target_rec["sha256_hash"] = sha256_cert

        return {
            "report_id": f"REP-{verification_id}",
            "verification": target_rec,
            "sha256_certificate_hash": sha256_cert,
            "issued_at": datetime.datetime.now().isoformat(),
            "issuing_authority": "LandGuard Statutory Verification Engine (Research Benchmark)",
            "watermark_notice": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
            "legal_notice": "This document is an algorithmic audit report generated for scientific research and evaluation purposes under the Evidence Act statutory verification framework.",
        }

    def update_report_status(
        self,
        verification_id: str,
        new_status: str,
        reason: Optional[str] = None,
        user_id: str = "USR-ADMIN-001",
    ) -> Optional[Dict[str, Any]]:
        """Updates report lifecycle status (VALID, WITHDRAWN, SUPERSEDED, RE_REVIEW_REQUIRED) and logs audit event."""
        valid_statuses = ["VALID", "WITHDRAWN", "SUPERSEDED", "RE_REVIEW_REQUIRED"]
        status_clean = (new_status or "").strip().upper()
        if status_clean not in valid_statuses:
            raise ValueError(f"Invalid report status '{new_status}'. Must be one of: {', '.join(valid_statuses)}")

        if not self._get_verification_record:
            return None
        rec = self._get_verification_record(verification_id)
        if not rec:
            return None

        now_iso = datetime.datetime.now().isoformat()
        rec["report_status"] = status_clean
        rec["status_reason"] = (reason or "").strip()
        rec["updated_at"] = now_iso

        if verification_id in self._seeded_dossiers:
            self._seeded_dossiers[verification_id]["report_status"] = status_clean
            self._seeded_dossiers[verification_id]["status_reason"] = (reason or "").strip()
            self._seeded_dossiers[verification_id]["updated_at"] = now_iso

        try:
            self.db.update_verification_report_status(verification_id, status_clean, reason)
            self.db.log_audit_event(
                actor_id=user_id,
                action_type="VERIFICATION_REPORT_STATUS_UPDATED",
                target_entity="VERIFICATION_REPORT",
                target_id=verification_id,
                details={
                    "verification_id": verification_id,
                    "new_status": status_clean,
                    "reason": reason,
                },
            )
        except Exception as e:
            print(f"[ReportService] Warning: Failed to persist report status update to SQLite: {e}")

        return rec

    def get_sanitized_public_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves verification record with citizen PII masked for unauthenticated public inspection."""
        if not self._get_verification_record:
            return None
        rec = self._get_verification_record(verification_id)
        if not rec:
            return None

        def mask_id(val: Optional[str]) -> str:
            if not val:
                return "N/A"
            s = str(val).strip()
            if len(s) <= 4:
                return "****"
            if s.isdigit() and len(s) >= 10:
                p_len = min(6, len(s) // 3)
                s_len = min(4, len(s) // 4)
                m_len = len(s) - p_len - s_len
                return f"{s[:p_len]}{'*' * m_len}{s[-s_len:]}"
            if "-" in s:
                parts = s.split("-")
                if len(parts) >= 2:
                    return f"{parts[0]}-***-{parts[-1][-4:]}"
            return f"{s[:3]}***{s[-3:]}" if len(s) > 6 else "****"

        parcel = rec.get("cadastral_parcel") or {}
        seller_nid = rec.get("seller_nid")
        buyer_nid = rec.get("buyer_nid")

        sanitized = {
            "verification_id": rec.get("verification_id"),
            "deed_number": rec.get("deed_number"),
            "dag_plot_number": rec.get("dag_plot_number"),
            "transferred_area_decimal": rec.get("transferred_area_decimal"),
            "execution_date": rec.get("execution_date"),
            "khatian_number": rec.get("khatian_number") or parcel.get("khatian_number"),
            "mouza": parcel.get("mouza", "N/A"),
            "upazila": parcel.get("upazila", "N/A"),
            "district": parcel.get("district", "N/A"),
            "seller_nid_masked": mask_id(seller_nid),
            "buyer_nid_masked": mask_id(buyer_nid),
            "overall_status": rec.get("overall_status"),
            "report_status": (rec.get("report_status") or "VALID").upper(),
            "status_reason": rec.get("status_reason", ""),
            "ml_risk_score": rec.get("ml_risk_score"),
            "rule_engine_flagged": rec.get("rule_engine_flagged"),
            "rules_triggered": [
                {
                    "rule_code": r.get("rule_code"),
                    "title": r.get("title"),
                    "title_bn": r.get("title_bn"),
                    "category": r.get("category"),
                    "severity": r.get("severity"),
                    "statutory_reference": r.get("statutory_reference"),
                    "explanation": r.get("explanation"),
                    "explanation_bn": r.get("explanation_bn"),
                }
                for r in rec.get("rules_triggered", [])
            ],
            "sha256_hash": rec.get("sha256_hash"),
            "timestamp": rec.get("timestamp"),
            "updated_at": rec.get("updated_at"),
            "disclaimer": "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT",
        }
        return sanitized

    def generate_pdf_report(self, verification_id: str, base_url: str = "http://localhost:8000", lang: str = "bn") -> Optional[bytes]:
        """Generates binary PDF dossier content for a verification record."""
        if not self._get_verification_record:
            return None
        rec = self._get_verification_record(verification_id)
        if not rec:
            return None
        from src.landguard_reports.pdf_generator import generate_verification_pdf
        return generate_verification_pdf(rec, base_url=base_url, lang=lang)
