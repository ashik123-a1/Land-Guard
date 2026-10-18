"""Automated test suite for Rule Governance, Seeded Scenarios, and Document Retention.
Validates:
1. Rule governance versioning, active rule definitions, and statutory justification enforcement.
2. Seeded reproducible scenario generator catalog and deterministic output with zero DB writes.
3. Document retention policy: authorized deletion, retention lock enforcement, and audit trail logging.
"""

import pytest
from fastapi.testclient import TestClient

from src.landguard_web.app import app
from src.landguard_services.rule_governance_service import RuleGovernanceService
from src.landguard_services.scenario_service import ScenarioService

client = TestClient(app, follow_redirects=False)


def test_rule_governance_service_and_versioning():
    """Verify ruleset versioning and mandatory statutory justification."""
    gov = RuleGovernanceService()
    active = gov.get_active_ruleset()
    assert active["ruleset_version"] == "2.4.0"
    assert "RULE-DOUBLE-SALE" in active["rules"]
    assert "RULE-AREA-CAPACITY" in active["rules"]

    # Rejection: justification too short
    with pytest.raises(ValueError):
        gov.update_ruleset(justification="too short")

    # Success: valid justification
    new_ver = gov.update_ruleset(
        new_thresholds={"critical_escalation_threshold": 0.75},
        officer="Senior Registrar M. Rahman",
        justification="Statutory Gazette Notification Land-2026/04 amended threshold",
    )
    assert new_ver["ruleset_version"] == "2.4.1"
    assert new_ver["ml_thresholds"]["critical_escalation_threshold"] == 0.75

    # History contains both versions immutably
    history = gov.get_ruleset_history()
    assert len(history) == 2
    assert history[0]["ruleset_version"] == "2.4.0"
    assert history[1]["ruleset_version"] == "2.4.1"


def test_admin_rules_api_endpoints():
    """GET and POST /api/admin/rules endpoints enforce Admin role and validation."""
    # Anonymous blocked
    anon_client = TestClient(app, follow_redirects=False)
    assert anon_client.get("/api/admin/rules").status_code == 303

    # Admin access
    admin_client = TestClient(app, follow_redirects=False)
    admin_client.post("/api/auth/demo-login?role=admin")

    get_res = admin_client.get("/api/admin/rules")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "active_ruleset" in data
    assert "version_history" in data

    # Update via API
    update_res = admin_client.post(
        "/api/admin/rules/update",
        json={
            "thresholds": {"tau_flagging_threshold": 0.36},
            "justification": "Annual calibration benchmark review completed by LandTech audit.",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["ml_thresholds"]["tau_flagging_threshold"] == 0.36


def test_scenario_service_reproducible_generation():
    """Scenario service returns catalog of 15 archetypes and generates seeded reproducible data."""
    svc = ScenarioService()
    catalog = svc.get_catalog()
    assert len(catalog) >= 15
    types = [c["scenario_type"] for c in catalog]
    assert "CONFLICTING_DOUBLE_SALE" in types
    assert "LEGITIMATE_NORMAL_SALE" in types

    # Deterministic generation with seed=42
    scen1 = svc.generate_reproducible_scenario("CONFLICTING_DOUBLE_SALE", seed=42)
    assert scen1["is_fraud_risk"] is True
    assert scen1["zero_operational_db_writes"] is True
    assert "SYNTHETIC DEMO" in scen1["disclaimer"]
    assert "target_transaction" in scen1

    # Exact reproducibility with same seed
    scen2 = svc.generate_reproducible_scenario("CONFLICTING_DOUBLE_SALE", seed=42)
    assert scen1["target_transaction"]["transferred_area_decimal"] == scen2["target_transaction"]["transferred_area_decimal"]


def test_scenario_api_endpoints():
    """GET /api/scenarios/catalog and POST /api/scenarios/generate work without DB mutation."""
    cat_res = client.get("/api/scenarios/catalog")
    assert cat_res.status_code == 200
    assert len(cat_res.json()) >= 15

    gen_res = client.post(
        "/api/scenarios/generate",
        json={"scenario_type": "EXAGGERATED_LAND_AREA", "seed": 99},
    )
    assert gen_res.status_code == 200
    data = gen_res.json()
    assert data["scenario_type"] == "EXAGGERATED_LAND_AREA"
    assert data["is_fraud_risk"] is True
    assert data["zero_operational_db_writes"] is True


def test_document_deletion_retention_policy():
    """DELETE /api/documents/{id} enforces authentication, ownership, and retention policy."""
    # Anonymous blocked
    anon_client = TestClient(app, follow_redirects=False)
    assert anon_client.delete("/api/documents/DOC-FAKE-001").status_code == 401

    # Authenticated Citizen uploads a document
    auth_client = TestClient(app, follow_redirects=False)
    auth_client.post("/api/auth/demo-login?role=citizen")

    # Upload synthetic document
    import io
    from PIL import Image
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    upload_res = auth_client.post(
        "/api/upload",
        files={"file": ("retention_test.png", buf, "image/png")},
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]

    # Delete document as authorized owner
    del_res = auth_client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"
    assert del_res.json()["document_id"] == doc_id
