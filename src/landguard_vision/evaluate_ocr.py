"""Evaluates OCR predictions with strict language separation (Bangla vs English), normalization, and field accuracy."""

import re
import unicodedata
from typing import List, Dict, Any, Tuple


_BN_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_text(text: str) -> str:
    """Normalizes Unicode encoding, Bengali/ASCII digits, whitespace, and typographic punctuation."""
    if not text:
        return ""
    # Unicode NFC normalization
    t = unicodedata.normalize("NFC", text)
    t = t.translate(_BN_DIGIT_MAP)
    # Replace non-breaking spaces and repeated whitespace
    t = re.sub(r"[\xa0\s]+", " ", t)
    # Normalize common typographic marks
    t = t.replace("—", "-").replace("–", "-").replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return t.strip()


def extract_english_subset(text: str) -> str:
    """Extracts Latin letters, digits, and common punctuation for English OCR evaluation."""
    t = normalize_text(text)
    # Match ASCII alphanumeric words and punctuation
    cleaned = re.sub(r"[^\x20-\x7E]+", " ", t)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_bangla_subset(text: str) -> str:
    """Extracts Bengali script characters for Bangla OCR evaluation."""
    t = normalize_text(text)
    # Match Bengali unicode block \u0980-\u09FF
    cleaned = re.sub(r"[^\u0980-\u09FF\s]+", " ", t)
    return re.sub(r"\s+", " ", cleaned).strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
        
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]


def compute_cer(reference: str, hypothesis: str) -> float:
    ref_clean = normalize_text(reference)
    hyp_clean = normalize_text(hypothesis)
    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0
    dist = levenshtein_distance(ref_clean, hyp_clean)
    return min(1.0, dist / len(ref_clean))


def compute_wer(reference: str, hypothesis: str) -> float:
    ref_words = re.sub(r"[^\w\s]", "", normalize_text(reference)).split()
    hyp_words = re.sub(r"[^\w\s]", "", normalize_text(hypothesis)).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return min(1.0, dist / len(ref_words))


