"""Test Cadastral Graph & What-If Simulator.
Verifies:
1. Cadastral Graph endpoint returns nodes and edges representation of ownership chain, surveys, and sub-plots.
2. What-If Transaction Simulator runs prospective statutory checks (capacity, seller title, double-selling risk).
3. Zero-mutation guarantees: What-If simulation NEVER writes to SQLite operational database or mutates application state.
"""

import pytest
from fastapi.testclient import TestClient
from src.landguard_web.app import app, service


@pytest.fixture
def client():
    return TestClient(app)


def test_cadastral_graph_valid_parcel(client):
    """GET /api/parcels/{plot_or_id}/graph returns full graph topology."""
    response = client.get("/api/parcels/9044/graph")
    assert response.status_code == 200
    data = response.json()

    assert data["dag_plot_number"] == "9044"
    assert "nodes" in data
    assert "edges" in data
    assert data["total_nodes"] > 0
    assert data["total_edges"] > 0
    assert "SYNTHETIC DEMO" in data["disclaimer"]

    # Verify parcel core node exists
    node_types = {n["type"] for n in data["nodes"]}
    assert "PARCEL" in node_types
    assert "SURVEY" in node_types
    assert "TRANSACTION" in node_types or "PARTY" in node_types


def test_cadastral_graph_not_found(client):
    """GET /api/parcels/{plot_or_id}/graph for non-existent parcel returns 404."""
    response = client.get("/api/parcels/NON_EXISTENT_PLOT_999999/graph")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_what_if_simulator_feasible_transaction(client):
    """POST /api/simulator/what-if evaluates feasible prospective sale."""
    payload = {
        "dag_plot_number": "9044",
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-TEST",
        "transferred_area_decimal": 4.5,
        "consideration_bdt": 1500000.0,
        "previous_deed_ref": "DEED-2001-35323",
        "mutation_case_no": "MUT-2006-5364/Rupsha",
    }
    response = client.post("/api/simulator/what-if", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["dag_plot_number"] == "9044"
    assert res["is_simulation"] is True
    assert res["can_proceed"] is True
    assert res["overall_verdict"] == "FEASIBLE"
    assert res["remaining_capacity_decimal"] == pytest.approx(9.24 - 4.5, 0.01)
    assert "SYNTHETIC DEMO" in res["disclaimer"]


def test_what_if_simulator_exceeds_capacity(client):
    """POST /api/simulator/what-if warns when proposed area exceeds parcel capacity."""
    payload = {
        "dag_plot_number": "9044",
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-TEST",
        "transferred_area_decimal": 25.0,  # Total parcel is 9.24 decimal
        "consideration_bdt": 5000000.0,
    }
    response = client.post("/api/simulator/what-if", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["can_proceed"] is False
    assert res["overall_verdict"] == "CRITICAL_DEFECT"
    warning_codes = [w["rule_code"] for w in res["statutory_warnings"]]
    assert "RULE_AREA_EXCEEDS_CAPACITY" in warning_codes


def test_what_if_simulator_seller_no_title(client):
    """POST /api/simulator/what-if warns when prospective vendor has no title or mutation record."""
    payload = {
        "dag_plot_number": "9044",
        "seller_nid": "FAKE-SELLER-WITHOUT-TITLE-999",
        "buyer_nid": "OWN-BUYER-TEST",
        "transferred_area_decimal": 2.0,
        "consideration_bdt": 500000.0,
    }
    response = client.post("/api/simulator/what-if", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["overall_verdict"] in ["HIGH_RISK", "CRITICAL_DEFECT"]
    warning_codes = [w["rule_code"] for w in res["statutory_warnings"]]
    assert any(c in warning_codes for c in ["RULE_SELLER_NOT_TITLEHOLDER", "RULE_SELLER_NO_TITLE"])


def test_what_if_simulator_zero_db_mutation(client):
    """Verify simulation is strictly read-only and causes ZERO mutations in SQLite operational database."""
    conn = service.db._get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM verification_runs")
    v_count_before = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints")
    comp_count_before = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cases")
    case_count_before = c.fetchone()[0]
    conn.close()

    # Execute simulation
    payload = {
        "dag_plot_number": "9044",
        "seller_nid": "OWN-CE177B4E",
        "buyer_nid": "OWN-BUYER-TEST",
        "transferred_area_decimal": 3.0,
        "consideration_bdt": 1000000.0,
    }
    res = client.post("/api/simulator/what-if", json=payload)
    assert res.status_code == 200

    conn = service.db._get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM verification_runs")
    v_count_after = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints")
    comp_count_after = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cases")
    case_count_after = c.fetchone()[0]
    conn.close()

    assert v_count_before == v_count_after
    assert comp_count_before == comp_count_after
    assert case_count_before == case_count_after


def test_cross_parcel_pattern_analysis(client):
    """GET /api/parcels/{plot}/patterns analyzes cross-parcel entity occurrences without labeling coincidences as fraud."""
    res = client.get("/api/parcels/9044/cross-parcel-patterns")
    assert res.status_code == 200
    data = res.json()

    assert data["target_dag_plot"] == "9044"
    assert "pattern_type" in data
    assert "risk_indicator" in data
    assert "explanation" in data
    assert "disclaimer" in data
    assert "fraudulent intent" in data["disclaimer"].lower()
    assert isinstance(data["conveyance_records"], list)

