"""Generates controlled experimental scenarios with realistic multi-feature variation and strict separation of:
1. Ground-truth scenario label (is_fraud_risk, ground_truth_label)
2. Observable evidence available to the system (structured registry records + separate document_evidence)
3. Hidden simulator metadata (simulator_audit_metadata, never passed to models or rules)
"""

import random
import uuid
import datetime
from typing import List, Dict, Any, Tuple
from .generate_ownership_histories import build_ownership_history_for_parcel

SCENARIO_TYPES = [
    # Legitimate classes (is_fraud_risk = False)
    ("LEGITIMATE_NORMAL_SALE", False, "Legitimate conveyance with unbroken chain and verified or pending mutation"),
    ("LEGITIMATE_INHERITANCE", False, "Valid ancestral heirship distribution under succession law"),
    ("LEGITIMATE_PARTIAL_SUBDIVISION", False, "Valid partial transfer of portion of plot within total capacity"),
    ("LEGITIMATE_CORRECTION_DEED", False, "Legitimate rectification deed amending minor typographical detail"),

    # Fraud Risk / Discrepancy classes (is_fraud_risk = True)
    ("ALTERED_PLOT_NUMBER", True, "Deed schedule cites plot number conflicting with underlying cadastral khatian"),
    ("ALTERED_OWNER_NAME", True, "Seller in deed is not recorded titleholder in land records"),
    ("EXAGGERATED_LAND_AREA", True, "Transferred or cumulative area exceeds recorded parcel capacity"),
    ("BROKEN_CHAIN_OF_TITLE", True, "Previous deed reference does not link to valid preceding conveyance"),
    ("CONFLICTING_DOUBLE_SALE", True, "Seller conveys same plot share to second buyer after prior transfer"),
    ("UNREGISTERED_MUTATION_MISMATCH", True, "Mutation reference fabricated or rejected by land office"),
    ("SYNTHETIC_SEAL_ABSENT_SUSPICIOUS", True, "Mandatory sub-registry authentication seal missing with irregular execution"),
    ("VISUAL_OVERLAY_TAMPERING", True, "Document contains mechanical paste-over or numerical splice"),
]

TARGETED_SCENARIO_TYPES = [
    # Difficult but legitimate title-chain and mutation scenarios
    ("LEGITIMATE_LONG_CHAIN_PENDING_MUTATION", False, "5-link legitimate title chain with recent bona fide purchase awaiting Namzari mutation hearing"),
    ("LEGITIMATE_MULTI_HEIR_PARTITION", False, "Complex ancestral chain with multiple heirs where cumulative partial transfers strictly equal parcel capacity"),
    ("LEGITIMATE_INITIALED_CORRECTION_DEED", False, "Legitimate clerical correction deed with Sub-Registrar initials amending typographical error"),
    ("AMBIGUOUS_UNTRACED_PRE1972_DEED", False, "Pre-1972 ancestral conveyance where archival index is damaged or unindexed (MISSING_EVIDENCE)"),

    # Unseen combinations of compound fraud indicators
    ("COMPOUND_DOUBLE_SALE_AND_ALTERED_PLOT", True, "Seller conveys same plot share twice while simultaneously altering plot number on deed schedule"),
    ("COMPOUND_FABRICATED_MUTATION_AND_AREA_EXCESS", True, "Fabricated mutation citing fictitious case accompanied by 160% area conveyance"),
    ("COMPOUND_IMPOSTER_AND_TAMPERED_DEED", True, "Non-titleholder imposter with mechanical paste-over alteration and missing official seal"),
]

ALL_SCENARIO_TYPES = SCENARIO_TYPES + TARGETED_SCENARIO_TYPES


