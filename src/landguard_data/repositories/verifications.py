"""Verification Repository
Handles persistence and querying for verification runs, findings, and report lifecycle.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class VerificationRepository(BaseRepository):
    """Data access repository for verification runs and rule findings."""

    def save_verification_run(self, v_run: Dict[str, Any], findings: Optional[List[Dict[str, Any]]] = None):
        """Persists a complete verification dossier and statutory findings to SQLite."""
        conn = self._get_connection()
        try:
            now = datetime.datetime.now().isoformat()
            vid = v_run["verification_id"]
            user_id = v_run.get("user_id") or "USR-CITIZEN-001"
            # Ensure user exists to satisfy foreign key constraint
            u_check = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not u_check:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO users (user_id, email, password_hash, full_name, role, created_at) VALUES (?, ?, ?, ?, 'CITIZEN', ?)",
                        (user_id, f"{user_id.lower()}@landguard.gov.bd", "auto_generated", user_id, now),
                    )
                except Exception:
                    user_id = "USR-CITIZEN-001"

            rep_status = (v_run.get("report_status") or "VALID").upper()
            stat_reason = v_run.get("status_reason")
            upd_at = v_run.get("updated_at") or now
            conn.execute(
                """
                INSERT OR REPLACE INTO verification_runs (
                    verification_id, user_id, document_id, deed_number, dag_plot_number,
                    transferred_area_decimal, overall_status, rule_engine_flagged,
                    ml_risk_score, ml_risk_tier, recommended_action, sha256_report_hash, created_at,
                    report_status, status_reason, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vid,
                    user_id,
                    v_run.get("document_id"),
                    v_run.get("deed_number"),
                    str(v_run.get("dag_plot_number", "")),
                    float(v_run.get("transferred_area_decimal") or 0.0),
                    v_run.get("overall_status", "UNKNOWN"),
                    1 if v_run.get("rule_engine_flagged") else 0,
                    float(v_run.get("ml_risk_score") or 0.0),
                    v_run.get("ml_risk_tier", "MEDIUM"),
                    v_run.get("recommended_action", "PROCEED_WITH_STANDARD_REVIEW"),
                    v_run.get("sha256_hash") or v_run.get("sha256_certificate_hash"),
                    v_run.get("timestamp") or now,
                    rep_status,
                    stat_reason,
                    upd_at,
                ),
            )
            if findings:
                conn.execute("DELETE FROM verification_findings WHERE verification_id = ?", (vid,))
                for f in findings:
                    fid = f.get("finding_id") or f"FND-{uuid.uuid4().hex[:6].upper()}"
                    conn.execute(
                        """
                        INSERT INTO verification_findings (
                            finding_id, verification_id, finding_code, category, severity,
                            explanation, source_reference, statutory_reference, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fid,
                            vid,
                            f.get("rule_code") or f.get("finding_code", "UNKNOWN_RULE"),
                            f.get("category", "RULE_CHECK"),
                            f.get("severity", "MEDIUM"),
                            f.get("explanation") or f.get("reason", ""),
                            f.get("source_reference", "STATUTORY_RULES_ENGINE"),
                            f.get("statutory_reference", "Registration Act 1908"),
                            now,
                        ),
                    )
            conn.commit()
        finally:
            conn.close()

    def get_verification_run(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a verification run and all associated rule findings."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM verification_runs WHERE verification_id = ?", (verification_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["rule_engine_flagged"] = bool(res.get("rule_engine_flagged"))

            f_cur = conn.execute("SELECT * FROM verification_findings WHERE verification_id = ?", (verification_id,))
            res["findings"] = [dict(f) for f in f_cur.fetchall()]
            return res
        finally:
            conn.close()

    def update_verification_report_status(
        self,
        verification_id: str,
        report_status: str,
        status_reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates report lifecycle state (VALID, WITHDRAWN, SUPERSEDED, RE_REVIEW_REQUIRED)."""
        conn = self._get_connection()
        try:
            now = datetime.datetime.now().isoformat()
            conn.execute(
                """
                UPDATE verification_runs
                SET report_status = ?, status_reason = ?, updated_at = ?
                WHERE verification_id = ?
                """,
                (report_status.upper(), status_reason, now, verification_id),
            )
            conn.commit()
            return self.get_verification_run(verification_id)
        finally:
            conn.close()

    def list_verification_runs(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Lists verification runs ordered by created_at DESC, optionally filtered by user_id."""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM verification_runs"
            params: List[Any] = []
            if user_id:
                query += " WHERE user_id = ?"
                params.append(user_id)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur = conn.execute(query, tuple(params))
            rows = [dict(row) for row in cur.fetchall()]
            for r in rows:
                r["rule_engine_flagged"] = bool(r.get("rule_engine_flagged"))
                if "sha256_report_hash" in r and "sha256_hash" not in r:
                    r["sha256_hash"] = r["sha256_report_hash"]
                if "created_at" in r and "timestamp" not in r:
                    r["timestamp"] = r["created_at"]

                vid = r["verification_id"]
                f_cur = conn.execute("SELECT * FROM verification_findings WHERE verification_id = ?", (vid,))
                findings = [dict(f) for f in f_cur.fetchall()]
                r["findings"] = findings
                r["rules_triggered"] = [
                    {
                        "rule_code": f.get("finding_code"),
                        "category": f.get("category"),
                        "severity": f.get("severity"),
                        "explanation": f.get("explanation"),
                        "statutory_reference": f.get("statutory_reference"),
                    }
                    for f in findings
                ]
            return rows
        finally:
            conn.close()
