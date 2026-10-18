"""Audit Repository
Handles immutable audit event logging and querying for administrative and operational events.
"""

import datetime
import json
import os
from typing import Dict, Any, List, Optional
from src.landguard_data.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    """Data access repository for audit trail events."""

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
        event_id = f"AUD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex().upper()}"
        details_str = json.dumps(details or {})
        now = datetime.datetime.now().isoformat()

        conn = self._get_connection()
        try:
            if self.db_type == "POSTGRESQL":
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO audit_events (event_id, actor_id, action_type, target_entity, target_id, details, ip_address, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (event_id, actor_id, action_type, target_entity, target_id, details_str, ip_address, now),
                )
                conn.commit()
                cur.close()
            else:
                conn.execute(
                    """
                    INSERT INTO audit_events (event_id, actor_id, action_type, target_entity, target_id, details, ip_address, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, actor_id, action_type, target_entity, target_id, details_str, ip_address, now),
                )
                conn.commit()
        except Exception as e:
            print(f"[LandGuard DB] Failed to log audit event: {e}")
        finally:
            conn.close()

    def get_recent_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent audit events sorted newest first."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT event_id, actor_id, action_type, target_entity, target_id, details, ip_address, created_at
                FROM audit_events ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            events = []
            for r in rows:
                ev = dict(r)
                if isinstance(ev.get("details"), str):
                    try:
                        ev["details"] = json.loads(ev["details"])
                    except Exception:
                        pass
                events.append(ev)
            return events
        except Exception as e:
            print(f"[LandGuard DB] Error fetching audit events: {e}")
            return []
        finally:
            conn.close()

    def get_audit_events_for_target(self, target_entity: str, target_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves audit events for a specific entity and ID, newest first."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT event_id, actor_id, action_type, target_entity, target_id, details, ip_address, created_at
                FROM audit_events
                WHERE target_entity = ? AND target_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (target_entity, target_id, limit),
            )
            rows = cursor.fetchall()
            events = []
            for r in rows:
                ev = dict(r)
                if isinstance(ev.get("details"), str):
                    try:
                        ev["details"] = json.loads(ev["details"])
                    except Exception:
                        pass
                events.append(ev)
            return events
        except Exception as e:
            print(f"[LandGuard DB] Error fetching audit events for target: {e}")
            return []
        finally:
            conn.close()
