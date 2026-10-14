"""LandGuard Operational Database Adapter
Primary & Active: Local SQLite (data/landguard_operational.db) - ALWAYS unconditional default.
Standby: Neon Serverless PostgreSQL (via DATABASE_URL) - configured for future use,
         active ONLY if explicitly selected via DATABASE_BACKEND=POSTGRESQL.
"""

import os
import sqlite3
import datetime
from typing import Dict, Any, List, Optional
import json

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


class LandGuardDatabase:
    """Operational database manager for LandGuard state and audit logging."""

    def __init__(self, db_path: Optional[str] = None):
        self.database_url = os.environ.get("DATABASE_URL")
        self.db_path = db_path or os.path.abspath("data/landguard_operational.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Check explicit backend selection. SQLite is ALWAYS the unconditional default.
        backend_choice = os.environ.get("DATABASE_BACKEND", "SQLITE").strip().upper()
        
        # Detect if Neon PostgreSQL is configured on standby
        self.neon_configured = bool(self.database_url and PSYCOPG2_AVAILABLE)
        
        if backend_choice == "POSTGRESQL" and self.neon_configured:
            try:
                test_conn = psycopg2.connect(self.database_url)
                test_conn.close()
                self.db_type = "POSTGRESQL"
                print(f"[LandGuard DB] Explicitly activated Neon PostgreSQL backend: {self.get_sanitized_url()}")
            except Exception as e:
                print(f"[LandGuard DB] Warning: PostgreSQL activation failed ({e}). Falling back to primary SQLite.")
                self.db_type = "SQLITE"
        else:
            # SQLite is ALWAYS the unconditional default for all application reads/writes
            self.db_type = "SQLITE"
            standby_info = f" (Neon PostgreSQL on standby: {self.get_sanitized_url()})" if self.neon_configured else ""
            print(f"[LandGuard DB] Active primary database: SQLite at {self.db_path}{standby_info}")

        self._init_database()

    def get_sanitized_url(self) -> Optional[str]:
        """Returns connection string with credentials stripped for safe logging and reporting."""
        if not self.database_url:
            return None
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.database_url)
            host = parsed.hostname or "unknown"
            port = f":{parsed.port}" if parsed.port else ""
            path = parsed.path or ""
            return f"{parsed.scheme}://***:***@{host}{port}{path}"
        except Exception:
            return "postgresql://***:***@neon.tech/neondb"

    def _get_connection(self):
        """Returns database connection with row factory."""
        if self.db_type == "POSTGRESQL":
            try:
                return psycopg2.connect(self.database_url)
            except Exception as e:
                print(f"[LandGuard DB] PostgreSQL connection error: {e}. Falling back to SQLite.")
                self.db_type = "SQLITE"
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                return conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn

    def _init_database(self):
        """Executes migration schema idempotently without dropping or truncating tables."""
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
                # Convert PostgreSQL-specific syntax for SQLite compatibility
                sqlite_script = sql_script.replace("BOOLEAN DEFAULT TRUE", "INTEGER DEFAULT 1")
                sqlite_script = sqlite_script.replace("BOOLEAN DEFAULT FALSE", "INTEGER DEFAULT 0")
                sqlite_script = sqlite_script.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                sqlite_script = sqlite_script.replace("JSON", "TEXT")
                conn.executescript(sqlite_script)
                conn.commit()
                print(f"[LandGuard DB] Verified SQLite operational schema at {self.db_path}")
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
            events = []
            if self.db_type == "POSTGRESQL":
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    """
                    SELECT event_id, actor_id, action_type, target_entity, target_id, details, ip_address, created_at
                    FROM audit_events ORDER BY created_at DESC LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                for r in rows:
                    ev = dict(r)
                    if isinstance(ev.get("details"), str):
                        try:
                            ev["details"] = json.loads(ev["details"])
                        except Exception:
                            pass
                    events.append(ev)
                cur.close()
            else:
                cursor = conn.execute(
                    """
                    SELECT event_id, actor_id, action_type, target_entity, target_id, details, ip_address, created_at
                    FROM audit_events ORDER BY created_at DESC LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
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
