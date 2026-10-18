"""Case Domain Service
Handles investigation case management, officer docket notes, SLA calculations, and clarification workflows.
"""

import datetime
import uuid
import threading
from typing import Dict, Any, List, Optional, Callable
from src.landguard_data.database import LandGuardDatabase


class CaseService:
    """Domain service managing title fraud investigation cases and dockets."""

    def __init__(
        self,
        db: Optional[LandGuardDatabase] = None,
        cases_cache: Optional[Dict[str, Dict[str, Any]]] = None,
        id_lock: Optional[threading.Lock] = None,
        create_notification_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    ):
        self.db = db or LandGuardDatabase()
        self.cases = cases_cache if cases_cache is not None else {}
        self._id_lock = id_lock or threading.Lock()
        self._create_notification = create_notification_fn

    def get_case_for_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Checks if an investigation case has already been opened for this verification ID."""
        if not verification_id:
            return None
        for c in self.cases.values():
            if c.get("verification_id") == verification_id:
                return c
        db_case = self.db.get_case_for_verification(verification_id)
        if db_case:
            self.cases[db_case["case_id"]] = db_case
            return db_case
        return None

    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an investigator review case with duplicate prevention."""
        verif_id = case_data.get("verification_id")
        if verif_id:
            existing = self.get_case_for_verification(verif_id)
            if existing:
                return existing

        with self._id_lock:
            case_num = len(self.cases) + 1
            yr = datetime.datetime.now().strftime("%Y")
            case_id = f"CASE-{yr}-{case_num:03d}"
            while case_id in self.cases or (self.db and self.db.get_case(case_id)):
                case_num += 1
                case_id = f"CASE-{yr}-{case_num:03d}"
            self.cases[case_id] = {"case_id": case_id}

        now_iso = datetime.datetime.now().isoformat()
        new_case = {
            "case_id": case_id,
            "created_at": now_iso,
            "updated_at": now_iso,
            "title": case_data.get("title", f"Investigation: Plot #{case_data.get('dag_plot_number', 'N/A')}"),
            "deed_number": case_data.get("deed_number", "N/A"),
            "dag_plot_number": str(case_data.get("dag_plot_number", "N/A")),
            "verification_id": case_data.get("verification_id"),
            "complaint_id": case_data.get("complaint_id"),
            "status": case_data.get("status", "OPEN"),
            "priority": case_data.get("priority", "HIGH"),
            "assigned_officer": case_data.get("assigned_officer", "Unassigned"),
            "statutory_finding": case_data.get("statutory_finding", "REVIEW_REQUIRED"),
            "ml_risk_score": case_data.get("ml_risk_score"),
            "evidence_summary": case_data.get("evidence_summary", ""),
            "officer_notes": [
                {
                    "timestamp": now_iso,
                    "author": case_data.get("assigned_officer", "System"),
                    "note": case_data.get("initial_note", "Case initialized from LandGuard verification finding."),
                }
            ],
        }
        self.cases[case_id] = new_case

        try:
            db_case = {
                "case_id": case_id,
                "complaint_id": case_data.get("complaint_id"),
                "verification_id": case_data.get("verification_id"),
                "title": new_case["title"],
                "dag_plot_number": new_case["dag_plot_number"],
                "deed_number": new_case["deed_number"],
                "priority": new_case["priority"],
                "status": new_case["status"],
                "assigned_officer_id": "USR-ADMIN-001",
                "statutory_finding": new_case["statutory_finding"],
                "ml_risk_score": new_case.get("ml_risk_score") or 0.5,
                "evidence_summary": new_case["evidence_summary"],
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            self.db.create_case(db_case)
            self.db.add_case_note(
                case_id=case_id,
                author_id="USR-ADMIN-001",
                note_text=case_data.get("initial_note", "Case initialized from LandGuard verification finding."),
            )
        except Exception as e:
            print(f"[CaseService] Warning: Failed to persist case to SQLite: {e}")

        return new_case

    def compute_case_sla(self, case_or_id: Any) -> Dict[str, Any]:
        """Calculates SLA deadline and overdue status for an investigation case."""
        if isinstance(case_or_id, str):
            c_data = self.get_case(case_or_id) or {}
            c = dict(c_data)
        elif isinstance(case_or_id, dict):
            c = dict(case_or_id)
        else:
            c = {}

        priority = str(c.get("priority", "HIGH")).upper()
        sla_hours = 24 if priority == "CRITICAL" else (48 if priority == "HIGH" else 120)
        c["sla_target_hours"] = sla_hours

        created_str = c.get("created_at")
        try:
            created_dt = datetime.datetime.fromisoformat(created_str) if created_str else datetime.datetime.now()
        except Exception:
            created_dt = datetime.datetime.now()

        deadline_dt = created_dt + datetime.timedelta(hours=sla_hours)
        c["sla_deadline"] = deadline_dt.isoformat()

        if str(c.get("status", "")).upper() in ["RESOLVED", "CLOSED"]:
            c["is_overdue"] = False
            c["hours_remaining"] = 0.0
            c["hours_overdue"] = 0.0
            c["sla_state"] = "RESOLVED"
        else:
            now_dt = datetime.datetime.now()
            hours_diff = (deadline_dt - now_dt).total_seconds() / 3600.0
            if hours_diff < 0:
                c["is_overdue"] = True
                c["hours_remaining"] = 0.0
                c["hours_overdue"] = round(-hours_diff, 1)
                c["sla_state"] = "OVERDUE"
            elif hours_diff <= 12:
                c["is_overdue"] = False
                c["hours_remaining"] = round(hours_diff, 1)
                c["hours_overdue"] = 0.0
                c["sla_state"] = "APPROACHING_DEADLINE"
            else:
                c["is_overdue"] = False
                c["hours_remaining"] = round(hours_diff, 1)
                c["hours_overdue"] = 0.0
                c["sla_state"] = "ON_TRACK"
        return c

    def get_overdue_cases(self) -> List[Dict[str, Any]]:
        """Returns all unclosed investigation cases exceeding SLA resolution deadlines."""
        all_cases = self.list_cases()
        return [c for c in all_cases if c.get("is_overdue")]

    def request_case_clarification(
        self,
        case_id: str,
        question: str,
        officer_id: str = "USR-ADMIN-001",
        officer_name: str = "Senior Registrar M. Rahman",
    ) -> Optional[Dict[str, Any]]:
        """Requests citizen clarification on an active investigation case, transitioning status to AWAITING_INFORMATION."""
        c = self.get_case(case_id)
        if not c:
            return None

        clean_q = question.strip()
        now_ts = datetime.datetime.now().isoformat()

        if case_id in self.cases:
            self.cases[case_id]["status"] = "AWAITING_INFORMATION"
            self.cases[case_id]["updated_at"] = now_ts

        self.add_case_note(
            case_id=case_id,
            note_text=f"[CLARIFICATION REQUESTED] {clean_q}",
            author=officer_name,
        )

        try:
            self.db.update_case(case_id, {"status": "AWAITING_INFORMATION"})
        except Exception as e:
            print(f"[CaseService] Warning: Failed to update case status in SQLite: {e}")

        complaint_id = c.get("complaint_id")
        link_target = f"/user/complaints/{complaint_id}" if complaint_id else "/user/dashboard"
        if self._create_notification:
            self._create_notification(
                recipient_user_id="USR-CITIZEN-001",
                title="Clarification Requested on Investigation",
                message=f"Investigating Officer {officer_name} requested information: {clean_q[:90]}",
                link_url=link_target,
            )

        try:
            self.db.log_audit_event(
                actor_id=officer_id,
                action_type="CASE_CLARIFICATION_REQUESTED",
                target_entity="CASE",
                target_id=case_id,
                details={
                    "case_id": case_id,
                    "question": clean_q,
                    "officer_name": officer_name,
                },
            )
        except Exception as e:
            print(f"[CaseService] Warning: Failed to log audit event: {e}")

        return self.get_case(case_id)

    def respond_case_clarification(
        self,
        case_id: str,
        response_text: str,
        user_id: str = "USR-CITIZEN-001",
        user_name: str = "Rafiqul Islam",
        user_role: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Submits citizen response to a clarification request, transitioning case back to UNDER_REVIEW."""
        c = self.get_case(case_id)
        if not c:
            return None

        # Domain service ownership enforcement
        if user_role == "CITIZEN":
            is_authorized = False
            comp_id = c.get("complaint_id")
            if comp_id and self.db:
                comp = self.db.get_complaint(comp_id)
                if comp and comp.get("citizen_user_id") == user_id:
                    is_authorized = True
            verif_id = c.get("verification_id")
            if not is_authorized and verif_id and self.db:
                verif = self.db.get_verification_run(verif_id)
                if verif and verif.get("user_id") == user_id:
                    is_authorized = True
            if not is_authorized and c.get("citizen_user_id") == user_id:
                is_authorized = True

            if not is_authorized:
                raise PermissionError(f"User '{user_id}' is not authorized to respond to Case '{case_id}'.")

        clean_resp = response_text.strip()
        now_ts = datetime.datetime.now().isoformat()

        if case_id in self.cases:
            self.cases[case_id]["status"] = "UNDER_REVIEW"
            self.cases[case_id]["updated_at"] = now_ts

        self.add_case_note(
            case_id=case_id,
            note_text=f"[CITIZEN CLARIFICATION RESPONSE] {clean_resp}",
            author=f"{user_name} (Citizen)",
        )

        try:
            self.db.update_case(case_id, {"status": "UNDER_REVIEW"})
        except Exception as e:
            print(f"[CaseService] Warning: Failed to update case status in SQLite: {e}")

        assigned_officer = c.get("assigned_officer_id") or "USR-ADMIN-001"
        if self._create_notification:
            self._create_notification(
                recipient_user_id=assigned_officer,
                title="Citizen Clarification Received",
                message=f"Citizen response received for Case {case_id}: {clean_resp[:90]}",
                link_url=f"/admin/cases/{case_id}",
            )

        try:
            self.db.log_audit_event(
                actor_id=user_id,
                action_type="CASE_CLARIFICATION_RESPONDED",
                target_entity="CASE",
                target_id=case_id,
                details={
                    "case_id": case_id,
                    "response": clean_resp,
                    "citizen_name": user_name,
                },
            )
        except Exception as e:
            print(f"[CaseService] Warning: Failed to log audit event: {e}")

        return self.get_case(case_id)

    def list_cases(self, status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists investigator review cases with optional filtering and SLA calculations."""
        try:
            db_cases = self.db.list_cases(status=status, priority=priority)
            if db_cases is not None:
                db_ids = {c["case_id"] for c in db_cases}
                mem_cases = [c for c in self.cases.values() if c.get("case_id") not in db_ids]
                all_raw = list(db_cases) + mem_cases
                if all_raw:
                    results = []
                    for c in all_raw:
                        self.cases[c["case_id"]] = c
                        results.append(self.compute_case_sla(c))
                    if status and status.upper() != "ALL":
                        results = [c for c in results if c.get("status") == status.upper()]
                    if priority and priority.upper() != "ALL":
                        results = [c for c in results if c.get("priority") == priority.upper()]
                    return sorted(results, key=lambda c: c.get("updated_at", ""), reverse=True)
                return []
        except Exception as e:
            print(f"[CaseService] Warning: SQLite list_cases fallback: {e}")

        results = [self.compute_case_sla(c) for c in self.cases.values()]
        if status and status.upper() != "ALL":
            results = [c for c in results if c.get("status") == status.upper()]
        if priority and priority.upper() != "ALL":
            results = [c for c in results if c.get("priority") == priority.upper()]
        return sorted(results, key=lambda c: c.get("updated_at", ""), reverse=True)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single case by case ID with SLA calculations."""
        try:
            db_case = self.db.get_case(case_id)
            if db_case:
                cached = self.cases.get(case_id) or {}
                if cached.get("officer_notes") and not db_case.get("officer_notes"):
                    db_case["officer_notes"] = cached["officer_notes"]
                self.cases[case_id] = db_case
                return self.compute_case_sla(db_case)
        except Exception as e:
            print(f"[CaseService] Warning: SQLite get_case fallback: {e}")

        c = self.cases.get(case_id)
        return self.compute_case_sla(c) if c else None

    def process_sla_escalations(self) -> List[Dict[str, Any]]:
        """Processes all unclosed cases and produces real, idempotent SLA overdue events and notifications."""
        escalated_events = []
        all_cases = self.list_cases()
        now_ts = datetime.datetime.now().isoformat()

        for c in all_cases:
            if c.get("status") in ["RESOLVED", "CLOSED"]:
                continue
            if c.get("is_overdue") and not c.get("overdue_escalated"):
                case_id = c.get("case_id")
                c["overdue_escalated"] = True
                c["overdue_escalated_at"] = now_ts
                if case_id in self.cases:
                    self.cases[case_id]["overdue_escalated"] = True
                    self.cases[case_id]["overdue_escalated_at"] = now_ts

                escalation_note = (
                    f"[SLA OVERDUE ESCALATION] Investigation resolution deadline exceeded by "
                    f"{c.get('hours_overdue', 0)} hours (target SLA: {c.get('sla_target_hours', 48)}h). "
                    f"Supervisory escalation triggered for priority {c.get('priority')}."
                )
                self.add_case_note(case_id=case_id, note_text=escalation_note, author="SLA-Monitor")

                if self._create_notification:
                    self._create_notification(
                        recipient_user_id="USR-ADMIN-001",
                        title=f"SLA Overdue: Case {case_id}",
                        message=f"Case {case_id} on Plot #{c.get('dag_plot_number', 'N/A')} is overdue by {c.get('hours_overdue')}h.",
                        link_url=f"/admin/cases/{case_id}",
                        notif_type="WARNING",
                    )

                try:
                    self.db.log_audit_event(
                        actor_id="SYSTEM-SLA-MONITOR",
                        action_type="CASE_SLA_OVERDUE_ESCALATION",
                        target_entity="CASE",
                        target_id=case_id,
                        details={
                            "case_id": case_id,
                            "priority": c.get("priority"),
                            "hours_overdue": c.get("hours_overdue"),
                            "sla_target_hours": c.get("sla_target_hours"),
                        },
                    )
                except Exception as e:
                    print(f"[CaseService] Warning: Failed to log SLA escalation audit event: {e}")

                escalated_events.append({
                    "case_id": case_id,
                    "priority": c.get("priority"),
                    "hours_overdue": c.get("hours_overdue"),
                    "escalated_at": now_ts,
                })

        return escalated_events

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates case status, priority, or assigned officer with audit tracking and complaint synchronization."""
        c = self.cases.get(case_id)
        if not c:
            try:
                db_c = self.db.get_case(case_id)
                if db_c:
                    self.cases[case_id] = db_c
                    c = db_c
            except Exception:
                pass
        if not c:
            return None
        now_ts = datetime.datetime.now().isoformat()

        # Track assignment history if assigned_officer changed
        old_officer = c.get("assigned_officer", "Unassigned")
        new_officer = updates.get("assigned_officer")
        if new_officer and new_officer != old_officer:
            if "assignment_history" not in c or not isinstance(c["assignment_history"], list):
                c["assignment_history"] = []
            assigned_by = updates.get("assigned_by", "Senior Registrar")
            c["assignment_history"].append({
                "timestamp": now_ts,
                "previous_officer": old_officer,
                "new_officer": new_officer,
                "assigned_by": assigned_by,
            })
            self.add_case_note(
                case_id=case_id,
                note_text=f"[OFFICER REASSIGNED] Assigned officer changed from '{old_officer}' to '{new_officer}'.",
                author=assigned_by,
            )

        # Track priority changes
        old_priority = c.get("priority", "NORMAL")
        new_priority = updates.get("priority")
        if new_priority and new_priority != old_priority:
            if "priority_history" not in c or not isinstance(c["priority_history"], list):
                c["priority_history"] = []
            escalated_by = updates.get("escalated_by", "Authorized Officer")
            reason = updates.get("priority_reason", "Administrative Priority Determination")
            c["priority_history"].append({
                "timestamp": now_ts,
                "previous_priority": old_priority,
                "new_priority": new_priority,
                "reason": reason,
                "officer": escalated_by,
            })
            self.add_case_note(
                case_id=case_id,
                note_text=f"[PRIORITY CHANGED] Priority updated from {old_priority} to {new_priority}. Reason: {reason}",
                author=escalated_by,
            )

        old_status = c.get("status", "OPEN")
        new_status = updates.get("status")

        valid_keys = ["status", "priority", "assigned_officer", "assigned_officer_id", "evidence_summary", "title", "statutory_finding"]
        for k in valid_keys:
            if k in updates and updates[k] is not None:
                c[k] = updates[k]
        c["updated_at"] = now_ts

        try:
            self.db.update_case(case_id, updates)
        except Exception as e:
            print(f"[CaseService] Warning: Failed to update case in SQLite: {e}")

        # Synchronize linked complaint & notify citizen
        comp_id = c.get("complaint_id")
        if comp_id:
            try:
                comp = self.db.get_complaint(comp_id)
                if comp:
                    comp_updates = {}
                    timeline = comp.get("timeline") or []
                    if new_status and new_status != old_status:
                        comp_updates["status"] = new_status
                        actor = updates.get("assigned_by") or updates.get("escalated_by") or "Senior Registrar"
                        timeline.append({
                            "timestamp": now_ts,
                            "title": f"Status Updated: {new_status}",
                            "description": f"Investigation case status transitioned to {new_status}.",
                            "actor": actor,
                        })
                        import json
                        comp_updates["timeline_json"] = json.dumps(timeline)
                        self.db.update_complaint(comp_id, comp_updates)

                        if self._create_notification and comp.get("citizen_user_id"):
                            self._create_notification(
                                recipient_user_id=comp["citizen_user_id"],
                                title=f"Case Status Update: {case_id}",
                                message=f"Investigation status for your complaint #{comp_id} has been updated to {new_status}.",
                                link_url=f"/user/complaints/{comp_id}",
                                notif_type="SUCCESS" if new_status in ["RESOLVED", "CLOSED"] else "INFO",
                            )
            except Exception as e:
                print(f"[CaseService] Warning: Failed to sync case update to complaint {comp_id}: {e}")

        return c

    def add_case_note(self, case_id: str, note_text: str, author: str = "Officer") -> Optional[Dict[str, Any]]:
        """Appends an audit note to an investigation case and syncs timeline to citizen complaint."""
        c = self.cases.get(case_id)
        if not c:
            try:
                db_c = self.db.get_case(case_id)
                if db_c:
                    self.cases[case_id] = db_c
                    c = db_c
            except Exception:
                pass
        if not c:
            return None
        now_ts = datetime.datetime.now().isoformat()
        if "officer_notes" not in c or not isinstance(c["officer_notes"], list):
            c["officer_notes"] = []
        c["officer_notes"].append({
            "timestamp": now_ts,
            "author": author,
            "note": note_text,
        })
        c["updated_at"] = now_ts

        try:
            db_author_id = author if str(author).startswith("USR-") else "USR-ADMIN-001"
            self.db.add_case_note(case_id=case_id, author_id=db_author_id, note_text=note_text)
        except Exception as e:
            print(f"[CaseService] Warning: Failed to persist case note to SQLite: {e}")

        # Sync note into citizen complaint timeline and notify citizen if note is from officer
        comp_id = c.get("complaint_id")
        if comp_id and not str(author).endswith("(Citizen)"):
            try:
                comp = self.db.get_complaint(comp_id)
                if comp:
                    timeline = comp.get("timeline") or []
                    timeline.append({
                        "timestamp": now_ts,
                        "title": "Investigator Note Added",
                        "description": f"{author}: {note_text}",
                        "actor": author,
                    })
                    import json
                    self.db.update_complaint(comp_id, {
                        "timeline_json": json.dumps(timeline),
                    })
                    if self._create_notification and comp.get("citizen_user_id"):
                        self._create_notification(
                            recipient_user_id=comp["citizen_user_id"],
                            title=f"New Note on Case: {case_id}",
                            message=f"An investigator added a note to your complaint #{comp_id}: {note_text[:100]}...",
                            link_url=f"/user/complaints/{comp_id}",
                            notif_type="INFO",
                        )
            except Exception as e:
                print(f"[CaseService] Warning: Failed to sync case note to complaint {comp_id}: {e}")

        return c
