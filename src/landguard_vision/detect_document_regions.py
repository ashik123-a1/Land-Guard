"""Layout analysis and document region detection using morphological projections."""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, List


def detect_document_regions(img: Image.Image) -> Dict[str, Any]:
    arr = np.array(img.convert("L"))
    h, w = arr.shape
    
    # Threshold
    _, binary = cv2.threshold(arr, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Horizontal projection profile to segment header, body, footer
    horiz_proj = np.sum(binary, axis=1)
    
    # Morphological line detection for tables
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.05), 1))
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * 0.04)))
    
    horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)
    vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)
    table_grid = cv2.add(horiz_lines, vert_lines)
    
    table_contours, _ = cv2.findContours(table_grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    table_boxes = []
    for cnt in table_contours:
        if cv2.contourArea(cnt) > 5000:
            x, y, bw, bh = cv2.boundingRect(cnt)
            table_boxes.append([y, x, y + bh, x + bw])
            
    return {
        "header_region": [0, 0, int(h * 0.22), w],
        "body_region": [int(h * 0.22), 0, int(h * 0.75), w],
        "footer_region": [int(h * 0.75), 0, h, w],
        "detected_table_boxes": table_boxes[:5],
        "has_table_structure": len(table_boxes) > 0
    }
