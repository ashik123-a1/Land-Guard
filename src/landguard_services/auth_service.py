"""Authentication Domain Service
Handles authentication, password verification, session lifecycle, and user profile queries.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from src.landguard_data.database import LandGuardDatabase
from src.landguard_web.security import verify_password


class AuthService:
    """Domain service managing user authentication and sessions."""

    def __init__(self, db: Optional[LandGuardDatabase] = None, fallback_users: Optional[Dict[str, Dict[str, Any]]] = None):
        self.db = db or LandGuardDatabase()
        self.fallback_users = fallback_users or {}
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticates user against SQLite database (or fallback credentials) using PBKDF2."""
        email_clean = (email or "").strip().lower()
        db_user = self.db.get_user_by_email(email_clean)
        if db_user:
            stored_hash = db_user.get("password_hash") or ""
            if verify_password(password, stored_hash):
                safe_user = dict(db_user)
                safe_user.pop("password_hash", None)
                safe_user.pop("password", None)
                return safe_user

        user = self.fallback_users.get(email_clean)
        if not user:
            return None
        stored_pw = user.get("password_hash") or user.get("password") or ""
        if verify_password(password, stored_pw):
            safe_user = dict(user)
            safe_user.pop("password", None)
            safe_user.pop("password_hash", None)
            return safe_user
        return None

    def create_session(self, user_dict: Dict[str, Any]) -> str:
        """Creates session token, records in SQLite, and logs audit event."""
        session_id = f"SESS-{uuid.uuid4().hex.upper()}"
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=24)
        session_payload = {
            "session_id": session_id,
            "user": user_dict,
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        self.sessions[session_id] = session_payload
        try:
            self.db.create_session(
                session_id=session_id,
                user_id=user_dict["user_id"],
                expires_at=expires_at.isoformat(),
            )
        except Exception as e:
            print(f"[AuthService] Warning: Failed to persist session to SQLite: {e}")

        self.db.log_audit_event(
            actor_id=user_dict["user_id"],
            action_type="USER_LOGIN",
            target_entity="SESSION",
            target_id=session_id,
            details={"email": user_dict.get("email"), "role": user_dict.get("role")},
        )
        return session_id

    def get_user_by_session(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validates session token from memory cache or SQLite and returns active user."""
        if not session_id:
            return None
        sess = self.sessions.get(session_id)
        if sess:
            expires_at = datetime.datetime.fromisoformat(sess["expires_at"])
            if datetime.datetime.now() > expires_at:
                del self.sessions[session_id]
                self.db.destroy_session(session_id)
                return None
            return sess["user"]

        db_sess = self.db.get_session(session_id)
        if db_sess:
            self.sessions[session_id] = {
                "session_id": session_id,
                "user": db_sess["user"],
                "created_at": datetime.datetime.now().isoformat(),
                "expires_at": db_sess["expires_at"],
            }
            return db_sess["user"]
        return None

    def destroy_session(self, session_id: Optional[str]):
        """Terminates session on logout."""
        if session_id:
            sess = self.sessions.pop(session_id, None)
            user = sess.get("user", {}) if sess else {}
            try:
                self.db.destroy_session(session_id)
            except Exception:
                pass
            self.db.log_audit_event(
                actor_id=user.get("user_id", "UNKNOWN"),
                action_type="USER_LOGOUT",
                target_entity="SESSION",
                target_id=session_id,
            )

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Returns safe user profile for display."""
        db_user = self.db.get_user_by_id(user_id)
        if db_user:
            clean = dict(db_user)
            clean.pop("password_hash", None)
            clean.pop("password", None)
            return clean

        for u in self.fallback_users.values():
            if u.get("user_id") == user_id:
                clean = dict(u)
                clean.pop("password_hash", None)
                clean.pop("password", None)
                return clean
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns safe directory listing of all system users."""
        users = self.db.list_users()
        if not users:
            users = [
                {k: v for k, v in u.items() if k not in ["password", "password_hash"]}
                for u in self.fallback_users.values()
            ]
        return users

    def update_user_preference(self, user_id: str, preferred_language: str) -> bool:
        """Updates user's preferred language in SQLite and active session cache."""
        # 1. Update SQLite
        try:
            self.db.users.update_user_preference(user_id=user_id, preferred_language=preferred_language)
        except Exception as e:
            print(f"[AuthService] Notice: Could not update preferred_language in DB: {e}")

        # 2. Update memory session cache
        for sess in self.sessions.values():
            if sess.get("user", {}).get("user_id") == user_id:
                sess["user"]["preferred_language"] = preferred_language

        # 3. Update fallback users if applicable
        for u in self.fallback_users.values():
            if u.get("user_id") == user_id:
                u["preferred_language"] = preferred_language

        return True
