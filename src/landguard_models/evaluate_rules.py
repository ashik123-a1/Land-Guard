"""Evaluates deterministic verification rule engine accuracy, precision, recall, and edge cases."""

from typing import List, Dict, Any
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, confusion_matrix
from .verification_rules import evaluate_verification_rules


def evaluate_rule_engine(
    dataset_records: List[Dict[str, Any]],
    include_document_evidence: bool = False
) -> Dict[str, Any]:
    y_true = []
    y_pred = []
    y_scores = []
    false_positives = []
    false_negatives = []
    rule_trigger_counts: Dict[str, int] = {}
    category_counts: Dict[str, int] = {}

    for item in dataset_records:
        txn = item["transaction"]
        parcel = item["parcel"]
        history = item.get("history_transactions", [])
        ground_truth_risk = 1 if item.get("is_fraud_risk", False) else 0
        mutations = item.get("mutations", [])
        doc_ev = item.get("document_evidence") if include_document_evidence else None

        is_flagged, score, violations = evaluate_verification_rules(
            txn=txn,
            parcel=parcel,
            history_txns=history,
            mutations=mutations,
            document_evidence=doc_ev,
            include_document_evidence=include_document_evidence,
        )
        pred_label = 1 if is_flagged else 0

        y_true.append(ground_truth_risk)
        y_pred.append(pred_label)
        y_scores.append(score)

        for v in violations:
            code = v["rule_code"]
            cat = v["category"]
            rule_trigger_counts[code] = rule_trigger_counts.get(code, 0) + 1
            category_counts[cat] = category_counts.get(cat, 0) + 1

        if pred_label == 1 and ground_truth_risk == 0:
            false_positives.append({
                "transaction_id": txn.get("transaction_id"),
                "scenario_category": item.get("scenario_category", "LEGITIMATE"),
                "violations": violations,
            })
        elif pred_label == 0 and ground_truth_risk == 1:
            false_negatives.append({
                "transaction_id": txn.get("transaction_id"),
                "scenario_category": item.get("scenario_category", "FRAUD_RISK"),
                "violations": violations,
            })

    p = float(precision_score(y_true, y_pred, zero_division=0))
    r = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    acc = float(accuracy_score(y_true, y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()

    return {
        "model_name": "Deterministic Rule Baseline",
        "total_evaluated": len(dataset_records),
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(acc, 4),
        "confusion_matrix": cm,
        "false_positive_count": len(false_positives),
        "false_negative_count": len(false_negatives),
        "rule_trigger_breakdown": rule_trigger_counts,
        "finding_category_breakdown": category_counts,
        "sample_false_positives": false_positives[:5],
        "sample_false_negatives": false_negatives[:5],
    }
