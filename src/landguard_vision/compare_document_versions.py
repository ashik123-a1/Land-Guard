"""Cross-document version comparator for detecting field and visual discrepancies."""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, Tuple


def compare_document_fields(
    doc_a_fields: Dict[str, Any],
    doc_b_fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Compares fields between two document versions and highlights differences."""
    all_keys = set(doc_a_fields.keys()).union(set(doc_b_fields.keys()))
    discrepancies = []
    matches = []
    
    for k in sorted(all_keys):
        va = str(doc_a_fields.get(k, "<MISSING>"))
        vb = str(doc_b_fields.get(k, "<MISSING>"))
        if va != vb:
            discrepancies.append({
                "field": k,
                "version_a_value": va,
                "version_b_value": vb
            })
        else:
            matches.append(k)
            
    return {
        "has_discrepancies": len(discrepancies) > 0,
        "discrepancy_count": len(discrepancies),
        "discrepancies": discrepancies,
        "matching_fields_count": len(matches)
    }


def compare_document_images(
    img_a: Image.Image,
    img_b: Image.Image
) -> Dict[str, Any]:
    """Computes pixel-level difference and identifies changed regions."""
    # Ensure same size
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.Resampling.BILINEAR)
        
    arr_a = np.array(img_a.convert("L"))
    arr_b = np.array(img_b.convert("L"))
    
    diff = cv2.absdiff(arr_a, arr_b)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    
    diff_pixels = np.count_nonzero(thresh)
    diff_ratio = diff_pixels / arr_a.size
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bounding_changes = []
    
    for cnt in contours:
        if cv2.contourArea(cnt) > 200:
            x, y, w, h = cv2.boundingRect(cnt)
            bounding_changes.append([y, x, y + h, x + w])
            
    return {
        "pixel_diff_ratio": round(float(diff_ratio), 4),
        "num_changed_regions": len(bounding_changes),
        "changed_bounding_boxes": bounding_changes[:10],
        "has_significant_visual_change": diff_ratio > 0.015
    }
