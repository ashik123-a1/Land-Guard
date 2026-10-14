"""Tests experimental tampering scenario generation and discrepancy injection."""

import random
from src.landguard_data.generate_entities import generate_entities
from src.landguard_data.generate_scenarios import create_scenario, SCENARIO_TYPES


def test_tampering_scenarios_injection():
    rng = random.Random(42)
    owners, parcels = generate_entities(count_owners=10, count_parcels=5, seed=42)
    
    # Test area inflation
    area_type = next(s for s in SCENARIO_TYPES if s[0] == "EXAGGERATED_LAND_AREA")
    scen, txns, muts, taxes = create_scenario(area_type, parcels[0], owners, rng)
    assert scen["is_fraud_risk"] is True
    assert txns[-1]["transferred_area_decimal"] > parcels[0]["total_area_decimal"]
    
    # Test plot mismatch
    plot_type = next(s for s in SCENARIO_TYPES if s[0] == "ALTERED_PLOT_NUMBER")
    scen_plot, txns_plot, _, _ = create_scenario(plot_type, parcels[0], owners, rng)
    assert scen_plot["is_fraud_risk"] is True
    assert "RULE_PLOT_MISMATCH_WITH_KHATIAN" in scen_plot["simulator_audit_metadata"]["expected_rule_violations"]
