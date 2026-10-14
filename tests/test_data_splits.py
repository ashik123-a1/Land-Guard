"""Tests grouped split assignment and leakage prevention."""

from src.landguard_data.build_splits import assign_grouped_splits, verify_leakage_free


def test_leakage_prevention():
    items = []
    for i in range(30):
        items.append({
            "scenario_id": f"SCN-{i//3}", # 10 distinct scenario groups
            "source_document_id": f"DOC-{i}",
            "value": i
        })
        
    splits = assign_grouped_splits(items, group_key="scenario_id", seed=42)
    assert len(splits["train"]) > 0
    assert len(splits["val"]) > 0
    assert len(splits["test"]) > 0
    
    report = verify_leakage_free(splits, group_key="scenario_id")
    assert report["is_leakage_free"] is True
    assert report["train_val_overlap"] == 0
    assert report["train_test_overlap"] == 0
    assert report["val_test_overlap"] == 0


def test_seller_grouped_splits_disjoint():
    items = []
    for i in range(60):
        items.append({
            "scenario_id": f"SCN-{i}",
            "primary_seller_id": f"OWN-{i // 4}",
            "parcel_id": f"PCL-{i // 4}",
        })
    splits = assign_grouped_splits(items, group_key="primary_seller_id", seed=42)
    report_seller = verify_leakage_free(splits, group_key="primary_seller_id")
    report_parcel = verify_leakage_free(splits, group_key="parcel_id")
    assert report_seller["is_leakage_free"] is True
    assert report_parcel["is_leakage_free"] is True

