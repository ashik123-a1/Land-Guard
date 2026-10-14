"""Builds grouped, leakage-free train, validation, and test splits."""

import random
from typing import List, Dict, Any, Tuple


def assign_grouped_splits(
    items: List[Dict[str, Any]],
    group_key: str = "scenario_id",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups items by group_key (e.g. scenario_id or parcel_id) so that no
    scenario or related variants leak across train/val/test splits.
    """
    rng = random.Random(seed)
    
    # Collect all unique groups
    groups = {}
    for item in items:
        grp = item.get(group_key) or item.get("source_document_id") or "UNGROUPED"
        if grp not in groups:
            groups[grp] = []
        groups[grp].append(item)
        
    unique_groups = list(groups.keys())
    rng.shuffle(unique_groups)
    
    n_total = len(unique_groups)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    
    train_groups = set(unique_groups[:n_train])
    val_groups = set(unique_groups[n_train:n_train + n_val])
    test_groups = set(unique_groups[n_train + n_val:])
    
    splits = {"train": [], "val": [], "test": []}
    
    for grp, grp_items in groups.items():
        if grp in train_groups:
            target = "train"
        elif grp in val_groups:
            target = "val"
        else:
            target = "test"
            
        for item in grp_items:
            item["split_assignment"] = target
            splits[target].append(item)
            
    return splits


def verify_leakage_free(splits: Dict[str, List[Dict[str, Any]]], group_key: str = "scenario_id") -> Dict[str, Any]:
    """Verifies that no groups or documents overlap between splits."""
    train_groups = {item.get(group_key) for item in splits["train"] if item.get(group_key)}
    val_groups = {item.get(group_key) for item in splits["val"] if item.get(group_key)}
    test_groups = {item.get(group_key) for item in splits["test"] if item.get(group_key)}
    
    train_val_overlap = train_groups.intersection(val_groups)
    train_test_overlap = train_groups.intersection(test_groups)
    val_test_overlap = val_groups.intersection(test_groups)
    
    # Document ID check
    train_docs = {item.get("source_document_id") for item in splits["train"] if item.get("source_document_id")}
    test_docs = {item.get("source_document_id") for item in splits["test"] if item.get("source_document_id")}
    doc_overlap = train_docs.intersection(test_docs)
    
    is_clean = len(train_val_overlap) == 0 and len(train_test_overlap) == 0 and len(val_test_overlap) == 0 and len(doc_overlap) == 0
    
    return {
        "is_leakage_free": is_clean,
        "train_count": len(splits["train"]),
        "val_count": len(splits["val"]),
        "test_count": len(splits["test"]),
        "train_val_overlap": len(train_val_overlap),
        "train_test_overlap": len(train_test_overlap),
        "val_test_overlap": len(val_test_overlap),
        "doc_overlap": len(doc_overlap)
    }
