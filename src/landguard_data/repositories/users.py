"""User and Session Repository
Handles persistence and queries for users and authentication sessions.
"""

import datetime
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access repository for users and sessions."""

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetches active user by email."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetches user by user_id."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns safe user directory listing."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT user_id, email, full_name, role, national_id, digital_identity_id,
                       phone, division, district, upazila, is_active, created_at
                FROM users ORDER BY created_at ASC
                """
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def create_session(
        self,
        session_id: str,
        user_id: str,
        expires_at: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """Records an active session in SQLite."""
        conn = self._get_connection()
        try:
            now = datetime.datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, created_at, expires_at, user_agent, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, now, expires_at, user_agent, ip_address),
            )
            conn.commit()
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves active session and associated user info."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT s.session_id, s.user_id, s.expires_at,
                       u.email, u.full_name, u.role, u.national_id, u.digital_identity_id,
                       u.phone, u.division, u.district, u.upazila, u.preferred_language
                FROM sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_id = ?
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            # Verify expiry
            if data["expires_at"] < datetime.datetime.now().isoformat():
                self.destroy_session(session_id)
                return None
            return {
                "session_id": data["session_id"],
                "user": {
                    "user_id": data["user_id"],
                    "email": data["email"],
                    "full_name": data["full_name"],
                    "role": data["role"],
                    "national_id": data["national_id"],
                    "digital_identity_id": data["digital_identity_id"],
                    "phone": data["phone"],
                    "division": data["division"],
                    "district": data["district"],
                    "upazila": data["upazila"],
                    "preferred_language": data.get("preferred_language") or "bn",
                },
                "expires_at": data["expires_at"],
            }
        finally:
            conn.close()

    def update_user_preference(self, user_id: str, preferred_language: str) -> bool:
        """Updates user's preferred language in SQLite."""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE users SET preferred_language = ? WHERE user_id = ?",
                (preferred_language, user_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def destroy_session(self, session_id: str):
        """Deletes session on logout."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()
