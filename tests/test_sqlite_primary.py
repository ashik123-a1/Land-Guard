"""Tests for SQLite Primary Database Architecture
Verifies:
1. SQLite is ALWAYS the unconditional active primary database even when DATABASE_URL is present.
2. /api/health endpoint reports db_type: "SQLITE" and Neon in STANDBY (active_for_traffic: False).
3. Audit events, complaints, and normal operations write directly to data/landguard_operational.db.
4. Existing SQLite tables and records remain intact without drops or truncations.
5. Neon PostgreSQL can only be activated when DATABASE_BACKEND=POSTGRESQL is explicitly set.
"""

import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app
from src.landguard_data.database import LandGuardDatabase

client = TestClient(app, follow_redirects=False)


def test_sqlite_is_unconditional_default_even_with_database_url():
    """Verify that LandGuardDatabase defaults to SQLite even if DATABASE_URL is present."""
    # Ensure DATABASE_URL is present
    original_backend = os.environ.get("DATABASE_BACKEND")
    try:
        # Without explicit DATABASE_BACKEND, SQLite must be active
        if "DATABASE_BACKEND" in os.environ:
            del os.environ["DATABASE_BACKEND"]
        
        db = LandGuardDatabase()
        assert db.db_type == "SQLITE"
        assert db.neon_configured is True  # Neon is detected on standby
        assert "landguard_operational.db" in db.db_path

        # With explicit DATABASE_BACKEND=SQLITE
        os.environ["DATABASE_BACKEND"] = "SQLITE"
        db2 = LandGuardDatabase()
        assert db2.db_type == "SQLITE"
    finally:
        if original_backend is not None:
            os.environ["DATABASE_BACKEND"] = original_backend
        else:
            os.environ["DATABASE_BACKEND"] = "SQLITE"


def test_health_endpoint_reports_sqlite_primary():
    """Verify /api/health explicitly reports db_type: SQLITE and Neon on standby."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "HEALTHY"
    assert data["db_type"] == "SQLITE"
    assert data["primary_database"] == "SQLITE"
    assert data["database_backend"] == "SQLITE"

    # Verify Neon PostgreSQL is reported separately on standby without claiming active traffic
    assert "neon_postgres" in data
    assert data["neon_postgres"]["configured"] is True
    assert data["neon_postgres"]["status"] == "STANDBY"
    assert data["neon_postgres"]["active_for_traffic"] is False


def test_audit_logging_writes_to_sqlite_file():
    """Verify audit logging operations write directly to local SQLite database file."""
    db = LandGuardDatabase()
    assert db.db_type == "SQLITE"

    test_action = f"TEST_SQLITE_AUDIT_VERIFICATION_{os.urandom(3).hex().upper()}"
    db.log_audit_event(
        actor_id="USR-TEST-001",
        action_type=test_action,
        target_entity="PARCEL",
        target_id="PAR-9044",
        details={"storage": "local_sqlite_file", "verified": True},
        ip_address="127.0.0.1",
    )

    # Directly verify in the SQLite database file using standard sqlite3
    conn = sqlite3.connect("data/landguard_operational.db")
    cur = conn.cursor()
    cur.execute("SELECT actor_id, action_type, target_entity, target_id FROM audit_events WHERE action_type = ?", (test_action,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "USR-TEST-001"
    assert row[1] == test_action
    assert row[2] == "PARCEL"
    assert row[3] == "PAR-9044"


def test_existing_sqlite_tables_remain_intact():
    """Verify that all 16 operational tables exist in SQLite and none were dropped."""
    expected_tables = {
        "roles", "users", "sessions", "parcels", "ownership_events",
        "deeds", "mutations", "tax_records", "documents", "verification_runs",
        "verification_findings", "complaints", "cases", "case_notes",
        "notifications", "audit_events"
    }

    conn = sqlite3.connect("data/landguard_operational.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {r[0] for r in cur.fetchall()}
    conn.close()

    assert expected_tables.issubset(existing_tables), f"Missing tables: {expected_tables - existing_tables}"


def test_explicit_postgresql_activation_requires_explicit_backend_flag():
    """Verify that PostgreSQL activates ONLY when DATABASE_BACKEND=POSTGRESQL is explicitly declared."""
    original_backend = os.environ.get("DATABASE_BACKEND")
    try:
        os.environ["DATABASE_BACKEND"] = "POSTGRESQL"
        db = LandGuardDatabase()
        # When explicitly configured, it connects to PostgreSQL
        assert db.db_type == "POSTGRESQL"
    finally:
        # Reset back to SQLite
        if original_backend is not None:
            os.environ["DATABASE_BACKEND"] = original_backend
        else:
            os.environ["DATABASE_BACKEND"] = "SQLITE"

    # Confirm it returns to SQLite
    db_restored = LandGuardDatabase()
    assert db_restored.db_type == "SQLITE"
