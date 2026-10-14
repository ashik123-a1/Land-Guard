"""Generates synthetic registered deeds and transactions."""

import random
import uuid
import datetime
from typing import List, Dict, Any

DEED_TYPES = [
    "Sale Deed (Kabala)",
    "Heirship Transfer (Waris)",
    "Gift (Heba)",
    "Exchange",
    "Mortgage"
]


def generate_transaction(
    parcel: Dict[str, Any],
    seller: Dict[str, Any],
    buyer: Dict[str, Any],
    execution_date: datetime.date,
    previous_deed_ref: str,
    scenario_id: str,
    rng: random.Random,
    area: float = None,
    deed_type: str = "Sale Deed (Kabala)"
) -> Dict[str, Any]:
    uid = uuid.UUID(int=rng.getrandbits(128)).hex[:8].upper()
    yr = execution_date.year
    deed_seq = rng.randint(1000, 99999)
    deed_num = f"DEED-{yr}-{deed_seq}"
    
    if area is None:
        area = min(parcel["total_area_decimal"], round(rng.uniform(1.0, parcel["total_area_decimal"]), 2))
        
    rate_per_dec = rng.uniform(80000, 450000)
    consideration = round(area * rate_per_dec, -3)
    mutation_case = f"MUT-{yr}-{rng.randint(100, 9999)}/{parcel['upazila']}"
    
    return {
        "transaction_id": f"TXN-{uid}",
        "deed_number": deed_num,
        "deed_type": deed_type,
        "execution_date": execution_date.isoformat(),
        "registration_sub_office": f"{parcel['upazila']} Sub-Registry Office, {parcel['district']}",
        "seller_ids": [seller["owner_id"]],
        "buyer_ids": [buyer["owner_id"]],
        "parcel_id": parcel["parcel_id"],
        "transferred_area_decimal": area,
        "consideration_bdt": consideration,
        "previous_deed_ref": previous_deed_ref or "INHERITED_ANCESTRAL_CS_RECORD",
        "mutation_case_no": mutation_case,
        "tax_clearance_year": yr,
        "scenario_id": scenario_id,
        "is_synthetic": True
    }
