"""Official seal / stamp presence detector and contour geometry validator."""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any


def detect_seal_presence(
    img: Image.Image,
    bbox: list = None
) -> Dict[str, Any]:
    """
    Detects whether an official seal / stamp circular or oval region is present.
    Strictly separates visual presence from legal authentication.
    """
    arr_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    h, w, _ = arr_bgr.shape
    
    if bbox is not None:
        y1, x1, y2, x2 = [int(v) for v in bbox]
        crop = arr_bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
    else:
        # Lower half
        crop = arr_bgr[int(h * 0.50):h, :]
        
    if crop.size == 0:
        return {
            "presence_detected": False,
            "status": "SEAL_ABSENT",
            "circularity": 0.0,
            "verification_status": "UNABLE_TO_VERIFY"
        }
        
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    best_circularity = 0.0
    found_seal = False
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 800:
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = 4 * np.pi * (area / (perimeter * perimeter))
                if circularity > best_circularity:
                    best_circularity = circularity
                if 0.35 <= circularity <= 1.25:
                    found_seal = True
                    break
                    
    # Also check for colored ink (blue/purple) in seal region
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # Blue/purple hue range: 90-150
    blue_mask = cv2.inRange(hsv, np.array([90, 40, 40]), np.array([160, 255, 255]))
    blue_pixels = int(np.count_nonzero(blue_mask))
    has_ink_color = bool((blue_pixels / crop.size) > 0.008)
    
    detected = bool(found_seal or has_ink_color)
    
    return {
        "presence_detected": detected,
        "status": "SEAL_PRESENT" if detected else "SEAL_ABSENT",
        "best_circularity": round(float(best_circularity), 4),
        "has_colored_ink": has_ink_color,
        "verification_status": "SYNTHETIC_REFERENCE_MATCH" if detected else "SYNTHETIC_MISMATCH"
    }
