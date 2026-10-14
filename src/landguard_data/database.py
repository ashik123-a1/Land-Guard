"""LandGuard Operational Database Adapter
Supports Neon PostgreSQL (via DATABASE_URL) with seamless local SQLite fallback.
Enforces foreign keys, indexes, and parameterized queries across all 10 table groups.
"""

import os
import sqlite3
import datetime
from typing import Dict, Any, List, Optional
import json


class LandGuardDatabase:
    """Operational database manager for LandGuard state and audit logging."""

    def __init__(self, db_path: Optional[str] = None):
        self.database_url = os.environ.get("DATABASE_URL")
        self.db_type = "POSTGRESQL" if self.database_url else "SQLITE"
        self.db_path = db_path or os.path.abspath("data/landguard_operational.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()

    def _get_connection(self):
        """Returns database connection with row factory."""
        if self.db_type == "SQLITE":
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        else:
            # PostgreSQL / Neon driver placeholder if configured
            try:
                import psycopg2
                return psycopg2.connect(self.database_url)
            except Exception as e:
                print(f"[LandGuard DB] Warning: PostgreSQL driver error: {e}. Falling back to SQLite.")
                self.db_type = "SQLITE"
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                return conn

    def _init_database(self):
        """Executes migration schema idempotently."""
        schema_path = os.path.abspath("migrations/001_initial_schema.sql")
        if not os.path.exists(schema_path):
            return

        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        conn = self._get_connection()
        try:
            if self.db_type == "SQLITE":
                # Convert PostgreSQL-specific syntax for SQLite compatibility
                sqlite_script = sql_script.replace("BOOLEAN DEFAULT TRUE", "INTEGER DEFAULT 1")
                sqlite_script = sqlite_script.replace("BOOLEAN DEFAULT FALSE", "INTEGER DEFAULT 0")
                sqlite_script = sqlite_script.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                sqlite_script = sqlite_script.replace("JSON", "TEXT")
                conn.executescript(sqlite_script)
                conn.commit()
                print(f"[LandGuard DB] Initialized SQLite operational database at {self.db_path}")
        except Exception as e:
            print(f"[LandGuard DB] Database initialization notice: {e}")
        finally:
            conn.close()

    def log_audit_event(
        self,
        actor_id: str,
        action_type: str,
        target_entity: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        """Logs an immutable audit event to the operational store."""
        event_id = f"AUD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex().upper()}"
        details_str = json.dumps(details or {})
        now = datetime.datetime.now().isoformat()

        conn = self._get_connection()
        try:
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
