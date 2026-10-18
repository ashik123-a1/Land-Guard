"""Complaint Domain Service
Handles citizen dispute filing, status transitions, expedited review requests and decisions.
"""

import datetime
import uuid
import threading
from typing import Dict, Any, List, Optional, Callable
from src.landguard_data.database import LandGuardDatabase


class ComplaintService:
    """Domain service managing citizen complaints and dispute workflows."""

    def __init__(
        self,
        db: Optional[LandGuardDatabase] = None,
        complaints_cache: Optional[Dict[str, Dict[str, Any]]] = None,
        cases_cache: Optional[Dict[str, Dict[str, Any]]] = None,
        id_lock: Optional[threading.Lock] = None,
        get_user_profile_fn: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        create_case_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        update_case_fn: Optional[Callable[[str, Dict[str, Any]], Optional[Dict[str, Any]]]] = None,
        create_notification_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    ):
        self.db = db or LandGuardDatabase()
        self.complaints = complaints_cache if complaints_cache is not None else {}
        self.cases = cases_cache if cases_cache is not None else {}
        self._id_lock = id_lock or threading.Lock()
        self._get_user_profile = get_user_profile_fn
        self._create_case = create_case_fn
        self._update_case = update_case_fn
        self._create_notification = create_notification_fn

    def create_complaint(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new citizen complaint and automatically logs case for investigation with SQLite persistence."""
        user = self._get_user_profile(user_id) if self._get_user_profile else {}
        if not user:
            db_user = self.db.get_user_by_id(user_id)
            user = db_user or {}

        with self._id_lock:
            comp_num = len(self.complaints) + 1
            yr = datetime.datetime.now().strftime("%Y")
            comp_id = f"CMP-{yr}-{comp_num:03d}"
            while comp_id in self.complaints or (self.db and self.db.get_complaint(comp_id)):
                comp_num += 1
                comp_id = f"CMP-{yr}-{comp_num:03d}"
            self.complaints[comp_id] = {"complaint_id": comp_id}

        now = datetime.datetime.now().isoformat()
        is_expedited = bool(data.get("is_expedited", False))
        exp_reason = data.get("expedite_reason") if is_expedited else None
        exp_status = "PENDING_DECISION" if is_expedited else "NONE"

        new_comp = {
            "complaint_id": comp_id,
            "citizen_user_id": user_id,
            "citizen_name": user.get("full_name", "Citizen"),
            "title": data.get("title", f"Complaint regarding Plot #{data.get('dag_plot_number', 'N/A')}"),
            "category": data.get("category", "SUSPECTED_DOUBLE_SALE"),
            "dag_plot_number": str(data.get("dag_plot_number", "N/A")),
            "deed_number": data.get("deed_number", "N/A"),
            "narrative_description": data.get("narrative_description", ""),
            "status": "SUBMITTED",
            "is_expedited": is_expedited,
            "expedite_reason": exp_reason,
            "expedite_status": exp_status,
            "assigned_officer": "Unassigned",
            "linked_case_id": None,
            "created_at": now,
            "updated_at": now,
            "timeline": [
                {
                    "timestamp": now,
                    "title": "Complaint Submitted",
                    "description": "Complaint successfully entered into LandGuard registry queue.",
                    "actor": f"{user.get('full_name', 'Citizen')} ({user.get('role', 'CITIZEN')})",
                }
            ],
        }

        self.complaints[comp_id] = new_comp

        # Persist to SQLite first so foreign key constraints on cases succeed
        try:
            self.db.create_complaint(new_comp)
        except Exception as e:
            print(f"[ComplaintService] Warning: Failed to persist complaint to SQLite: {e}")

        # Automatically spawn corresponding investigation case
        case_data = {
            "title": f"Investigation: {new_comp['title']}",
            "deed_number": new_comp["deed_number"],
            "dag_plot_number": new_comp["dag_plot_number"],
            "priority": "CRITICAL" if is_expedited else "HIGH",
            "assigned_officer": "Unassigned",
            "statutory_finding": "REVIEW_REQUIRED",
            "evidence_summary": f"Citizen complaint filed ({new_comp['category']}): {new_comp['narrative_description'][:150]}...",
            "initial_note": f"Complaint {comp_id} received from {user.get('full_name')}.",
            "complaint_id": comp_id,
        }
        if self._create_case:
            spawned_case = self._create_case(case_data)
            new_comp["linked_case_id"] = spawned_case.get("case_id")
            try:
                self.db.update_complaint(comp_id, {"linked_case_id": new_comp["linked_case_id"]})
            except Exception:
                pass

        # Log audit event
        self.db.log_audit_event(
            actor_id=user_id,
            action_type="CREATE_COMPLAINT",
            target_entity="COMPLAINT",
            target_id=comp_id,
            details={"category": new_comp["category"], "dag": new_comp["dag_plot_number"]},
        )

        # Notify Admins and Citizen
        if self._create_notification:
            self._create_notification(
                recipient_user_id=user_id,
                title=f"Complaint Received: {comp_id}",
                message=f"Your complaint concerning Plot #{new_comp['dag_plot_number']} has been assigned tracking ID {comp_id}.",
                link_url=f"/user/complaints/{comp_id}",
                notif_type="SUCCESS",
            )

        return new_comp

    def list_complaints(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists citizen complaints with optional user, category, and status filtering from SQLite and cache."""
        try:
            db_comps = self.db.list_complaints(citizen_user_id=user_id, status=status, category=category)
            if db_comps is not None and len(db_comps) > 0:
                for c in db_comps:
                    self.complaints[c["complaint_id"]] = c
                return db_comps
            elif db_comps == []:
                return []
        except Exception as e:
            print(f"[ComplaintService] Warning: SQLite list_complaints fallback: {e}")

        results = list(self.complaints.values())
        if user_id:
            results = [c for c in results if c.get("citizen_user_id") == user_id]
        if status and status.upper() != "ALL":
            results = [c for c in results if c.get("status") == status.upper()]
        if category and category.upper() != "ALL":
            results = [c for c in results if c.get("category") == category.upper()]
        return sorted(results, key=lambda c: c.get("updated_at", ""), reverse=True)

    def get_complaint(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        """Returns single complaint details from memory or SQLite."""
        try:
            db_c = self.db.get_complaint(complaint_id)
            if db_c:
                self.complaints[complaint_id] = db_c
                return db_c
        except Exception as e:
            print(f"[ComplaintService] Warning: SQLite get_complaint error: {e}")

        return self.complaints.get(complaint_id)

    def request_expedited_review(self, complaint_id: str, user_id: str, reason: str, reason_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Citizen requests expedited review on existing complaint with duplicate request prevention and SQLite persistence."""
        comp = self.get_complaint(complaint_id)
        if not comp:
            return None

        # Duplicate pending request prevention (SRS v5 Section 6)
        if comp.get("expedite_status") == "PENDING_DECISION":
            raise ValueError("An expedited review request is already pending administrative decision for this complaint.")

        now = datetime.datetime.now().isoformat()
        full_reason = f"[{reason_category}] {reason}" if reason_category else reason

        comp["is_expedited"] = True
        comp["expedite_reason"] = full_reason
        comp["expedite_category"] = reason_category or "OTHER_JUSTIFIED_URGENCY"
        comp["expedite_status"] = "PENDING_DECISION"
        comp["updated_at"] = now

        if "timeline" not in comp or not isinstance(comp["timeline"], list):
            comp["timeline"] = []
        comp["timeline"].append({
            "timestamp": now,
            "title": "Expedited Review Requested",
            "description": f"Urgency Reason: {full_reason}",
            "actor": "Citizen",
        })

        try:
            self.db.update_complaint(complaint_id, {
                "is_expedited": True,
                "expedite_reason": full_reason,
                "expedite_status": "PENDING_DECISION",
            })
        except Exception as e:
            print(f"[ComplaintService] Warning: Failed to update expedite in SQLite: {e}")

        self.db.log_audit_event(
            actor_id=user_id,
            action_type="REQUEST_EXPEDITE",
            target_entity="COMPLAINT",
            target_id=complaint_id,
            details={"reason": full_reason, "category": comp["expedite_category"]},
        )
        return comp

    def decide_expedite(
        self,
        complaint_id: str,
        decision: str,
        reason: str,
        officer: str = "Admin",
    ) -> Optional[Dict[str, Any]]:
        """Admin decides expedite request (APPROVED, REJECTED, or REQUEST_INFO) with priority escalation and SQLite persistence."""
        comp = self.get_complaint(complaint_id)
        if not comp:
            return None
        now = datetime.datetime.now().isoformat()
        decision_upper = decision.upper()

        if decision_upper == "APPROVED":
            status_value = "APPROVED"
            new_priority = "CRITICAL"
        elif decision_upper in ["REQUEST_INFO", "AWAITING_INFORMATION", "REQUEST_INFORMATION"]:
            status_value = "AWAITING_INFORMATION"
            new_priority = comp.get("priority", "HIGH")
        else:
            status_value = "REJECTED"
            new_priority = comp.get("priority", "NORMAL")

        comp["expedite_status"] = status_value
        comp["updated_at"] = now

        # Preserve priority history
        if "priority_history" not in comp or not isinstance(comp["priority_history"], list):
            comp["priority_history"] = []

        if decision_upper == "APPROVED":
            comp["priority"] = new_priority
            comp["priority_history"].append({
                "priority": new_priority,
                "decided_by": officer,
                "timestamp": now,
                "reason": reason,
                "event": "EXPEDITE_APPROVED",
            })

            linked_cid = comp.get("linked_case_id")
            if linked_cid and linked_cid in self.cases:
                self.cases[linked_cid]["priority"] = "CRITICAL"
                self.cases[linked_cid].setdefault("priority_history", []).append({
                    "priority": "CRITICAL",
                    "decided_by": officer,
                    "timestamp": now,
                    "reason": reason,
                })
                if self._update_case:
                    self._update_case(linked_cid, {"priority": "CRITICAL"})

        if "timeline" not in comp or not isinstance(comp["timeline"], list):
            comp["timeline"] = []
        comp["timeline"].append({
            "timestamp": now,
            "title": f"Expedited Review Decision: {status_value}",
            "description": f"Official Rationale: {reason}",
            "actor": officer,
        })

        try:
            self.db.update_complaint(complaint_id, {
                "expedite_status": status_value,
            })
        except Exception as e:
            print(f"[ComplaintService] Warning: Failed to persist expedite decision in SQLite: {e}")

        self.db.log_audit_event(
            actor_id=officer,
            action_type="DECIDE_EXPEDITE",
            target_entity="COMPLAINT",
            target_id=complaint_id,
            details={"decision": status_value, "reason": reason},
        )

        if self._create_notification:
            notif_type = "SUCCESS" if status_value == "APPROVED" else ("WARNING" if status_value == "AWAITING_INFORMATION" else "INFO")
            self._create_notification(
                recipient_user_id=comp["citizen_user_id"],
                title=f"Expedite Decision: {status_value}",
                message=f"Your expedited review request for {complaint_id} was updated to {status_value}. Notes: {reason}",
                link_url=f"/user/complaints/{complaint_id}",
                notif_type=notif_type,
            )

        return comp

    def analyze_complaint_ai(
        self,
        complaint_id: str,
        viewer_user_id: Optional[str] = None,
        is_staff: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Performs AI claim extraction, category suggestion, duplicate detection, and registry evidence matching."""
        comp = self.get_complaint(complaint_id)
        if not comp:
            return None

        from src.landguard_ai.complaint_analyzer import analyze_complaint

        # Fetch parcel record from database
        parcel = None
        dag_plot = str(comp.get("dag_plot_number", "")).strip()
        if dag_plot and dag_plot != "N/A":
            try:
                parcel = self.db.get_parcel(dag_plot)
            except Exception:
                parcel = None

        all_complaints = self.list_complaints()

        # Fetch any statutory verification findings on this plot if available
        findings = []
        try:
            recent_runs = self.db.list_verification_runs(limit=20)
            for r in recent_runs:
                if str(r.get("dag_plot_number")) == dag_plot:
                    findings.extend(r.get("statutory_findings", []))
        except Exception:
            findings = []

        analysis = analyze_complaint(
            complaint=comp,
            parcel_record=parcel,
            all_complaints=all_complaints,
            verification_findings=findings,
            viewer_user_id=viewer_user_id,
            is_staff=is_staff,
        )
        return analysis
