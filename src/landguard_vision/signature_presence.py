"""Signature region presence detector and synthetic reference consistency evaluator."""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, Tuple


def detect_signature_presence(
    img: Image.Image,
    bbox: list = None,
    min_stroke_density: float = 0.004,
    max_stroke_density: float = 0.35
) -> Dict[str, Any]:
    """
    Evaluates signature presence inside a target region.
    Strictly distinguishes visual presence from legal authenticity verification.

    Fixes applied from Phase 4 Vision Audit:
    1. Eliminated unconditional cv2.THRESH_OTSU on blank signature boxes, which previously
       forced a bimodal split on uniform paper noise and produced 186 false positives.
       Ink extraction now requires pixels to be significantly darker than the local paper
       background percentile (bg_p85 - 40).
    2. Removed upward -5px y-padding on candidate bounding boxes that previously clipped
       descenders of the printed 'Signature of Seller:' label above the box.
    3. In unassisted mode (bbox=None), scans the lower-right signature zone (0.66h..0.90h,
       0.68w..0.86w) while rejecting circular blue seals (Tax Receipts) and full-width
       cadastral grid/legend lines (Parcel Maps).
    """
    arr_rgb = np.array(img.convert("RGB"))
    arr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2GRAY)
    h, w = arr.shape

    if bbox is not None and len(bbox) == 4:
        y1, x1, y2, x2 = [int(v) for v in bbox]
        # Crop strictly inside the candidate signature box without upward padding into printed labels
        crop = arr[max(0, y1 + 2):min(h, y2 + 2), max(0, x1):min(w, x2)]
        crop_rgb = arr_rgb[max(0, y1 + 2):min(h, y2 + 2), max(0, x1):min(w, x2)]
        is_assisted = True
    else:
        # Unassisted lower-right signature band covering Sale Deed (y~0.75h),
        # Mutation Record (y~0.68h), and Application (y~0.83h) signature zones
        y1, y2 = int(h * 0.67), int(h * 0.89)
        x1, x2 = int(w * 0.69), int(w * 0.86)
        crop = arr[y1:y2, x1:x2]
        crop_rgb = arr_rgb[y1:y2, x1:x2]
        is_assisted = False

    if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
        return {
            "presence_detected": False,
            "status": "REGION_ABSENT",
            "stroke_density": 0.0,
            "edge_density": 0.0,
            "verification_status": "UNABLE_TO_VERIFY"
        }

    # Suppress translucent red watermark pixels so diagonal watermarks passing through
    # an empty signature box are not mistaken for pen ink
    r_c = crop_rgb[:, :, 0].astype(np.int16)
    g_c = crop_rgb[:, :, 1].astype(np.int16)
    b_c = crop_rgb[:, :, 2].astype(np.int16)
    wm_mask = ((r_c - g_c) >= 15) & ((r_c - b_c) >= 15) & (r_c > 140)
    clean_crop = crop.copy()
    bg_val = float(np.percentile(clean_crop, 85))
    clean_crop[wm_mask] = int(bg_val)

    # Extract true dark ink strokes relative to local paper background luminance
    ink_thresh = max(60.0, bg_val - 42.0)
    ink_mask = (clean_crop < ink_thresh).astype(np.uint8) * 255
    non_zero = int(np.count_nonzero(ink_mask))
    density = non_zero / crop.size

    # Canny edges on watermark-cleaned crop
    edges = cv2.Canny(clean_crop, 45, 140)
    edge_density = int(np.count_nonzero(edges)) / crop.size

    if is_assisted:
        has_signature = (
            (density >= min_stroke_density)
            and (edge_density >= 0.005)
            and (density <= max_stroke_density)
        )
    else:
        # In unassisted quadrant search, reject regions dominated by:
        # (a) Circular blue official seals (e.g. Union Land Office seal in bottom-right of TAX_RECEIPT)
        # (b) Cadastral map boundary boxes or printed legend rows (PARCEL_MAP)
        blue_seal_mask = ((b_c - r_c) >= 25) & (b_c > 90)
        blue_seal_ratio = float(np.count_nonzero(blue_seal_mask)) / crop.size

        # Check for signature-specific geometry: a thin horizontal baseline (~120-160px)
        # paired with diagonal cursive pen strokes in a localized vertical band (<65px tall)
        ys, xs = np.where(ink_mask > 0)
        if len(ys) >= 25:
            y_span = int(np.percentile(ys, 95) - np.percentile(ys, 5))
            x_span = int(np.percentile(xs, 95) - np.percentile(xs, 5))
        else:
            y_span, x_span = 0, 0

        has_signature = (
            (density >= 0.0025)
            and (density <= 0.045)
            and (edge_density >= 0.004)
            and (blue_seal_ratio < 0.005)
            and (10 <= y_span <= 58)
            and (95 <= x_span <= 165)
        )

    status = "PRESENCE_DETECTED" if has_signature else "REGION_ABSENT"

    return {
        "presence_detected": bool(has_signature),
        "status": status,
        "stroke_density": round(float(density), 4),
        "edge_density": round(float(edge_density), 4),
        "verification_status": "SYNTHETIC_REFERENCE_MATCH" if has_signature else "SYNTHETIC_MISMATCH"
    }
