"""Tests multi-template image rendering across all 6 document categories."""

import random
from src.landguard_data.generate_entities import generate_entities
from src.landguard_data.generate_records import generate_records_for_parcels
from src.landguard_data.generate_scenarios import create_scenario, SCENARIO_TYPES
from src.landguard_data.generate_documents import (
    build_sale_deed_document, build_khatian_document, build_mutation_document,
    build_tax_receipt_document, build_parcel_map_document, build_application_document
)
from src.landguard_data.render_documents import render_document


def test_render_all_six_categories():
    rng = random.Random(42)
    owners, parcels = generate_entities(count_owners=5, count_parcels=2, seed=42)
    owners_map = {o["owner_id"]: o for o in owners}
    khatians = generate_records_for_parcels(parcels, owners, rng)
    scen, txns, muts, taxes = create_scenario(SCENARIO_TYPES[0], parcels[0], owners, rng)
    
    docs = [
        build_sale_deed_document(txns[0], parcels[0], owners[0], owners[1], "TMPL-DEED-01"),
        build_khatian_document(khatians[0], parcels[0], owners_map, "TMPL-KH-01"),
        build_mutation_document(muts[0], parcels[0], owners[0], owners[1], "TMPL-MUT-01"),
        build_tax_receipt_document(taxes[0], parcels[0], owners[0], "TMPL-TAX-01"),
        build_parcel_map_document(parcels[0], "TMPL-MAP-01"),
        build_application_document(parcels[0], owners[0], "TMPL-APP-01")
    ]
    
    for doc in docs:
        img, full_text, bboxes, has_sig, has_seal = render_document(doc)
        assert img is not None
        assert img.size[0] > 500 and img.size[1] > 500
        assert len(full_text) > 10
        assert isinstance(bboxes, dict)
