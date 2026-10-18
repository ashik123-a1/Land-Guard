"""LandGuard Operational Database Adapter
Primary & Active: Local SQLite (data/landguard_operational.db) - ALWAYS unconditional default.
Standby: Neon Serverless PostgreSQL (via DATABASE_URL) - configured for future use,
         active ONLY if explicitly selected via DATABASE_BACKEND=POSTGRESQL.

Acts as a unified facade coordinating specialized repositories:
- UserRepository
- ComplaintRepository
- CaseRepository
- VerificationRepository
- DocumentRepository
- NotificationRepository
- AuditRepository
"""

import os
import sqlite3
import datetime
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from src.landguard_web.security import hash_password, verify_password
except ImportError:
    import hashlib
    import secrets

    def hash_password(password: str, salt: Optional[str] = None) -> str:
        if not salt:
            salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"pbkdf2_sha256$100000${salt}${dk.hex()}"

    def verify_password(plain_password: str, stored_hash: str) -> bool:
        return plain_password == stored_hash

from src.landguard_data.repositories import (
    BaseRepository,
    UserRepository,
    ComplaintRepository,
    CaseRepository,
    VerificationRepository,
    DocumentRepository,
    NotificationRepository,
    AuditRepository,
    ParcelRepository,
)


class LandGuardDatabase(BaseRepository):
    """Operational database manager and facade for LandGuard state, entities, and audit logging."""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path=db_path)

        if self.db_type == "POSTGRESQL":
            print(f"[LandGuard DB] Explicitly activated Neon PostgreSQL backend: {self.get_sanitized_url()}")
        else:
            standby_info = f" (Neon PostgreSQL on standby: {self.get_sanitized_url()})" if self.neon_configured else ""
            print(f"[LandGuard DB] Active primary database: SQLite at {self.db_path}{standby_info}")

        self._init_database()

        # Initialize domain repositories pointing to the same active database
        self.users = UserRepository(db_path=self.db_path)
        self.complaints = ComplaintRepository(db_path=self.db_path)
        self.cases = CaseRepository(db_path=self.db_path)
        self.verifications = VerificationRepository(db_path=self.db_path)
        self.documents = DocumentRepository(db_path=self.db_path)
        self.notifications = NotificationRepository(db_path=self.db_path)
        self.audit = AuditRepository(db_path=self.db_path)
        self.parcels = ParcelRepository(db_path=self.db_path)

    def _init_database(self):
        """Executes migration schema and seeds initial operational entities idempotently."""
        schema_path = os.path.abspath("migrations/001_initial_schema.sql")
        if not os.path.exists(schema_path):
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        conn = self._get_connection()
        try:
            if self.db_type == "POSTGRESQL":
                cur = conn.cursor()
                cur.execute(sql_script)
                conn.commit()
                cur.close()
                print("[LandGuard DB] Initialized PostgreSQL / Neon schema idempotently.")
            else:
                sqlite_script = sql_script.replace("BOOLEAN DEFAULT TRUE", "INTEGER DEFAULT 1")
                sqlite_script = sqlite_script.replace("BOOLEAN DEFAULT FALSE", "INTEGER DEFAULT 0")
                sqlite_script = sqlite_script.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                sqlite_script = sqlite_script.replace("JSON", "TEXT")
                conn.executescript(sqlite_script)
                conn.commit()
                print(f"[LandGuard DB] Verified SQLite operational schema at {self.db_path}")

            # Ensure columns for report lifecycle exist on verification_runs
            for col, col_def in [
                ("report_status", "VARCHAR(50) DEFAULT 'VALID'"),
                ("status_reason", "TEXT"),
                ("updated_at", "DATETIME"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE verification_runs ADD COLUMN {col} {col_def}")
                    conn.commit()
                except Exception:
                    pass

            # Ensure preferred_language exists on users table
            try:
                conn.execute("ALTER TABLE users ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'bn'")
                conn.commit()
            except Exception:
                pass

            # Ensure timeline_json exists on complaints table
            try:
                conn.execute("ALTER TABLE complaints ADD COLUMN timeline_json TEXT")
                conn.commit()
            except Exception:
                pass

            self._seed_initial_data_if_empty(conn)
        except Exception as e:
            print(f"[LandGuard DB] Database initialization notice: {e}")
        finally:
            conn.close()

    def _seed_initial_data_if_empty(self, conn):
        """Seeds initial roles, demo users, sample complaint, and initial case if tables are empty."""
        cur = conn.cursor()
        now = datetime.datetime.now().isoformat()

        # 1. Seed Roles
        cur.execute("SELECT COUNT(*) FROM roles")
        if cur.fetchone()[0] == 0:
            roles = [
                ("CITIZEN", "Citizen", "Registered citizen titleholder or dispute complainant", now),
                ("INVESTIGATOR", "Investigator", "Authorized title fraud investigation officer", now),
                ("ADMIN", "Senior Registrar", "Authorized land registrar and chief determination authority", now),
            ]
            cur.executemany("INSERT INTO roles (role_id, role_name, description, created_at) VALUES (?, ?, ?, ?)", roles)
            conn.commit()

        # 2. Seed Demo Users
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            users = [
                (
                    "USR-CITIZEN-001",
                    "citizen@landguard.gov.bd",
                    hash_password("demo123"),
                    "Nakib Md Ashik",
                    "CITIZEN",
                    "19882691234567890",
                    "CIT-BD-884920",
                    "+880 1712-345678",
                    "Dhaka",
                    "Dhaka",
                    "Savar",
                    1,
                    now,
                    now,
                ),
                (
                    "USR-INVESTIGATOR-001",
                    "investigator@landguard.gov.bd",
                    hash_password("demo123"),
                    "Inspector S. Karim",
                    "INVESTIGATOR",
                    "19822691234567891",
                    "OFF-INV-2041",
                    "+880 1711-223344",
                    "Dhaka",
                    "Dhaka",
                    "Dhaka Sadar",
                    1,
                    now,
                    now,
                ),
                (
                    "USR-ADMIN-001",
                    "admin@landguard.gov.bd",
                    hash_password("admin123"),
                    "Hasin Ishruq Nabil",
                    "ADMIN",
                    "19752691234567892",
                    "ADM-REG-1001",
                    "+880 1819-556677",
                    "Dhaka",
                    "Dhaka",
                    "Secretariat",
                    1,
                    now,
                    now,
                ),
            ]
            cur.executemany(
                """
                INSERT INTO users (
                    user_id, email, password_hash, full_name, role, national_id,
                    digital_identity_id, phone, division, district, upazila,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                users,
            )
            conn.commit()

        # 3. Seed Initial Demo Complaint if empty
        cur.execute("SELECT COUNT(*) FROM complaints")
        if cur.fetchone()[0] == 0:
            demo_complaint = (
                "CMP-2026-001",
                "USR-CITIZEN-001",
                "SUSPECTED_DOUBLE_SALE",
                "6792",
                "DEED-2005-23539",
                "Double Disposition Claim on Dag Plot #6792 (Paba Upazila)",
                "I entered into an agreement to purchase Plot #6792. However, local AC Land records indicate vendor previously executed deed DEED-2000-41374 conveying full holding capacity. Vendor claims deed was cancelled but no court decree is presented.",
                "UNDER_REVIEW",
                1,
                "Vendor demands earnest money deposit within 48 hours or threatens forfeiture.",
                "APPROVED",
                now,
                now,
            )
            cur.execute(
                """
                INSERT INTO complaints (
                    complaint_id, citizen_user_id, category, dag_plot_number, deed_number,
                    title, narrative_description, status, is_expedited, expedite_reason,
                    expedite_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                demo_complaint,
            )
            conn.commit()

        # 4. Seed Initial Demo Case & Case Note if empty
        cur.execute("SELECT COUNT(*) FROM cases")
        if cur.fetchone()[0] == 0:
            demo_case = (
                "CASE-2026-001",
                "CMP-2026-001",
                None,
                "Investigation: Double Disposition Claim on Dag Plot #6792 (Paba Upazila)",
                "6792",
                "DEED-2005-23539",
                "CRITICAL",
                "UNDER_REVIEW",
                "USR-ADMIN-001",
                "STATUTORY_CONTRADICTION",
                0.9450,
                "Sub-Registry volume cross-examination indicates prior transfer executed in 2000. AC Land mutation record reflects vendor lacks title.",
                now,
                now,
            )
            cur.execute(
                """
                INSERT INTO cases (
                    case_id, complaint_id, verification_id, title, dag_plot_number,
                    deed_number, priority, status, assigned_officer_id,
                    statutory_finding, ml_risk_score, evidence_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                demo_case,
            )
            cur.execute(
                """
                INSERT INTO case_notes (note_id, case_id, author_id, note_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "NOTE-2026-001",
                    "CASE-2026-001",
                    "USR-ADMIN-001",
                    "Preliminary verification reveals prior deed DEED-2000-41374 exists in Book 1 volume. Dispatched field inspector to Rajshahi Sub-Registry.",
                    now,
                ),
            )
            conn.commit()

        # 5. Seed Initial Notification if empty
        cur.execute("SELECT COUNT(*) FROM notifications")
        if cur.fetchone()[0] == 0:
            cur.execute(
                """
                INSERT INTO notifications (notification_id, recipient_user_id, title, message, link_url, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "NOTIF-2026-001",
                    "USR-CITIZEN-001",
                    "Expedited Review Approved: CMP-2026-001",
                    "Your expedite request for complaint CMP-2026-001 has been approved by Senior Registrar M. Rahman.",
                    "/user/complaints/CMP-2026-001",
                    0,
                    now,
                ),
            )
            conn.commit()

    # ---------------------------------------------------------
    # Delegated Methods: Audit Logging
    # ---------------------------------------------------------

    def log_audit_event(
        self,
        actor_id: str,
        action_type: str,
        target_entity: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        """Logs an immutable audit event to the active operational store."""
        return self.audit.log_audit_event(
            actor_id=actor_id,
            action_type=action_type,
            target_entity=target_entity,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
        )

    def get_recent_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent audit events sorted newest first."""
        return self.audit.get_recent_audit_events(limit=limit)

    def get_audit_events_for_target(self, target_entity: str, target_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves audit events for a specific entity and ID, newest first."""
        return self.audit.get_audit_events_for_target(target_entity=target_entity, target_id=target_id, limit=limit)

    # ---------------------------------------------------------
    # Delegated Methods: Users & Sessions
    # ---------------------------------------------------------

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetches active user by email."""
        return self.users.get_user_by_email(email=email)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetches user by user_id."""
        return self.users.get_user_by_id(user_id=user_id)

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns safe user directory listing."""
        return self.users.list_users()

    def create_session(
        self,
        session_id: str,
        user_id: str,
        expires_at: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """Records an active session in the database."""
        return self.users.create_session(
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves active session and associated user info."""
        return self.users.get_session(session_id=session_id)

    def destroy_session(self, session_id: str):
        """Invalidates a session on logout or expiry."""
        return self.users.destroy_session(session_id=session_id)

    # ---------------------------------------------------------
    # Delegated Methods: Complaints
    # ---------------------------------------------------------

    def create_complaint(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new citizen complaint."""
        return self.complaints.create_complaint(c=c)

    def get_complaint(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single complaint with citizen details and linked case info."""
        return self.complaints.get_complaint(complaint_id=complaint_id)

    def list_complaints(
        self,
        citizen_user_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists complaints with optional citizen, category, or status filtering."""
        return self.complaints.list_complaints(
            citizen_user_id=citizen_user_id,
            status=status,
            category=category,
        )

    def update_complaint(self, complaint_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates complaint fields in SQLite."""
        return self.complaints.update_complaint(complaint_id=complaint_id, updates=updates)

    # ---------------------------------------------------------
    # Delegated Methods: Cases & Case Notes
    # ---------------------------------------------------------

    def create_case(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an investigation case docket in SQLite."""
        return self.cases.create_case(case_dict=case_dict)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves case details and all associated officer notes."""
        return self.cases.get_case(case_id=case_id)

    def get_case_for_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Finds active case escalated from a specific verification run."""
        return self.cases.get_case_for_verification(verification_id=verification_id)

    def list_cases(self, status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists investigation cases with optional filtering."""
        return self.cases.list_cases(status=status, priority=priority)

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates case status, priority, or assignment."""
        return self.cases.update_case(case_id=case_id, updates=updates)

    def add_case_note(self, case_id: str, author_id: str, note_text: str) -> Dict[str, Any]:
        """Appends a timestamped officer note to an investigation case."""
        return self.cases.add_case_note(case_id=case_id, author_id=author_id, note_text=note_text)

    def get_case_notes(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieves all notes for a case."""
        return self.cases.get_case_notes(case_id=case_id)

    # ---------------------------------------------------------
    # Delegated Methods: Notifications
    # ---------------------------------------------------------

    def create_notification(
        self,
        recipient_user_id: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        notification_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates and persists an in-app notification."""
        return self.notifications.create_notification(
            recipient_user_id=recipient_user_id,
            title=title,
            message=message,
            link_url=link_url,
            notification_id=notification_id,
        )

    def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all notifications for a specific user, sorted newest first."""
        return self.notifications.get_notifications(user_id=user_id)

    def mark_notification_read(self, notification_id: str):
        """Marks a notification as read."""
        return self.notifications.mark_notification_read(notification_id=notification_id)

    def mark_all_notifications_read(self, user_id: str) -> int:
        """Marks all notifications as read for a specific user."""
        return self.notifications.mark_all_read(user_id=user_id)

    # ---------------------------------------------------------
    # Delegated Methods: Verification Runs & Findings
    # ---------------------------------------------------------

    def save_verification_run(self, v_run: Dict[str, Any], findings: Optional[List[Dict[str, Any]]] = None):
        """Persists a complete verification dossier and statutory findings to SQLite."""
        return self.verifications.save_verification_run(v_run=v_run, findings=findings)

    def get_verification_run(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a verification run and all associated rule findings."""
        return self.verifications.get_verification_run(verification_id=verification_id)

    def list_verification_runs(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Lists verification runs ordered newest first, optionally filtered by user_id."""
        return self.verifications.list_verification_runs(user_id=user_id, limit=limit, offset=offset)

    def update_verification_report_status(
        self,
        verification_id: str,
        report_status: str,
        status_reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates report lifecycle state (VALID, WITHDRAWN, SUPERSEDED, RE_REVIEW_REQUIRED)."""
        return self.verifications.update_verification_report_status(
            verification_id=verification_id,
            report_status=report_status,
            status_reason=status_reason,
        )

    # ---------------------------------------------------------
    # Delegated Methods: Documents
    # ---------------------------------------------------------

    def save_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves metadata for an uploaded deed document."""
        return self.documents.save_document(doc_data=doc_data)

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves document record by document_id."""
        return self.documents.get_document(document_id=document_id)

    def delete_document(self, document_id: str) -> bool:
        """Deletes document record by document_id from operational database."""
        return self.documents.delete_document(document_id=document_id)
