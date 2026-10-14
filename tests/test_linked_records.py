"""Tests entity linkages, relational consistency, and referential integrity."""

import random
from src.landguard_data.generate_entities import generate_entities
from src.landguard_data.generate_records import generate_records_for_parcels
from src.landguard_data.generate_scenarios import create_scenario, SCENARIO_TYPES


def test_linked_entities_and_scenarios():
    rng = random.Random(42)
    owners, parcels = generate_entities(count_owners=10, count_parcels=5, seed=42)
    khatians = generate_records_for_parcels(parcels, owners, rng)
    
    parcel_ids = {p["parcel_id"] for p in parcels}
    for kh in khatians:
        assert kh["parcel_id"] in parcel_ids
        assert len(kh["owners"]) >= 1
        total_share = sum(o["share_fraction"] for o in kh["owners"])
        assert abs(total_share - 1.0) < 0.05
        
    scen_type = SCENARIO_TYPES[0]
    scen, txns, muts, taxes = create_scenario(scen_type, parcels[0], owners, rng)
    assert len(txns) >= 2
    assert len(muts) == len(txns)
    assert len(taxes) == len(txns)
