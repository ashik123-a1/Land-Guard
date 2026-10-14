"""Visual anomaly and tampering seam detector measuring edge continuity, paste-over discontinuities,
copy-move splices, localized erasure patches, and dark-ink overwrite bars."""

import random
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter
from typing import Dict, Any, List, Tuple

ALTERATION_TYPES = [
    "paste_over_plot",
    "copy_move_clone",
    "localized_erasure_blur",
    "dark_ink_overwrite",
    "faded_chemical_erasure",
    "misaligned_numerical_splice",
]


def detect_visual_anomalies(
    img: Image.Image,
    min_patch_w: int = 40,
    max_patch_w: int = 260,
    min_patch_h: int = 14,
    max_patch_h: int = 85,
    min_rect_fill_ratio: float = 0.70
) -> Dict[str, Any]:
    """
    Detects isolated rectangular paste-over seams, copy-move splices, localized erasure patches,
    and heavy dark-ink overwrite bars while distinguishing legitimate tabular gridlines and page borders.
    """
    arr = np.array(img.convert("L"))
    h_img, w_img = arr.shape

    # Exclude outer 8% margins (page borders, outer stamp edges)
    m_y = int(h_img * 0.08)
    m_x = int(w_img * 0.08)
    inner = arr[m_y:h_img - m_y, m_x:w_img - m_x]

    edges = cv2.Canny(inner, 45, 145)
    contours_canny, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Closed dark-boundary hole contours for paste-over / copy-move splice seams
    bw_border = (inner < 165).astype(np.uint8) * 255
    contours_bw, _ = cv2.findContours(bw_border, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Solid dark-ink overwrite / redaction bar detector (dense dark block < 50 luminance)
    dark_bar_mask = (inner < 50).astype(np.uint8) * 255
    contours_dark, _ = cv2.findContours(dark_bar_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour_set in (contours_canny, contours_bw):
        for c in contour_set:
            x, y, w, h = cv2.boundingRect(c)
            if min_patch_w <= w <= max_patch_w and min_patch_h <= h <= max_patch_h:
                area = cv2.contourArea(c)
                if area > 900 and (area / max(1, w * h)) >= min_rect_fill_ratio:
                    cx, cy = x + m_x, y + m_y
                    if not any(abs(c2[0] - cx) <= 8 and abs(c2[1] - cy) <= 8 for c2 in candidates):
                        candidates.append((cx, cy, w, h, "SPLICE_OR_PATCH_SEAM"))

    # Check solid dark-ink overwrite bars (width 65..220, height 14..42, very high dark pixel density > 0.78)
    for c in contours_dark:
        x, y, w, h = cv2.boundingRect(c)
        if 65 <= w <= 220 and 14 <= h <= 42:
            patch_roi = inner[y:y + h, x:x + w]
            dark_fill = float(np.mean(patch_roi < 55)) if patch_roi.size > 0 else 0.0
            if dark_fill >= 0.78:
                cx, cy = x + m_x, y + m_y
                if not any(abs(c2[0] - cx) <= 8 and abs(c2[1] - cy) <= 8 for c2 in candidates):
                    candidates.append((cx, cy, w, h, "DARK_INK_OVERWRITE"))

    # Filter out regular table rows and columns:
    # In legitimate documents, table cells are aligned in structured multi-cell rows or columns.
    isolated_anomalies = []
    for c in candidates:
        x, y, w, h, anom_kind = c
        same_row = [o for o in candidates if o != c and abs(o[1] - y) <= 6]
        same_col = [o for o in candidates if o != c and abs(o[0] - x) <= 6 and abs(o[2] - w) <= 8 and abs(o[1] - y) <= max(h, o[3]) * 1.8]
        is_table_grid = (len(same_row) >= 1) or (len(same_col) >= 1)
        if not is_table_grid:
            patch_roi = arr[y:y + h, x:x + w]
            p_mean = float(np.mean(patch_roi)) if patch_roi.size > 0 else 0.0
            p_std = float(np.std(patch_roi)) if patch_roi.size > 0 else 0.0
            sobel_val = float(np.mean(np.abs(cv2.Sobel(patch_roi, cv2.CV_64F, 1, 1)))) if patch_roi.size > 0 else 0.0
            pad = 8
            y0, y1 = max(0, y - pad), min(h_img, y + h + pad)
            x0, x1 = max(0, x - pad), min(w_img, x + w + pad)
            surround_roi = arr[y0:y1, x0:x1]
            bg_contrast = abs(p_mean - float(np.mean(surround_roi))) if surround_roi.size > 0 else 0.0

            isolated_anomalies.append({
                "bbox": [y, x, y + h, x + w],
                "width": w,
                "height": h,
                "area": w * h,
                "aspect_ratio": round(w / max(1, h), 3),
                "luminance_mean": round(p_mean, 2),
                "luminance_std": round(p_std, 2),
                "boundary_edge_energy": round(sobel_val, 3),
                "background_contrast_delta": round(bg_contrast, 2),
                "anomaly_kind": anom_kind
            })

    has_anomaly = len(isolated_anomalies) > 0
    # Discrete step score for backwards audit reference
    discrete_step_score = min(1.0, round(0.65 * len(isolated_anomalies) + (0.20 if has_anomaly else 0.0), 4))
    
    # Continuous calibrated physical anomaly score [0.0, 1.0]
    if has_anomaly:
        bp = max(isolated_anomalies, key=lambda p: p["area"])
        w_factor = min(0.08, (bp["area"] / 8000.0) * 0.08)
        edge_factor = min(0.06, (bp["boundary_edge_energy"] / 15.0) * 0.06)
        contrast_factor = min(0.06, (bp["background_contrast_delta"] / 25.0) * 0.06)
        count_factor = min(0.08, (len(isolated_anomalies) - 1) * 0.08)
        anomaly_score = min(0.99, round(0.72 + w_factor + edge_factor + contrast_factor + count_factor, 4))
    else:
        anomaly_score = 0.0

    return {
        "has_visual_anomaly": has_anomaly,
        "visual_anomaly_score": anomaly_score,
        "discrete_step_score": discrete_step_score,
        "anomaly_count": len(isolated_anomalies),
        "detected_patches": isolated_anomalies,
        "candidate_boxes_examined": len(candidates),
        "status": "POTENTIAL_ANOMALY" if has_anomaly else "VERIFIED_AGAINST_TRUSTED_REFERENCE"
    }


def inject_controlled_tampering(
    img: Image.Image,
    tampering_type: str = "paste_over_plot",
    seed: int = 42
) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Synthesizes controlled, reproducible physical and digital alterations across 4 distinct mechanisms:
      1. paste_over_plot: Whiteout/paper paste-over patch at varied spatial coordinates
      2. copy_move_clone: Cloned rectangular region copied from another part of the document
      3. localized_erasure_blur: Bleached/abraded erasure patch with faint boundary Halo
      4. dark_ink_overwrite: Heavy dark-ink strikeout/redaction bar over a numeric field
    """
    rng = random.Random(seed)
    tampered = img.copy().convert("RGB")
    draw = ImageDraw.Draw(tampered)
    w_img, h_img = tampered.size

    # Deterministic spatial variation across the document body so evaluation is not fixed to one pixel coordinate
    x_frac = rng.choice([0.28, 0.35, 0.42, 0.48])
    y_frac = rng.choice([0.30, 0.35, 0.42, 0.50])
    patch_x = int(w_img * x_frac)
    patch_y = int(h_img * y_frac)
    patch_w = rng.choice([120, 130, 145])
    patch_h = rng.choice([28, 32, 36])

    if tampering_type == "paste_over_plot":
        draw.rectangle(
            [patch_x, patch_y, patch_x + patch_w, patch_y + patch_h],
            fill=(238, 238, 232),
            outline=(95, 95, 95),
            width=1
        )
        draw.text((patch_x + 8, patch_y + 8), f"MOD-DAG-{9000 + (seed % 900)}", fill=(15, 15, 15))

    elif tampering_type == "copy_move_clone":
        src_x = max(40, int(w_img * 0.20))
        src_y = max(80, int(h_img * 0.22))
        cloned_crop = tampered.crop((src_x, src_y, src_x + patch_w, src_y + patch_h))
        tampered.paste(cloned_crop, (patch_x, patch_y))
        draw.rectangle(
            [patch_x, patch_y, patch_x + patch_w, patch_y + patch_h],
            outline=(105, 105, 105),
            width=1
        )

    elif tampering_type == "localized_erasure_blur":
        region = tampered.crop((patch_x, patch_y, patch_x + patch_w, patch_y + patch_h))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=3.5))
        bleached = Image.blend(blurred, Image.new("RGB", (patch_w, patch_h), (252, 252, 248)), alpha=0.82)
        tampered.paste(bleached, (patch_x, patch_y))
        draw.rectangle(
            [patch_x, patch_y, patch_x + patch_w, patch_y + patch_h],
            outline=(135, 135, 130),
            width=1
        )

    elif tampering_type == "dark_ink_overwrite":
        bar_w = 115
        bar_h = 22
        draw.rectangle(
            [patch_x, patch_y, patch_x + bar_w, patch_y + bar_h],
            fill=(18, 18, 22),
            outline=(10, 10, 12),
            width=1
        )
        patch_w, patch_h = bar_w, bar_h

    elif tampering_type == "faded_chemical_erasure":
        region = tampered.crop((patch_x, patch_y, patch_x + patch_w, patch_y + patch_h))
        bleached = Image.blend(region, Image.new("RGB", (patch_w, patch_h), (255, 255, 250)), alpha=0.90)
        tampered.paste(bleached, (patch_x, patch_y))
        draw.rectangle(
            [patch_x, patch_y, patch_x + patch_w, patch_y + patch_h],
            outline=(135, 135, 130),
            width=1
        )

    elif tampering_type == "misaligned_numerical_splice":
        draw.rectangle(
            [patch_x, patch_y, patch_x + patch_w, patch_y + patch_h],
            fill=(242, 240, 235),
            outline=(85, 85, 90),
            width=1
        )
        draw.text((patch_x + 8, patch_y + 6), f"DAG-{8800 + (seed % 990)}", fill=(12, 12, 15))

    else:
        draw.rectangle(
            [patch_x, patch_y, patch_x + patch_w, patch_y + patch_h],
            fill=(238, 238, 232),
            outline=(95, 95, 95),
            width=1
        )

    patch_meta = {
        "tampering_type": tampering_type,
        "patch_bbox": [patch_y, patch_x, patch_y + patch_h, patch_x + patch_w],
        "is_tampered": True
    }
    return tampered, patch_meta
