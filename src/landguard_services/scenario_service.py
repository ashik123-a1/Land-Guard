"""Synthetic Scenario Service
Provides seeded, reproducible generation of synthetic land dispute scenarios
across all 15 defined fraud and legitimate benchmark classes.

Non-Negotiable Constraints:
- 100% reproducible with deterministic random seed.
- ZERO writes to live operational registry database.
- Explicit synthetic legal disclaimer on all generated records.
"""

import random
from typing import Dict, Any, List, Optional
from src.landguard_data.generate_scenarios import ALL_SCENARIO_TYPES, create_scenario


SYNTHETIC_DISCLAIMER = (
    "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT. All records, names, plots, and seals "
    "are synthetically generated for research, benchmark evaluation, and training purposes."
)


class ScenarioService:
    """Domain service managing seeded synthetic scenario catalog and deterministic generation."""

    def __init__(self, db=None):
        self.db = db

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Returns catalog of all available reproducible scenario archetypes."""
        catalog = []
        for code, is_fraud, desc in ALL_SCENARIO_TYPES:
            catalog.append({
                "scenario_type": code,
                "is_fraud_risk": is_fraud,
                "classification": "FRAUD_DISCREPANCY" if is_fraud else "LEGITIMATE_CONTROL",
                "description": desc,
            })
        return catalog

    def generate_reproducible_scenario(
        self,
        scenario_type: str,
        seed: Optional[int] = 42,
    ) -> Dict[str, Any]:
        """Deterministically generates a complete synthetic scenario including deed, parcel, ownership history, and document evidence."""
        # Find matching scenario archetype
        match = None
        for item in ALL_SCENARIO_TYPES:
            if item[0].upper() == scenario_type.upper():
                match = item
                break

        if not match:
            valid_types = [t[0] for t in ALL_SCENARIO_TYPES]
            raise ValueError(f"Unknown scenario type '{scenario_type}'. Valid types: {valid_types[:5]}...")

        actual_seed = seed if seed is not None else 42
        rng = random.Random(actual_seed)

        # Baseline synthetic parcel definition
        synthetic_parcel = {
            "parcel_id": "PCL-SYNTH-9044",
            "dag_plot_number": 9044,
            "khatian_number": "1420",
            "mouza": "Dakshin Khan",
            "jl_number": "18",
            "upazila": "Uttara",
            "district": "Dhaka",
            "division": "Dhaka",
            "total_area_decimal": 12.50,
            "recorded_land_class": "Nal",
        }

        # Baseline synthetic owners pool
        synthetic_owners = [
            {"owner_id": "OWN-001", "name": "Abdul Latif Mia", "national_id": "19602691234567890", "address": "Savar, Dhaka"},
            {"owner_id": "OWN-002", "name": "Rokeya Begum", "national_id": "19652691234567891", "address": "Savar, Dhaka"},
            {"owner_id": "OWN-003", "name": "Anisur Rahman", "national_id": "19852691234567892", "address": "Dhanmondi, Dhaka"},
            {"owner_id": "OWN-004", "name": "Farhana Sultana", "national_id": "19902691234567893", "address": "Uttara, Dhaka"},
        ]

        scenario_meta, all_txns, mutations, tax_receipts = create_scenario(
            scenario_type_info=match,
            parcel=synthetic_parcel,
            owners_pool=synthetic_owners,
            rng=rng,
        )

        target_txn = all_txns[-1] if all_txns else {}

        return {
            "scenario_id": scenario_meta.get("scenario_id", f"SCN-SEED-{actual_seed}"),
            "scenario_type": match[0],
            "ground_truth_label": "FRAUD_RISK" if match[1] else "LEGITIMATE",
            "is_fraud_risk": match[1],
            "description": match[2],
            "seed_used": actual_seed,
            "disclaimer": SYNTHETIC_DISCLAIMER,
            "scenario_meta": scenario_meta,
            "document_evidence": scenario_meta.get("document_evidence", {}),
            "target_transaction": target_txn,
            "ownership_history_chain": all_txns,
            "mutations": mutations,
            "tax_receipts": tax_receipts,
            "parcel_metadata": synthetic_parcel,
            "zero_operational_db_writes": True,
        }
