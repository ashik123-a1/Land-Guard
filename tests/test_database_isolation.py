"""Automated verification suite for Test Database Isolation and Operational Data Protection.
Validates:
1. LANDGUARD_DB_PATH points to a temporary isolated SQLite database, never data/landguard_operational.db.
2. The BaseRepository safety guard rejects any attempt to open a connection to data/landguard_operational.db during tests.
3. State-changing operations (creating complaints, audit events) persist in the isolated test database while leaving the operational database completely unchanged.
"""

import os
import sqlite3
import pytest
from src.landguard_data.repositories.base import BaseRepository, get_default_db_path
from src.landguard_web.service import service

OPERATIONAL_DB_PATH = os.path.abspath("data/landguard_operational.db")


def test_isolation_environment_active():
    """Verify that tests execute strictly against an isolated temporary clone."""
    active_path = get_default_db_path()
    assert active_path != OPERATIONAL_DB_PATH, "Default DB path must not point to operational database in tests."
    assert "landguard_operational.db" in active_path
    assert os.path.exists(active_path), f"Isolated test database '{active_path}' must exist."
    assert os.path.abspath(service.db.db_path) == os.path.abspath(active_path)


def test_operational_database_write_protection_guard():
    """Verify that BaseRepository raises RuntimeError if a test tries to connect to operational DB."""
    # Attempt to initialize a repository directly pointing to operational database
    repo = BaseRepository(db_path=OPERATIONAL_DB_PATH)
    assert os.path.abspath(repo.db_path) == OPERATIONAL_DB_PATH

    with pytest.raises(RuntimeError) as exc_info:
        repo._get_connection()

    assert "SAFETY GUARD TRIGGERED" in str(exc_info.value)
    assert "Automated test attempted to connect to operational database" in str(exc_info.value)


def test_state_changing_operations_do_not_mutate_operational_database():
    """Verify that writing a complaint in test updates only the isolated DB and leaves operational DB untouched."""
    # 1. Capture exact baseline from operational database in read-only mode
    conn_ro = sqlite3.connect(f"file:{OPERATIONAL_DB_PATH}?mode=ro", uri=True)
    cur = conn_ro.cursor()
    cur.execute("SELECT COUNT(*) FROM complaints")
    initial_operational_complaints = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM audit_events")
    initial_operational_audits = cur.fetchone()[0]
    conn_ro.close()

    # 2. Write a new complaint through service
    comp = service.create_complaint(
        user_id="USR-CITIZEN-001",
        data={
            "citizen_user_id": "USR-CITIZEN-001",
            "title": "Isolated Test Complaint Verification",
            "dag_plot_number": "9044",
            "category": "TITLE_DISPUTE",
            "narrative_description": "Ensuring this complaint is strictly written to isolated DB.",
        }
    )
    assert comp is not None
    assert comp["complaint_id"].startswith("CMP-")

    # 3. Verify it exists in the isolated test database
    assert service.get_complaint(comp["complaint_id"]) is not None

    # 4. Check operational database again in read-only mode: MUST BE COMPLETELY UNCHANGED
    conn_ro2 = sqlite3.connect(f"file:{OPERATIONAL_DB_PATH}?mode=ro", uri=True)
    cur2 = conn_ro2.cursor()
    cur2.execute("SELECT COUNT(*) FROM complaints")
    final_operational_complaints = cur2.fetchone()[0]
    cur2.execute("SELECT COUNT(*) FROM audit_events")
    final_operational_audits = cur2.fetchone()[0]
    cur2.execute("SELECT 1 FROM complaints WHERE complaint_id = ?", (comp["complaint_id"],))
    found_in_operational = cur2.fetchone()
    conn_ro2.close()

    assert final_operational_complaints == initial_operational_complaints, (
        f"OPERATIONAL POLLUTION DETECTED! Operational complaints changed: {initial_operational_complaints} -> {final_operational_complaints}"
    )
    assert final_operational_audits == initial_operational_audits, (
        f"OPERATIONAL POLLUTION DETECTED! Operational audits changed: {initial_operational_audits} -> {final_operational_audits}"
    )
    assert found_in_operational is None, "Test complaint leaked into operational database!"