def evaluate_ocr_predictions(
    eval_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates predictions separately across English, Bangla, and overall subsets,
    broken down by category and image quality, plus separate downstream structured
    field extraction metrics (exact match, precision, recall, F1).
    """
    total_cases = len(eval_cases)
    
    overall_cers = []
    overall_wers = []
    english_cers = []
    english_wers = []
    bangla_cers = []
    bangla_wers = []
    
    field_matches = 0
    total_fields_checked = 0
    total_fields_predicted = 0
    per_field_stats = {}
    
    by_category = {}
    by_quality = {}
    examples = []
    
    checked_field_keys = ["deed_number", "dag_plot_number", "khatian_number", "transferred_area_decimal"]
    
    for case in eval_cases:
        gt_raw = case["ground_truth_text"]
        pred_raw = case["predicted_text"]
        
        gt_norm = normalize_text(gt_raw)
        pred_norm = normalize_text(pred_raw)
        
        # 1. Overall
        cer_all = compute_cer(gt_norm, pred_norm)
        wer_all = compute_wer(gt_norm, pred_norm)
        overall_cers.append(cer_all)
        overall_wers.append(wer_all)
        
        # 2. English subset
        gt_en = extract_english_subset(gt_norm)
        pred_en = extract_english_subset(pred_norm)
        cer_en = compute_cer(gt_en, pred_en) if gt_en else 0.0
        wer_en = compute_wer(gt_en, pred_en) if gt_en else 0.0
        if gt_en:
            english_cers.append(cer_en)
            english_wers.append(wer_en)
            
        # 3. Bangla subset
        gt_bn = extract_bangla_subset(gt_norm)
        pred_bn = extract_bangla_subset(pred_norm)
        cer_bn = compute_cer(gt_bn, pred_bn) if gt_bn else 0.0
        wer_bn = compute_wer(gt_bn, pred_bn) if gt_bn else 0.0
        if gt_bn:
            bangla_cers.append(cer_bn)
            bangla_wers.append(wer_bn)
            
        # 4. Downstream Structured Field Extraction Metrics
        gt_fields = case.get("ground_truth_fields", {})
        pred_fields = case.get("extracted_fields", {})
        
        for k in checked_field_keys:
            has_gt = (k in gt_fields and gt_fields[k] is not None and str(gt_fields[k]) != "")
            has_pred = (k in pred_fields and pred_fields[k] is not None and str(pred_fields[k]) != "")
            if k not in per_field_stats:
                per_field_stats[k] = {"gt_count": 0, "pred_count": 0, "match_count": 0}
            if has_gt:
                total_fields_checked += 1
                per_field_stats[k]["gt_count"] += 1
                if has_pred:
                    total_fields_predicted += 1
                    per_field_stats[k]["pred_count"] += 1
                if str(pred_fields.get(k)) == str(gt_fields[k]):
                    field_matches += 1
                    per_field_stats[k]["match_count"] += 1
                     
        # Grouped Metrics
        cat = case.get("document_type", "UNKNOWN")
        if cat not in by_category:
            by_category[cat] = {"overall_cer": [], "english_cer": [], "bangla_cer": [], "wer": [], "en_wer": [], "bn_wer": []}
        by_category[cat]["overall_cer"].append(cer_all)
        by_category[cat]["english_cer"].append(cer_en)
        by_category[cat]["bangla_cer"].append(cer_bn)
        by_category[cat]["wer"].append(wer_all)
        by_category[cat]["en_wer"].append(wer_en)
        if gt_bn:
            by_category[cat]["bn_wer"].append(wer_bn)
        
        q = case.get("quality_class", "UNKNOWN")
        if q not in by_quality:
            by_quality[q] = {"overall_cer": [], "english_cer": [], "bangla_cer": [], "wer": [], "en_wer": [], "bn_wer": []}
        by_quality[q]["overall_cer"].append(cer_all)
        by_quality[q]["english_cer"].append(cer_en)
        by_quality[q]["bangla_cer"].append(cer_bn)
        by_quality[q]["wer"].append(wer_all)
        by_quality[q]["en_wer"].append(wer_en)
        if gt_bn:
            by_quality[q]["bn_wer"].append(wer_bn)
        
        if len(examples) < 12:
            examples.append({
                "image_id": case["image_id"],
                "document_type": cat,
                "quality_class": q,
                "overall_cer": round(cer_all, 4),
                "english_cer": round(cer_en, 4),
                "bangla_cer": round(cer_bn, 4),
                "english_gt_sample": gt_en[:90],
                "english_pred_sample": pred_en[:90],
                "bangla_gt_sample": gt_bn[:90],
                "bangla_pred_sample": pred_bn[:90]
            })
            
    def mean_s(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0
        
    field_recall = round(field_matches / max(1, total_fields_checked), 4)
    field_precision = round(field_matches / max(1, total_fields_predicted), 4)
    field_f1 = round(2 * field_precision * field_recall / max(1e-9, field_precision + field_recall), 4) if (field_precision + field_recall) > 0 else 0.0
    
    summary = {
        "total_evaluated": total_cases,
        "overall": {
            "mean_cer": mean_s(overall_cers),
            "mean_wer": mean_s(overall_wers)
        },
        "english_subset": {
            "mean_cer": mean_s(english_cers),
            "mean_wer": mean_s(english_wers),
            "evaluated_samples": len(english_cers)
        },
        "bangla_subset": {
            "mean_cer": mean_s(bangla_cers),
            "mean_wer": mean_s(bangla_wers),
            "evaluated_samples": len(bangla_cers)
        },
        "exact_field_match_rate": field_recall,
        "field_extraction_metrics": {
            "exact_match_accuracy": field_recall,
            "field_precision": field_precision,
            "field_recall": field_recall,
            "field_f1": field_f1,
            "fields_checked_count": total_fields_checked,
            "fields_predicted_count": total_fields_predicted,
            "fields_matched_count": field_matches,
            "per_field": {
                fk: {
                    "gt_count": fv["gt_count"],
                    "pred_count": fv["pred_count"],
                    "match_count": fv["match_count"],
                    "exact_match_rate": round(fv["match_count"] / max(1, fv["gt_count"]), 4),
                    "precision": round(fv["match_count"] / max(1, fv["pred_count"]), 4),
                }
                for fk, fv in per_field_stats.items()
            }
        },
        "fields_checked_count": total_fields_checked,
        "fields_matched_count": field_matches,
        "by_category": {
            k: {
                "overall_cer": mean_s(v["overall_cer"]),
                "english_cer": mean_s(v["english_cer"]),
                "bangla_cer": mean_s(v["bangla_cer"]),
                "mean_wer": mean_s(v["wer"]),
                "english_wer": mean_s(v["en_wer"]),
                "bangla_wer": mean_s(v["bn_wer"]),
                "count": len(v["overall_cer"])
            }
            for k, v in by_category.items()
        },
        "by_quality": {
            k: {
                "overall_cer": mean_s(v["overall_cer"]),
                "english_cer": mean_s(v["english_cer"]),
                "bangla_cer": mean_s(v["bangla_cer"]),
                "mean_wer": mean_s(v["wer"]),
                "english_wer": mean_s(v["en_wer"]),
                "bangla_wer": mean_s(v["bn_wer"]),
                "count": len(v["overall_cer"])
            }
            for k, v in by_quality.items()
        },
        "sample_comparisons": examples
    }
    
    return summary

