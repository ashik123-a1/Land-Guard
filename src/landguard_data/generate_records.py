"""Generates synthetic Khatian / Porcha land records across survey periods."""

import random
import uuid
from typing import List, Dict, Any

SURVEY_TYPES = [
    ("CS", 1935, 1945),
    ("SA", 1956, 1965),
    ("RS", 1978, 1990),
    ("BS", 1998, 2018)
]


def generate_khatian_record(
    parcel: Dict[str, Any],
    owners: List[Dict[str, Any]],
    survey_info: tuple,
    khatian_no: int,
    rng: random.Random
) -> Dict[str, Any]:
    stype, start_yr, end_yr = survey_info
    uid = uuid.UUID(int=rng.getrandbits(128)).hex[:8].upper()
    eff_year = rng.randint(start_yr, end_yr)
    
    # Generate proportional shares summing to 1.0
    num_owners = min(len(owners), rng.randint(1, 3))
    selected_owners = rng.sample(owners, num_owners)
    
    raw_shares = [rng.uniform(0.1, 1.0) for _ in range(num_owners)]
    tot = sum(raw_shares)
    shares = [round(s / tot, 4) for s in raw_shares]
    diff = round(1.0 - sum(shares), 4)
    shares[0] = round(shares[0] + diff, 4)
    
    owner_entries = [
        {"owner_id": selected_owners[i]["owner_id"], "share_fraction": shares[i]}
        for i in range(num_owners)
    ]
    
    return {
        "record_id": f"REC-{uid}",
        "khatian_type": stype,
        "khatian_number": khatian_no,
        "parcel_id": parcel["parcel_id"],
        "owners": owner_entries,
        "effective_year": eff_year,
        "status": "ACTIVE" if stype == "BS" else "SUPERSEDED",
        "is_synthetic": True
    }


def generate_records_for_parcels(
    parcels: List[Dict[str, Any]],
    owners: List[Dict[str, Any]],
    rng: random.Random
) -> List[Dict[str, Any]]:
    records = []
    khatian_counter = 1001
    
    for parcel in parcels:
        # Each parcel gets historical records: CS, SA, RS, BS
        for survey in SURVEY_TYPES:
            rec = generate_khatian_record(parcel, owners, survey, khatian_counter, rng)
            records.append(rec)
            khatian_counter += 1
            
    return records