def create_scenario(
    scenario_type_info: tuple,
    parcel: Dict[str, Any],
    owners_pool: List[Dict[str, Any]],
    rng: random.Random
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    scen_cat, is_fraud, desc = scenario_type_info
    uid = uuid.UUID(int=rng.getrandbits(128)).hex[:8].upper()
    scen_id = f"SCN-{uid}"

    injected_mods: List[str] = []
    expected_violations: List[str] = []

    # Base chronological ownership history (2 to 4 links)
    txns, mutations, tax_receipts = build_ownership_history_for_parcel(
        parcel=parcel,
        owners_pool=owners_pool,
        scenario_id=scen_id,
        chain_length=rng.randint(2, 4),
        rng=rng
    )

    target_txn = txns[-1]
    p_area = float(parcel["total_area_decimal"])
    exec_year = int(str(target_txn["execution_date"])[:4])

    # Default realistic market consideration per decimal (~95k to 145k BDT)
    market_rate = rng.uniform(95000.0, 145000.0)
    base_share = rng.uniform(0.55, 1.00)
    target_txn["transferred_area_decimal"] = round(p_area * base_share, 2)
    target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * market_rate, 2)

    # Default observable document evidence (derived when OCR/CV inspects the physical deed)
    doc_evidence: Dict[str, Any] = {
        "doc_dag_plot_number": int(parcel["dag_plot_number"]),
        "doc_transferred_area_decimal": float(target_txn["transferred_area_decimal"]),
        "cv_seal_present": True,
        "cv_signature_present": True,
        "cv_visual_anomaly_detected": False,
        "cv_visual_anomaly_score": round(rng.uniform(0.01, 0.18), 3),
        "ocr_confidence": round(rng.uniform(0.86, 0.98), 3),
    }

    # =========================================================================
    # A. LEGITIMATE SCENARIO FAMILIES (Varied, non-constant operational vectors)
    # =========================================================================
    if scen_cat == "LEGITIMATE_NORMAL_SALE":
        # 12% have 1-2 year minor tax payment lag
        if rng.random() < 0.12:
            lag = rng.randint(1, 2)
            target_txn["tax_clearance_year"] = exec_year - lag
            injected_mods.append(f"Benign tax lag of {lag} yr(s)")
        # 8% are recent deeds with pending Namzari mutation
        if rng.random() < 0.08 and mutations:
            mutations[-1]["status"] = "PENDING"
            injected_mods.append("Recent legitimate sale with PENDING mutation")

    elif scen_cat == "LEGITIMATE_INHERITANCE":
        target_txn["deed_type"] = "Inheritance Partition (Warishnama)"
        if rng.random() < 0.65:
            target_txn["previous_deed_ref"] = "INHERITED_ANCESTRAL_CS_RECORD"
        heir_share = rng.uniform(0.20, 0.65)
        target_txn["transferred_area_decimal"] = round(p_area * heir_share, 2)
        target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(40000.0, 90000.0), 2)
        doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
        if rng.random() < 0.18:
            target_txn["tax_clearance_year"] = exec_year - rng.randint(1, 3)
            injected_mods.append("Ancestral multi-year tax lag")
        if rng.random() < 0.15 and mutations:
            mutations[-1]["status"] = "PENDING"
            injected_mods.append("Succession mutation currently PENDING")
        # 6% of old family partition memoranda lack a sub-registrar seal (requiring review, not fraud)
        if rng.random() < 0.06:
            doc_evidence["cv_seal_present"] = False
            injected_mods.append("Informal family partition memo without sub-registry seal")

    elif scen_cat == "LEGITIMATE_PARTIAL_SUBDIVISION":
        # Valid partial transfer within total capacity
        sub_share = rng.uniform(0.20, 0.45)
        target_txn["transferred_area_decimal"] = round(p_area * sub_share, 2)
        target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * market_rate, 2)
        doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
        # In 25% of cases, the current seller previously sold ANOTHER valid partial portion (sum <= p_area)
        if len(txns) >= 3 and rng.random() < 0.25:
            current_seller = target_txn["seller_ids"][0]
            txns[-2]["seller_ids"] = [current_seller]
            txns[-2]["transferred_area_decimal"] = round(p_area * rng.uniform(0.20, 0.40), 2)
            # Ensure current_seller acquired the parcel in txns[-3]
            txns[-3]["buyer_ids"] = [current_seller]
            injected_mods.append("Seller executed prior partial subdivision within total parcel capacity")
        if rng.random() < 0.10:
            target_txn["tax_clearance_year"] = exec_year - 1

    elif scen_cat == "LEGITIMATE_CORRECTION_DEED":
        target_txn["deed_type"] = "Correction Deed (Bhul-Sanshodhon)"
        target_txn["transferred_area_decimal"] = round(p_area * rng.uniform(0.40, 0.90), 2)
        # Rectification deeds often carry nominal/administrative consideration
        target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(25000.0, 65000.0), 2)
        doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
        if rng.random() < 0.15 and mutations:
            mutations[-1]["status"] = "PENDING"
            injected_mods.append("Rectification deed awaiting mutation update")
        # 8% of correction deeds have marginal clerical strikeover or OCR digit blur
        if rng.random() < 0.08:
            doc_evidence["cv_visual_anomaly_detected"] = True
            doc_evidence["cv_visual_anomaly_score"] = round(rng.uniform(0.38, 0.55), 3)
            injected_mods.append("Initialed clerical correction mark on deed")

    # =========================================================================
    # B. FRAUD-RISK SCENARIO FAMILIES (Multi-feature patterns, zero oracle flags on txn)
    # =========================================================================
    elif scen_cat == "ALTERED_PLOT_NUMBER":
        fake_plot = int(parcel["dag_plot_number"]) + rng.randint(50, 500)
        injected_mods.append(f"Plot altered on deed schedule from {parcel['dag_plot_number']} to {fake_plot}")
        expected_violations.append("RULE_PLOT_MISMATCH_WITH_KHATIAN")
        # Observable in document_evidence (OCR on deed), NOT as a hidden flag on registry txn!
        doc_evidence["doc_dag_plot_number"] = fake_plot
        # 42% also exhibit secondary registry risk signals (unverified mutation, tax arrears, price discount)
        if rng.random() < 0.42:
            if rng.random() < 0.65 and mutations:
                mutations.pop()
                injected_mods.append("Unverified mutation accompanying plot mismatch")
            target_txn["tax_clearance_year"] = exec_year - rng.randint(2, 5)
            target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(45000.0, 72000.0), 2)

    elif scen_cat == "ALTERED_OWNER_NAME":
        imposter = rng.choice([o for o in owners_pool if o["owner_id"] not in target_txn["seller_ids"]])
        target_txn["seller_ids"] = [imposter["owner_id"]]
        injected_mods.append(f"Seller substituted with non-titleholder {imposter['owner_id']}")
        expected_violations.append("RULE_SELLER_NOT_TITLEHOLDER")
        # 45% also have missing/rejected mutation or fire-sale consideration
        if rng.random() < 0.45:
            if mutations and rng.random() < 0.70:
                mutations[-1]["status"] = "REJECTED"
                injected_mods.append("Mutation rejected due to seller title mismatch")
            target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(38000.0, 68000.0), 2)
            target_txn["tax_clearance_year"] = exec_year - rng.randint(1, 4)

    elif scen_cat == "EXAGGERATED_LAND_AREA":
        inflated_area = round(p_area * rng.uniform(1.15, 2.45), 2)
        injected_mods.append(f"Transferred area inflated from {p_area} to {inflated_area}")
        expected_violations.append("RULE_AREA_EXCEEDS_CAPACITY")
        target_txn["transferred_area_decimal"] = inflated_area
        doc_evidence["doc_transferred_area_decimal"] = inflated_area
        target_txn["consideration_bdt"] = round(inflated_area * rng.uniform(60000.0, 110000.0), 2)
        if rng.random() < 0.35 and mutations:
            mutations.pop()
            injected_mods.append("No verified mutation for exaggerated area transfer")
        if rng.random() < 0.30:
            target_txn["tax_clearance_year"] = exec_year - rng.randint(2, 4)

    elif scen_cat == "BROKEN_CHAIN_OF_TITLE":
        bogus_ref = f"DEED-{rng.randint(1985, 2012)}-{rng.randint(10000, 89999)}"
        injected_mods.append(f"Unverifiable ancestor deed {bogus_ref} referenced")
        expected_violations.append("RULE_BROKEN_CHAIN_OF_TITLE")
        target_txn["previous_deed_ref"] = bogus_ref
        if rng.random() < 0.40 and mutations:
            mutations.pop()
            injected_mods.append("Unverified mutation accompanying broken chain")
        if rng.random() < 0.35:
            target_txn["tax_clearance_year"] = exec_year - rng.randint(2, 6)

    elif scen_cat == "CONFLICTING_DOUBLE_SALE":
        # Seller conveys share that pushes cumulative seller disposition > 100% of parcel capacity
        if len(txns) >= 2:
            prior_seller = txns[-2]["seller_ids"][0]
            second_buyer = rng.choice([
                o for o in owners_pool
                if o["owner_id"] != prior_seller and o["owner_id"] not in txns[-2]["buyer_ids"]
            ])
            txns[-2]["transferred_area_decimal"] = round(p_area * rng.uniform(0.75, 1.00), 2)
            target_txn["seller_ids"] = [prior_seller]
            target_txn["buyer_ids"] = [second_buyer["owner_id"]]
            target_txn["transferred_area_decimal"] = round(p_area * rng.uniform(0.75, 1.00), 2)
            doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
            injected_mods.append(f"Conflicting double sale by seller {prior_seller} to {second_buyer['owner_id']}")
        expected_violations.append("RULE_CONFLICTING_DOUBLE_DISPOSITION")
        if rng.random() < 0.40 and mutations:
            mutations[-1]["status"] = "REJECTED"
        if rng.random() < 0.30:
            target_txn["tax_clearance_year"] = exec_year - rng.randint(1, 4)

    elif scen_cat == "UNREGISTERED_MUTATION_MISMATCH":
        fake_mut = f"MUT-{exec_year}-{rng.randint(1000, 9999)}/{parcel['upazila']}"
        injected_mods.append(f"Fabricated mutation reference {fake_mut}")
        expected_violations.append("RULE_UNVERIFIED_MUTATION_RECORD")
        target_txn["mutation_case_no"] = fake_mut
        mutations = [m for m in mutations if m.get("mutation_case_no") != fake_mut]
        if rng.random() < 0.45:
            target_txn["tax_clearance_year"] = exec_year - rng.randint(2, 6)
            target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(42000.0, 75000.0), 2)

    elif scen_cat == "SYNTHETIC_SEAL_ABSENT_SUSPICIOUS":
        injected_mods.append("Authentication registrar seal absent on deed document")
        expected_violations.append("RULE_MANDATORY_REGISTRAR_SEAL_ABSENT")
        doc_evidence["cv_seal_present"] = False
        if rng.random() < 0.30:
            doc_evidence["cv_signature_present"] = False
        # 40% also exhibit registry-level irregularities (missing mutation, tax arrears, discounted consideration)
        if rng.random() < 0.40:
            if mutations and rng.random() < 0.75:
                mutations.pop()
                injected_mods.append("Unregistered deed lacking both seal and mutation")
            target_txn["tax_clearance_year"] = exec_year - rng.randint(2, 5)
            target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(40000.0, 70000.0), 2)

    elif scen_cat == "VISUAL_OVERLAY_TAMPERING":
        injected_mods.append("Mechanical paste-over splice on deed document")
        expected_violations.append("RULE_VISUAL_TAMPERING_DETECTED")
        doc_evidence["cv_visual_anomaly_detected"] = True
        doc_evidence["cv_visual_anomaly_score"] = round(rng.uniform(0.72, 0.96), 3)
        # 50% of paste-over alterations modify the document's printed area or plot number relative to registry
        if rng.random() < 0.50:
            doc_evidence["doc_transferred_area_decimal"] = round(target_txn["transferred_area_decimal"] * rng.uniform(1.35, 1.95), 2)
            injected_mods.append("Paste-over inflates document area vs registry record")
        # 38% also show registry-level anomalies
        if rng.random() < 0.38:
            if mutations and rng.random() < 0.65:
                mutations.pop()
            target_txn["tax_clearance_year"] = exec_year - rng.randint(2, 5)
            target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(45000.0, 74000.0), 2)

    # =========================================================================
    # C. TARGETED EXPANSION SCENARIO FAMILIES
    # =========================================================================
    elif scen_cat == "LEGITIMATE_LONG_CHAIN_PENDING_MUTATION":
        # 5-link title chain with recent bona fide purchase awaiting Namzari mutation hearing
        txns_ext, muts_ext, tax_ext = build_ownership_history_for_parcel(
            parcel=parcel,
            owners_pool=owners_pool,
            scenario_id=scen_id,
            chain_length=5,
            rng=rng
        )
        txns = txns_ext
        mutations = muts_ext
        tax_receipts = tax_ext
        target_txn = txns[-1]
        target_txn["seller_ids"] = [txns[-2]["buyer_ids"][0]]
        target_txn["transferred_area_decimal"] = round(p_area * rng.uniform(0.60, 0.95), 2)
        target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * market_rate, 2)
        doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
        if mutations:
            mutations[-1]["status"] = "PENDING"
        target_txn["tax_clearance_year"] = exec_year - 1
        injected_mods.append("5-link legitimate title chain with recent purchase awaiting Namzari mutation")
        expected_violations.append("RULE_MUTATION_PENDING_REVIEW")

    elif scen_cat == "LEGITIMATE_MULTI_HEIR_PARTITION":
        # Complex ancestral chain with multiple heirs where cumulative partial transfers strictly equal parcel capacity
        target_txn["deed_type"] = "Inheritance Partition (Warishnama)"
        target_txn["previous_deed_ref"] = "INHERITED_ANCESTRAL_CS_RECORD"
        share = round(p_area * 0.25, 2)
        target_txn["transferred_area_decimal"] = share
        target_txn["consideration_bdt"] = round(share * rng.uniform(50000.0, 85000.0), 2)
        doc_evidence["doc_transferred_area_decimal"] = share
        if len(txns) >= 2:
            current_seller = target_txn["seller_ids"][0]
            txns[-2]["seller_ids"] = [current_seller]
            txns[-2]["transferred_area_decimal"] = round(p_area * 0.50, 2)
        injected_mods.append("Valid multi-heir partition where cumulative shares equal parcel capacity")
        expected_violations.append("RULE_PARTIAL_SUBDIVISION_CAPACITY_CHECK")

    elif scen_cat == "LEGITIMATE_INITIALED_CORRECTION_DEED":
        target_txn["deed_type"] = "Correction Deed (Bhul-Sanshodhon)"
        target_txn["transferred_area_decimal"] = round(p_area * rng.uniform(0.50, 0.85), 2)
        target_txn["consideration_bdt"] = round(target_txn["transferred_area_decimal"] * rng.uniform(30000.0, 60000.0), 2)
        doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
        doc_evidence["cv_visual_anomaly_detected"] = True
        doc_evidence["cv_visual_anomaly_score"] = round(rng.uniform(0.38, 0.50), 3)
        doc_evidence["cv_seal_present"] = True
        injected_mods.append("Clerical strikeover initialed by Sub-Registrar on rectification deed")
        expected_violations.append("RULE_VISUAL_TAMPERING_DETECTED")

    elif scen_cat == "AMBIGUOUS_UNTRACED_PRE1972_DEED":
        untraced_ref = f"UNINDEXED_PRE1972_VOLUME_{rng.randint(100, 999)}"
        target_txn["previous_deed_ref"] = untraced_ref
        injected_mods.append(f"Pre-1972 ancestral conveyance cited where archive index is unindexed/damaged: {untraced_ref}")
        expected_violations.append("RULE_BROKEN_CHAIN_OF_TITLE")

    elif scen_cat == "COMPOUND_DOUBLE_SALE_AND_ALTERED_PLOT":
        if len(txns) >= 2:
            prior_seller = txns[-2]["seller_ids"][0]
            second_buyer = rng.choice([o for o in owners_pool if o["owner_id"] != prior_seller and o["owner_id"] not in txns[-2]["buyer_ids"]])
            txns[-2]["transferred_area_decimal"] = round(p_area * 0.80, 2)
            target_txn["seller_ids"] = [prior_seller]
            target_txn["buyer_ids"] = [second_buyer["owner_id"]]
            target_txn["transferred_area_decimal"] = round(p_area * 0.80, 2)
            doc_evidence["doc_transferred_area_decimal"] = target_txn["transferred_area_decimal"]
        fake_plot = int(parcel["dag_plot_number"]) + rng.randint(50, 400)
        doc_evidence["doc_dag_plot_number"] = fake_plot
        injected_mods.append("Compound fraud: Conflicting double sale combined with altered plot number on deed")
        expected_violations.extend(["RULE_CONFLICTING_DOUBLE_DISPOSITION", "RULE_PLOT_MISMATCH_WITH_KHATIAN"])

    elif scen_cat == "COMPOUND_FABRICATED_MUTATION_AND_AREA_EXCESS":
        inflated_area = round(p_area * rng.uniform(1.40, 2.10), 2)
        target_txn["transferred_area_decimal"] = inflated_area
        doc_evidence["doc_transferred_area_decimal"] = inflated_area
        fake_mut = f"MUT-{exec_year}-{rng.randint(1000, 9999)}/{parcel['upazila']}"
        target_txn["mutation_case_no"] = fake_mut
        mutations = [m for m in mutations if m.get("mutation_case_no") != fake_mut]
        injected_mods.append("Compound fraud: Exaggerated area transfer accompanied by fabricated mutation citation")
        expected_violations.extend(["RULE_AREA_EXCEEDS_CAPACITY", "RULE_UNVERIFIED_MUTATION_RECORD"])

    elif scen_cat == "COMPOUND_IMPOSTER_AND_TAMPERED_DEED":
        imposter = rng.choice([o for o in owners_pool if o["owner_id"] not in target_txn["seller_ids"]])
        target_txn["seller_ids"] = [imposter["owner_id"]]
        doc_evidence["cv_seal_present"] = False
        doc_evidence["cv_visual_anomaly_detected"] = True
        doc_evidence["cv_visual_anomaly_score"] = round(rng.uniform(0.88, 0.98), 3)
        injected_mods.append("Compound fraud: Imposter seller with physical paste-over alteration and missing registrar seal")
        expected_violations.extend(["RULE_SELLER_NOT_TITLEHOLDER", "RULE_MANDATORY_REGISTRAR_SEAL_ABSENT", "RULE_VISUAL_TAMPERING_DETECTED"])

    scenario = {
        "scenario_id": scen_id,
        "scenario_category": scen_cat,
        "is_fraud_risk": is_fraud,
        "description": desc,
        "document_evidence": doc_evidence,
        "simulator_audit_metadata": {
            "scenario_id": scen_id,
            "scenario_category": scen_cat,
            "injected_modifications": injected_mods,
            "expected_rule_violations": expected_violations,
        },
        "ground_truth_label": "FRAUD_RISK" if is_fraud else "LEGITIMATE",
    }

    return scenario, txns, mutations, tax_receipts
