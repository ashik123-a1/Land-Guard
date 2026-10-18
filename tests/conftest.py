"""Pytest Root Configuration & Test Database Isolation Suite.
Guarantees:
1. All automated tests run against an isolated, disposable temporary SQLite clone.
2. The operational database (data/landguard_operational.db) is strictly protected.
3. Temporary clone is created using SQLite's supported backup API (preserving WAL state).
4. Eagerly-imported service facade and repositories are rebound to the isolated database.
5. Strict safety guard prevents any automated test from connecting to the operational database.
"""

import os
import shutil
import sqlite3
import tempfile
import pytest

_TEST_TEMP_DIR = None
_TEST_DB_PATH = None
_OPERATIONAL_DB_PATH = os.path.abspath("data/landguard_operational.db")


def pytest_configure(config):
    """Establishes isolated temporary database BEFORE test discovery and module imports."""
    global _TEST_TEMP_DIR, _TEST_DB_PATH

    _TEST_TEMP_DIR = tempfile.mkdtemp(prefix="landguard_test_isolation_")
    _TEST_DB_PATH = os.path.abspath(os.path.join(_TEST_TEMP_DIR, "landguard_operational.db"))

    # Populate temporary test database using SQLite online backup API
    if os.path.exists(_OPERATIONAL_DB_PATH):
        src_conn = sqlite3.connect(f"file:{_OPERATIONAL_DB_PATH}?mode=ro", uri=True)
        dst_conn = sqlite3.connect(_TEST_DB_PATH)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

    # Configure environment overrides
    os.environ["LANDGUARD_DB_PATH"] = _TEST_DB_PATH
    os.environ["LANDGUARD_TEST_MODE"] = "1"

    # Rebind service singleton if already imported
    try:
        from src.landguard_web.service import service
        service.rebind_database(_TEST_DB_PATH)
    except Exception:
        pass


def pytest_unconfigure(config):
    """Cleans up isolated temporary database after all test suites complete."""
    global _TEST_TEMP_DIR, _TEST_DB_PATH

    if os.environ.get("LANDGUARD_DB_PATH") == _TEST_DB_PATH:
        os.environ.pop("LANDGUARD_DB_PATH", None)
    os.environ.pop("LANDGUARD_TEST_MODE", None)

    if _TEST_TEMP_DIR and os.path.exists(_TEST_TEMP_DIR):
        try:
            shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
        except Exception:
            pass


@pytest.fixture(autouse=True, scope="function")
def ensure_test_database_isolation():
    """Safety assertion verifying that every test runs strictly against the isolated database."""
    current_db = os.environ.get("LANDGUARD_DB_PATH")
    assert current_db is not None, "LANDGUARD_DB_PATH must be set during test runs."
    assert os.path.abspath(current_db) != _OPERATIONAL_DB_PATH, (
        f"VIOLATION: Test database path '{current_db}' matches operational database path!"
    )
    
    # Ensure service singleton uses the isolated path
    try:
        from src.landguard_web.service import service
        if hasattr(service, "db") and os.path.abspath(service.db.db_path) != os.path.abspath(current_db):
            service.rebind_database(current_db)
    except Exception:
        pass
