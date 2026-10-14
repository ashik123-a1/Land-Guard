"""Generates chronological ownership histories and chains of title."""

import random
import datetime
from typing import List, Dict, Any, Tuple
from .generate_transactions import generate_transaction


def build_ownership_history_for_parcel(
    parcel: Dict[str, Any],
    owners_pool: List[Dict[str, Any]],
    scenario_id: str,
    chain_length: int,
    rng: random.Random
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Creates a legitimate chain of title:
    Ancestor -> Transfer 1 -> Transfer 2 -> Current Owner.
    Returns (transactions, mutation_records, tax_receipts)
    """
    transactions = []
    mutations = []
    tax_receipts = []
    
    current_year = 1995
    prev_deed_ref = ""
    current_seller = rng.choice(owners_pool)
    
    for i in range(chain_length):
        buyer = rng.choice([o for o in owners_pool if o["owner_id"] != current_seller["owner_id"]])
        step_year = current_year + rng.randint(4, 8)
        current_year = min(step_year, 2024)
        
        exec_date = datetime.date(current_year, rng.randint(1, 12), rng.randint(1, 28))
        txn = generate_transaction(
            parcel=parcel,
            seller=current_seller,
            buyer=buyer,
            execution_date=exec_date,
            previous_deed_ref=prev_deed_ref,
            scenario_id=scenario_id,
            rng=rng,
            area=parcel["total_area_decimal"]
        )
        transactions.append(txn)
        prev_deed_ref = txn["deed_number"]
        
        # Mutation order record
        mut_date = exec_date + datetime.timedelta(days=rng.randint(30, 180))
        mut_record = {
            "mutation_id": f"MUTREC-{txn['transaction_id'][4:]}",
            "mutation_case_no": txn["mutation_case_no"],
            "parcel_id": parcel["parcel_id"],
            "previous_owner_id": current_seller["owner_id"],
            "new_owner_id": buyer["owner_id"],
            "khatian_type": "BS (Namzari)",
            "effective_date": mut_date.isoformat(),
            "status": "APPROVED",
            "scenario_id": scenario_id,
            "is_synthetic": True
        }
        mutations.append(mut_record)
        
        # Annual tax receipt
        tax_rec = {
            "receipt_id": f"TAX-{txn['transaction_id'][4:]}",
            "receipt_no": f"DCL-{current_year}-{rng.randint(10000, 99999)}",
            "parcel_id": parcel["parcel_id"],
            "owner_id": buyer["owner_id"],
            "tax_year": current_year,
            "assessed_bdt": round(parcel["total_area_decimal"] * 25.0, 2),
            "paid_bdt": round(parcel["total_area_decimal"] * 25.0, 2),
            "payment_status": "PAID",
            "scenario_id": scenario_id,
            "is_synthetic": True
        }
        tax_receipts.append(tax_rec)
        
        current_seller = buyer
        
    return transactions, mutations, tax_receipts
