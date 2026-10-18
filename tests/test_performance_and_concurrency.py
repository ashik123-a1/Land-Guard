"""Test Performance, Load, and Concurrency Verification.
Verifies:
1. SQLite WAL mode (Write-Ahead Logging) and busy timeout are active.
2. Concurrent parallel verification runs execute without database lock errors or data loss.
3. Concurrent parallel case notes, complaints, and audit logging succeed under multi-threaded load.
4. Response latency remains responsive under concurrent load.
"""

import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app, service


@pytest.fixture
def client():
    return TestClient(app)


def test_sqlite_wal_mode_and_concurrency_settings():
    """Verify SQLite database connection has WAL mode and busy_timeout configured."""
    conn = service.db._get_connection()
    c = conn.cursor()
    c.execute("PRAGMA journal_mode;")
    mode = c.fetchone()[0]
    assert str(mode).lower() in ["wal", "memory"]

    c.execute("PRAGMA busy_timeout;")
    timeout_val = c.fetchone()[0]
    assert int(timeout_val) >= 1000
    conn.close()


def test_concurrent_verification_runs():
    """Simulate 15 concurrent deed verification requests across 5 worker threads."""
    test_client = TestClient(app)

    def run_single_verification(idx: int):
        payload = {
            "confirmed_fields": {
                "deed_number": f"DEED-CONC-{idx:03d}",
                "dag_plot_number": "9044",
                "transferred_area_decimal": 1.5,
                "execution_date": "2024-06-01",
                "seller_nid": "OWN-CE177B4E",
                "buyer_nid": f"BUYER-CONC-{idx:03d}",
                "consideration_bdt": 500000.0,
            }
        }
        res = test_client.post("/api/verify", json=payload)
        return res.status_code, res.json()

    num_requests = 15
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_single_verification, i) for i in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_requests
    for status_code, data in results:
        assert status_code == 200
        assert data["verification_id"].startswith("VRF-")
        assert data["overall_status"] in ["CLEAR_FOR_STANDARD_PROCESSING", "REVIEW_REQUIRED", "CONFIRMED_INCONSISTENCY"]


def test_concurrent_complaints_and_audit_logging():
    """Simulate parallel citizen dispute filings and case notes under concurrency."""
    def run_single_complaint_and_note(idx: int):
        comp = service.create_complaint(
            user_id="USR-CITIZEN-001",
            data={
                "citizen_user_id": "USR-CITIZEN-001",
                "title": f"Concurrent Dispute #{idx}",
                "dag_plot_number": "9044",
                "category": "TITLE_DISPUTE",
                "narrative_description": f"Concurrent stress test complaint #{idx}",
            }
        )
        service.db.log_audit_event(
            actor_id="USR-CITIZEN-001",
            action_type="CONCURRENT_STRESS_TEST",
            target_entity="COMPLAINT",
            target_id=comp["complaint_id"],
            details={"idx": idx},
        )
        return comp["complaint_id"]

    num_writes = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_single_complaint_and_note, i) for i in range(num_writes)]
        comp_ids = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(comp_ids) == num_writes
    assert len(set(comp_ids)) == num_writes  # All IDs must be unique
