"""Comprehensive model evaluation suite computing Precision, Recall, F1, ROC-AUC, PR-AUC, Calibration (Brier/ECE), Validation Threshold Selection, and Bootstrap 95% CIs."""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    brier_score_loss
)


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) across uniform probability bins."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.clip(np.asarray(y_prob, dtype=float), 0.0, 1.0)
    if len(y_true) == 0:
        return 0.0
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= lo) & (y_prob <= hi)
        else:
            mask = (y_prob >= lo) & (y_prob < hi)
        if np.any(mask):
            bin_acc = float(np.mean(y_true[mask]))
            bin_conf = float(np.mean(y_prob[mask]))
            ece += (np.sum(mask) / n) * abs(bin_acc - bin_conf)
    return float(ece)


def select_optimal_threshold(
    model,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    scaler = None
) -> float:
    """Selects the decision threshold on the VALIDATION set only to maximize F1-score."""
    if X_val is None or y_val is None or len(y_val) == 0:
        return 0.5
    X_eval = scaler.transform(X_val) if scaler is not None else X_val
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_eval)[:, 1]
    else:
        return 0.5

    best_thr = 0.5
    best_f1 = -1.0
    for thr in np.linspace(0.20, 0.80, 61):
        preds = (probs >= thr).astype(int)
        score = float(f1_score(y_val, preds, zero_division=0))
        if score > best_f1 or (abs(score - best_f1) < 1e-6 and abs(thr - 0.5) < abs(best_thr - 0.5)):
            best_f1 = score
            best_thr = float(thr)
    return round(best_thr, 4)


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    n_boot: int = 200,
    seed: int = 42
) -> Dict[str, List[float]]:
    """Computes 95% bootstrap confidence intervals for key classification metrics."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    if n < 5:
        return {}
    accs, precs, recs, f1s, prs = [], [], [], [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_pred[idx]
        ypr = y_prob[idx]
        accs.append(float(accuracy_score(yt, yp)))
        precs.append(float(precision_score(yt, yp, zero_division=0)))
        recs.append(float(recall_score(yt, yp, zero_division=0)))
        f1s.append(float(f1_score(yt, yp, zero_division=0)))
        if len(np.unique(yt)) > 1:
            prs.append(float(average_precision_score(yt, ypr)))
    def _ci(arr):
        if not arr:
            return [0.0, 0.0]
        return [round(float(np.percentile(arr, 2.5)), 4), round(float(np.percentile(arr, 97.5)), 4)]
    return {
        "accuracy_ci95": _ci(accs),
        "precision_ci95": _ci(precs),
        "recall_ci95": _ci(recs),
        "f1_score_ci95": _ci(f1s),
        "pr_auc_ci95": _ci(prs),
    }


def evaluate_classifier(
    name: str,
    model,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    scaler = None,
    threshold: Optional[float] = None,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    if scaler is not None:
        X_eval = scaler.transform(X_test)
    else:
        X_eval = X_test

    if threshold is None and X_val is not None and y_val is not None:
        selected_threshold = select_optimal_threshold(model, X_val, y_val, scaler=scaler)
    else:
        selected_threshold = threshold if threshold is not None else 0.5

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_eval)[:, 1]
        if threshold is not None or (X_val is not None and y_val is not None):
            y_pred = (y_prob >= selected_threshold).astype(int)
        else:
            y_pred = model.predict(X_eval)
    elif hasattr(model, "decision_function"):
        y_prob = model.decision_function(X_eval)
        y_pred = model.predict(X_eval)
    else:
        y_pred = model.predict(X_eval)
        y_prob = y_pred.astype(float)

    acc = float(accuracy_score(y_test, y_pred))
    p = float(precision_score(y_test, y_pred, zero_division=0))
    r = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    try:
        roc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        roc = 0.5

    try:
        pr_auc = float(average_precision_score(y_test, y_prob))
    except Exception:
        pr_auc = 0.5

    try:
        prob_clipped = np.clip(y_prob, 0.0, 1.0)
        brier = float(brier_score_loss(y_test, prob_clipped))
        ece = compute_ece(y_test, prob_clipped)
    except Exception:
        brier = 0.25
        ece = 0.0

    cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]

    # Per-class metrics
    try:
        p_classes = precision_score(y_test, y_pred, average=None, zero_division=0)
        r_classes = recall_score(y_test, y_pred, average=None, zero_division=0)
        f1_classes = f1_score(y_test, y_pred, average=None, zero_division=0)
        per_class = {
            "legitimate": {"precision": round(float(p_classes[0]), 4), "recall": round(float(r_classes[0]), 4), "f1": round(float(f1_classes[0]), 4)},
            "fraud": {"precision": round(float(p_classes[1]), 4), "recall": round(float(r_classes[1]), 4), "f1": round(float(f1_classes[1]), 4)}
        }
    except Exception:
        per_class = {}

    fp_indices = np.where((y_pred == 1) & (y_test == 0))[0].tolist()
    fn_indices = np.where((y_pred == 0) & (y_test == 1))[0].tolist()
    boot_ci = compute_bootstrap_ci(np.asarray(y_test), np.asarray(y_pred), np.asarray(y_prob))

    return {
        "model_name": name,
        "decision_threshold": round(float(selected_threshold), 4),
        "accuracy": round(acc, 4),
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "ece_score": round(ece, 4),
        "confusion_matrix": cm,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "per_class_metrics": per_class,
        "bootstrap_ci_95": boot_ci,
        "false_positive_count": len(fp_indices),
        "false_negative_count": len(fn_indices),
        "sample_fp_indices": fp_indices[:5],
        "sample_fn_indices": fn_indices[:5]
    }


def compare_all_models(
    results_list: List[Dict[str, Any]]
) -> pd.DataFrame:
    rows = []
    for res in results_list:
        rows.append({
            "Model": res["model_name"],
            "Accuracy": res["accuracy"],
            "Precision": res["precision"],
            "Recall": res["recall"],
            "F1-Score": res["f1_score"],
            "ROC-AUC": res.get("roc_auc", "N/A"),
            "PR-AUC": res.get("pr_auc", "N/A"),
            "Brier": res.get("brier_score", "N/A"),
            "ECE": res.get("ece_score", "N/A"),
            "FP Count": res["false_positive_count"],
            "FN Count": res["false_negative_count"]
        })
    return pd.DataFrame(rows)

