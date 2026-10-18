"""LandGuard Base Repository
Manages SQLite database connections with WAL mode, foreign keys, busy timeout,
and connection pooling safety. Preserves Neon PostgreSQL standby connection capability.
"""

import os
import sqlite3
from typing import Optional

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


def get_default_db_path() -> str:
    """Returns the active SQLite database path.
    Honors LANDGUARD_DB_PATH environment variable if set (e.g. during test runs).
    Defaults to the canonical operational database: data/landguard_operational.db.
    """
    override = os.environ.get("LANDGUARD_DB_PATH")
    if override and override.strip():
        return os.path.abspath(override.strip())
    return os.path.abspath("data/landguard_operational.db")


class BaseRepository:
    """Base database connection provider for specialized repositories."""

    def __init__(self, db_path: Optional[str] = None):
        self.database_url = os.environ.get("DATABASE_URL")
        self.db_path = os.path.abspath(db_path) if db_path else get_default_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        backend_choice = os.environ.get("DATABASE_BACKEND", "SQLITE").strip().upper()
        self.neon_configured = bool(self.database_url and PSYCOPG2_AVAILABLE)

        if backend_choice == "POSTGRESQL" and self.neon_configured:
            try:
                test_conn = psycopg2.connect(self.database_url)
                test_conn.close()
                self.db_type = "POSTGRESQL"
            except Exception:
                self.db_type = "SQLITE"
        else:
            self.db_type = "SQLITE"

    def get_sanitized_url(self) -> Optional[str]:
        """Returns connection string with credentials stripped for safe reporting."""
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
        """Returns an active SQLite connection configured with WAL mode and busy timeout."""
        # Operational Database Write Protection Guard in Automated Test Environments:
        is_testing = bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("LANDGUARD_TEST_MODE"))
        operational_path = os.path.abspath("data/landguard_operational.db")
        if is_testing and os.path.abspath(self.db_path) == operational_path:
            raise RuntimeError(
                f"SAFETY GUARD TRIGGERED: Automated test attempted to connect to operational database "
                f"'{self.db_path}'! Tests must use an isolated temporary database configured via LANDGUARD_DB_PATH."
            )

        if self.db_type == "POSTGRESQL":
            try:
                return psycopg2.connect(self.database_url)
            except Exception:
                self.db_type = "SQLITE"
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA busy_timeout = 5000;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                return conn
        else:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            return conn
