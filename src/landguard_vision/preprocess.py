"""Image preprocessing pipeline for document OCR enhancement."""

import numpy as np
import cv2
from PIL import Image


def to_grayscale(img: Image.Image, suppress_red_watermark: bool = True) -> np.ndarray:
    arr = np.array(img)
    if len(arr.shape) == 3:
        if suppress_red_watermark and arr.shape[2] >= 3:
            # The synthetic watermark is rendered in translucent red (215, 35, 35),
            # whereas document typography is rendered in neutral dark gray/black (R ≈ G ≈ B).
            # Suppressing high-red-chroma pixels prevents the diagonal watermark from
            # bleeding into OCR character strokes while keeping the saved PNG untouched.
            r = arr[:, :, 0].astype(np.int16)
            g = arr[:, :, 1].astype(np.int16)
            b = arr[:, :, 2].astype(np.int16)
            # Only suppress translucent pastel-red watermark pixels on light paper (g > 105, b > 105),
            # preserving dark ink strokes underneath the watermark and solid dark-red map labels.
            red_mask = ((r - g) >= 16) & ((r - b) >= 16) & (r > 150) & (g > 105) & (b > 105)
            cleaned = arr[:, :, :3].copy()
            # Estimate paper background from median luminance
            bg_val = int(np.median(g))
            cleaned[red_mask] = [bg_val, bg_val, bg_val]
            return cv2.cvtColor(cleaned, cv2.COLOR_RGB2GRAY)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return arr


def enhance_contrast_clahe(gray: np.ndarray, clip_limit: float = 1.4, tile_grid_size: tuple = (8, 8)) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray)


def denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, None, h=8, templateWindowSize=7, searchWindowSize=21)


def deskew(gray: np.ndarray) -> np.ndarray:
    """
    Estimates mild page skew using horizontal Hough line segments rather than
    global minAreaRect (which was previously fooled by diagonal watermarks and page aspect ratio).
    """
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=120, minLineLength=120, maxLineGap=20)
    if lines is None or len(lines) == 0:
        return gray

    angles = []
    for line in lines:
        x1, y1, x2, y2 = np.asarray(line).reshape(-1)[:4]
        if x2 == x1:
            continue
        deg = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Only consider near-horizontal structural/text lines (within +/- 12 degrees)
        # to ignore 28-degree diagonal watermark lines and vertical table borders
        if 0.4 <= abs(deg) <= 12.0:
            angles.append(deg)

    if len(angles) < 3:
        return gray

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.4 or abs(median_angle) > 12.0:
        return gray

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated


def preprocess_for_ocr(img: Image.Image, apply_deskew: bool = True, apply_clahe: bool = False) -> np.ndarray:
    gray = to_grayscale(img, suppress_red_watermark=True)
    h, w = gray.shape[:2]

    # Scale up small/low-resolution images to restore character stroke fidelity
    if min(h, w) < 900:
        scale = 1.35
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # Apply mild contrast normalization only when image dynamic range is compressed (low_contrast)
    p5, p95 = np.percentile(gray, [5, 95])
    if (p95 - p5) < 110 or apply_clahe:
        gray = enhance_contrast_clahe(gray, clip_limit=1.4)

    if apply_deskew:
        gray = deskew(gray)
    return gray
