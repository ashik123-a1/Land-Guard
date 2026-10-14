"""Validates dataset integrity, schema compliance, and cross-record consistency."""

import json
import os
from typing import List, Dict, Any, Tuple
import jsonschema


def load_schema(schema_path: str) -> dict:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(record: dict, schema: dict) -> Tuple[bool, str]:
    try:
        jsonschema.validate(instance=record, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, str(e.message)


def validate_referential_integrity(
    owners: List[dict],
    parcels: List[dict],
    transactions: List[dict],
    records: List[dict]
) -> Dict[str, Any]:
    owner_ids = {o["owner_id"] for o in owners}
    parcel_ids = {p["parcel_id"] for p in parcels}
    
    missing_parcels_in_txn = []
    missing_sellers_in_txn = []
    missing_parcels_in_rec = []
    
    for txn in transactions:
        if txn["parcel_id"] not in parcel_ids:
            missing_parcels_in_txn.append(txn["transaction_id"])
        for s in txn["seller_ids"]:
            if s not in owner_ids:
                missing_sellers_in_txn.append(s)
                
    for rec in records:
        if rec["parcel_id"] not in parcel_ids:
            missing_parcels_in_rec.append(rec["record_id"])
            
    is_valid = (
        len(missing_parcels_in_txn) == 0 and
        len(missing_sellers_in_txn) == 0 and
        len(missing_parcels_in_rec) == 0
    )
    
    return {
        "is_valid": is_valid,
        "total_owners": len(owners),
        "total_parcels": len(parcels),
        "total_transactions": len(transactions),
        "total_records": len(records),
        "missing_parcels_in_txn": len(missing_parcels_in_txn),
        "missing_sellers_in_txn": len(missing_sellers_in_txn),
        "missing_parcels_in_rec": len(missing_parcels_in_rec)
    }
