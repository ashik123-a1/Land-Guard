"""Case Repository
Handles persistence and querying for investigation cases and case notes.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class CaseRepository(BaseRepository):
    """Data access repository for investigation cases and notes."""

    def create_case(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an investigation case docket in SQLite."""
        conn = self._get_connection()
        try:
            now = datetime.datetime.now().isoformat()
            cid = case_dict.get("case_id") or f"CASE-2026-{uuid.uuid4().hex[:5].upper()}"
            conn.execute(
                """
                INSERT INTO cases (
                    case_id, complaint_id, verification_id, title, dag_plot_number,
                    deed_number, priority, status, assigned_officer_id,
                    statutory_finding, ml_risk_score, evidence_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    case_dict.get("complaint_id"),
                    case_dict.get("verification_id"),
                    case_dict.get("title", ""),
                    str(case_dict.get("dag_plot_number", "")),
                    str(case_dict.get("deed_number", "")),
                    case_dict.get("priority", "HIGH"),
                    case_dict.get("status", "OPEN"),
                    case_dict.get("assigned_officer_id") or "USR-ADMIN-001",
                    case_dict.get("statutory_finding", "REVIEW_REQUIRED"),
                    float(case_dict.get("ml_risk_score") or 0.50),
                    case_dict.get("evidence_summary", ""),
                    case_dict.get("created_at") or now,
                    case_dict.get("updated_at") or now,
                ),
            )
            conn.commit()
            return self.get_case(cid)
        finally:
            conn.close()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves case details and all associated officer notes."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT c.*, u.full_name as assigned_officer_name
                FROM cases c
                LEFT JOIN users u ON c.assigned_officer_id = u.user_id
                WHERE c.case_id = ?
                """,
                (case_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["assigned_officer"] = res.get("assigned_officer") or res.get("assigned_officer_name") or "Unassigned"
            res["officer_notes"] = self.get_case_notes(case_id)
            return res
        finally:
            conn.close()

    def get_case_for_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Finds active case escalated from a specific verification run."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT case_id FROM cases WHERE verification_id = ?", (verification_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self.get_case(row["case_id"])
        finally:
            conn.close()

    def list_cases(self, status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists investigation cases with optional filtering."""
        conn = self._get_connection()
        try:
            query = """
                SELECT c.*, u.full_name as assigned_officer_name
                FROM cases c
                LEFT JOIN users u ON c.assigned_officer_id = u.user_id
                WHERE 1=1
            """
            params = []
            if status and status.upper() != "ALL":
                query += " AND c.status = ?"
                params.append(status.upper())
            if priority and priority.upper() != "ALL":
                query += " AND c.priority = ?"
                params.append(priority.upper())

            query += " ORDER BY c.updated_at DESC"
            cur = conn.execute(query, tuple(params))
            out = []
            for r in cur.fetchall():
                c_dict = dict(r)
                c_dict["assigned_officer"] = c_dict.get("assigned_officer") or c_dict.get("assigned_officer_name") or "Unassigned"
                c_dict["officer_notes"] = self.get_case_notes(c_dict["case_id"])
                out.append(c_dict)
            return out
        finally:
            conn.close()

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates case status, priority, or assignment."""
        conn = self._get_connection()
        try:
            fields = []
            values = []
            now = datetime.datetime.now().isoformat()
            updates["updated_at"] = now
            allowed = ["status", "priority", "assigned_officer_id", "statutory_finding", "evidence_summary", "title", "updated_at"]
            for k, v in updates.items():
                if k in allowed:
                    fields.append(f"{k} = ?")
                    values.append(v)

            if not fields:
                return self.get_case(case_id)

            values.append(case_id)
            sql = f"UPDATE cases SET {', '.join(fields)} WHERE case_id = ?"
            conn.execute(sql, tuple(values))
            conn.commit()
            return self.get_case(case_id)
        finally:
            conn.close()

    def add_case_note(self, case_id: str, author_id: str, note_text: str) -> Dict[str, Any]:
        """Appends a timestamped officer note to an investigation case."""
        conn = self._get_connection()
        try:
            nid = f"NOTE-{uuid.uuid4().hex[:6].upper()}"
            now = datetime.datetime.now().isoformat()
            resolved_author = author_id if str(author_id).startswith("USR-") else "USR-ADMIN-001"
            conn.execute(
                """
                INSERT INTO case_notes (note_id, case_id, author_id, note_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nid, case_id, resolved_author, note_text.strip(), now),
            )
            conn.execute("UPDATE cases SET updated_at = ? WHERE case_id = ?", (now, case_id))
            conn.commit()
            return {"note_id": nid, "case_id": case_id, "author": author_id, "note": note_text, "timestamp": now}
        finally:
            conn.close()

    def get_case_notes(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieves all notes for a case."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT cn.note_id, cn.note_text as note, cn.created_at as timestamp,
                       COALESCE(u.full_name, cn.author_id) as author
                FROM case_notes cn
                LEFT JOIN users u ON cn.author_id = u.user_id
                WHERE cn.case_id = ?
                ORDER BY cn.created_at ASC
                """,
                (case_id,),
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
