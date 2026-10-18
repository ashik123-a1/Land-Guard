"""Complaint Repository
Handles persistence and querying for citizen complaints.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository):
    """Data access repository for citizen complaints."""

    def create_complaint(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new citizen complaint."""
        conn = self._get_connection()
        try:
            import json
            now = datetime.datetime.now().isoformat()
            cid = c.get("complaint_id") or f"CMP-2026-{uuid.uuid4().hex[:5].upper()}"
            timeline = c.get("timeline") or [
                {
                    "timestamp": c.get("created_at") or now,
                    "title": "Complaint Submitted",
                    "description": "Complaint successfully entered into LandGuard registry queue.",
                    "actor": "Citizen (CITIZEN)",
                }
            ]
            timeline_str = json.dumps(timeline)
            try:
                conn.execute(
                    """
                    INSERT INTO complaints (
                        complaint_id, citizen_user_id, category, dag_plot_number, deed_number,
                        title, narrative_description, status, is_expedited, expedite_reason,
                        expedite_status, created_at, updated_at, timeline_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cid,
                        c.get("citizen_user_id"),
                        c.get("category", "SUSPECTED_DOUBLE_SALE"),
                        str(c.get("dag_plot_number", "")),
                        str(c.get("deed_number", "")),
                        c.get("title", ""),
                        c.get("narrative_description", ""),
                        c.get("status", "SUBMITTED"),
                        1 if c.get("is_expedited") else 0,
                        c.get("expedite_reason"),
                        c.get("expedite_status", "NONE"),
                        c.get("created_at") or now,
                        c.get("updated_at") or now,
                        timeline_str,
                    ),
                )
            except Exception:
                conn.execute(
                    """
                    INSERT INTO complaints (
                        complaint_id, citizen_user_id, category, dag_plot_number, deed_number,
                        title, narrative_description, status, is_expedited, expedite_reason,
                        expedite_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cid,
                        c.get("citizen_user_id"),
                        c.get("category", "SUSPECTED_DOUBLE_SALE"),
                        str(c.get("dag_plot_number", "")),
                        str(c.get("deed_number", "")),
                        c.get("title", ""),
                        c.get("narrative_description", ""),
                        c.get("status", "SUBMITTED"),
                        1 if c.get("is_expedited") else 0,
                        c.get("expedite_reason"),
                        c.get("expedite_status", "NONE"),
                        c.get("created_at") or now,
                        c.get("updated_at") or now,
                    ),
                )
            conn.commit()
            return self.get_complaint(cid)
        finally:
            conn.close()

    def get_complaint(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single complaint with citizen details and linked case info."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT c.*, u.full_name as citizen_name, cs.case_id as linked_case_id,
                       cs.assigned_officer_id, cs.priority as case_priority
                FROM complaints c
                LEFT JOIN users u ON c.citizen_user_id = u.user_id
                LEFT JOIN cases cs ON c.complaint_id = cs.complaint_id
                WHERE c.complaint_id = ?
                """,
                (complaint_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["is_expedited"] = bool(res.get("is_expedited"))

            import json
            timeline = []
            if res.get("timeline_json"):
                try:
                    timeline = json.loads(res["timeline_json"])
                except Exception:
                    timeline = []
            if not timeline:
                created_ts = res.get("created_at") or datetime.datetime.now().isoformat()
                timeline = [
                    {
                        "timestamp": created_ts,
                        "title": "Complaint Submitted",
                        "description": "Complaint successfully entered into LandGuard registry queue.",
                        "actor": f"{res.get('citizen_name') or 'Citizen'} (CITIZEN)",
                    }
                ]
                try:
                    ev_cur = conn.execute(
                        "SELECT * FROM audit_events WHERE target_id = ? ORDER BY created_at ASC",
                        (complaint_id,),
                    )
                    for ev in ev_cur.fetchall():
                        ev_dict = dict(ev)
                        act_type = ev_dict.get("action_type", "")
                        if act_type == "EXPEDITE_REVIEW_REQUESTED":
                            timeline.append({
                                "timestamp": ev_dict.get("created_at", created_ts),
                                "title": "Expedited Review Requested",
                                "description": "Priority escalation requested under statutory urgency grounds.",
                                "actor": "Citizen (CITIZEN)",
                            })
                        elif act_type == "EXPEDITE_REVIEW_DECIDED":
                            timeline.append({
                                "timestamp": ev_dict.get("created_at", created_ts),
                                "title": "Expedite Decision Recorded",
                                "description": "Official determination recorded on expedited review request.",
                                "actor": "Senior Registrar (ADMIN)",
                            })
                except Exception:
                    pass
            res["timeline"] = timeline
            return res
        finally:
            conn.close()

    def list_complaints(
        self,
        citizen_user_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists complaints with optional citizen, category, or status filtering."""
        conn = self._get_connection()
        try:
            query = """
                SELECT c.*, u.full_name as citizen_name, cs.case_id as linked_case_id
                FROM complaints c
                LEFT JOIN users u ON c.citizen_user_id = u.user_id
                LEFT JOIN cases cs ON c.complaint_id = cs.complaint_id
                WHERE 1=1
            """
            params = []
            if citizen_user_id:
                query += " AND c.citizen_user_id = ?"
                params.append(citizen_user_id)
            if status and status.upper() != "ALL":
                query += " AND c.status = ?"
                params.append(status.upper())
            if category and category.upper() != "ALL":
                query += " AND c.category = ?"
                params.append(category.upper())

            query += " ORDER BY c.updated_at DESC"
            cur = conn.execute(query, tuple(params))
            out = []
            for r in cur.fetchall():
                row_dict = dict(r)
                row_dict["is_expedited"] = bool(row_dict.get("is_expedited"))
                out.append(row_dict)
            return out
        finally:
            conn.close()

    def update_complaint(self, complaint_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates complaint fields in SQLite."""
        conn = self._get_connection()
        try:
            fields = []
            values = []
            now = datetime.datetime.now().isoformat()
            updates["updated_at"] = now
            for k, v in updates.items():
                if k in ["status", "is_expedited", "expedite_reason", "expedite_status", "updated_at", "title", "narrative_description", "timeline_json"]:
                    fields.append(f"{k} = ?")
                    values.append(1 if v is True else (0 if v is False else v))

            if not fields:
                return self.get_complaint(complaint_id)

            values.append(complaint_id)
            sql = f"UPDATE complaints SET {', '.join(fields)} WHERE complaint_id = ?"
            conn.execute(sql, tuple(values))
            conn.commit()
            return self.get_complaint(complaint_id)
        finally:
            conn.close()

    def get_complaints_by_plot(self, dag_plot_number: str) -> List[Dict[str, Any]]:
        """Retrieves all complaints associated with a specific cadastral plot."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT c.*, u.full_name as citizen_name, cs.case_id as linked_case_id
                FROM complaints c
                LEFT JOIN users u ON c.citizen_user_id = u.user_id
                LEFT JOIN cases cs ON c.complaint_id = cs.complaint_id
                WHERE c.dag_plot_number = ?
                ORDER BY c.created_at DESC
                """,
                (str(dag_plot_number).strip(),),
            )
            out = []
            for r in cur.fetchall():
                row_dict = dict(r)
                row_dict["is_expedited"] = bool(row_dict.get("is_expedited"))
                out.append(row_dict)
            return out
        finally:
            conn.close()
