"""Applies deterministic, reproducible scan degradation and artifact simulations."""

import io
import random
from typing import Tuple, Dict, Any
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import cv2


def apply_degradation(
    img: Image.Image,
    quality_class: str,
    rng: random.Random
) -> Tuple[Image.Image, dict]:
    """
    Transforms clean document image into simulated realistic scan/photo variant.
    Returns (degraded_image, degradation_params_dict).
    """
    params = {"quality_class": quality_class}
    res = img.copy()
    w, h = res.size
    
    if quality_class == "clean_digital":
        # Pure source
        pass
        
    elif quality_class == "clean_scan":
        # Subtle scanner noise & contrast
        res = res.filter(ImageFilter.GaussianBlur(radius=0.4))
        enh = ImageEnhance.Contrast(res)
        res = enh.enhance(1.05)
        params["blur_radius"] = 0.4
        
    elif quality_class == "grayscale_scan":
        # Converted to 8-bit grayscale and back to RGB
        res = res.convert("L").convert("RGB")
        enh = ImageEnhance.Contrast(res)
        res = enh.enhance(1.15)
        params["grayscale"] = True
        
    elif quality_class == "low_resolution":
        # Downscale and re-upscale
        scale = rng.uniform(0.35, 0.50)
        low_w = max(100, int(w * scale))
        low_h = max(100, int(h * scale))
        res = res.resize((low_w, low_h), Image.Resampling.BILINEAR).resize((w, h), Image.Resampling.NEAREST)
        params["downscale_ratio"] = round(scale, 3)
        
    elif quality_class == "mild_rotation":
        angle = rng.uniform(-2.5, 2.5)
        res = res.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(245, 245, 240))
        params["rotation_angle_deg"] = round(angle, 2)
        
    elif quality_class == "skewed_scan":
        # Slight perspective shear
        arr = np.array(res)
        pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        dx = rng.randint(10, 30)
        dy = rng.randint(5, 20)
        pts2 = np.float32([[dx, 0], [w - dx, dy], [0, h - dy], [w, h]])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        warped = cv2.warpPerspective(arr, M, (w, h), borderValue=(245, 245, 240))
        res = Image.fromarray(warped)
        params["perspective_dx"] = dx
        
    elif quality_class == "low_contrast":
        factor = rng.uniform(0.55, 0.70)
        enh = ImageEnhance.Contrast(res)
        res = enh.enhance(factor)
        params["contrast_factor"] = round(factor, 2)
        
    elif quality_class == "uneven_illumination":
        # Vertical gradient simulating camera flash or ceiling light gradient
        arr = np.array(res).astype(np.float32)
        gradient = np.linspace(0.65, 1.15, h)[:, np.newaxis, np.newaxis]
        arr = np.clip(arr * gradient, 0, 255).astype(np.uint8)
        res = Image.fromarray(arr)
        params["gradient_type"] = "linear_vertical"
        
    elif quality_class == "blur":
        radius = rng.uniform(1.2, 2.4)
        res = res.filter(ImageFilter.GaussianBlur(radius=radius))
        params["gaussian_blur_radius"] = round(radius, 2)
        
    elif quality_class == "compression_artifacts":
        q = rng.randint(20, 35)
        buffer = io.BytesIO()
        res.save(buffer, format="JPEG", quality=q)
        buffer.seek(0)
        res = Image.open(buffer).convert("RGB")
        params["jpeg_quality"] = q
        
    elif quality_class == "light_noise":
        arr = np.array(res).astype(np.float32)
        noise = np.random.RandomState(rng.randint(0, 10000)).normal(0, 14, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        res = Image.fromarray(arr)
        params["noise_sigma"] = 14
        
    elif quality_class == "wrinkled_paper":
        # Draw soft fold/crease lines
        draw = ImageDraw.Draw(res)
        for _ in range(3):
            lx1 = rng.randint(0, w)
            ly1 = 0
            lx2 = rng.randint(0, w)
            ly2 = h
            draw.line([(lx1, ly1), (lx2, ly2)], fill=(200, 195, 185), width=2)
        params["wrinkle_creases"] = 3
        
    elif quality_class == "mild_stains":
        # Draw translucent tea/coffee-like smudge
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        sx = rng.randint(int(w * 0.2), int(w * 0.8))
        sy = rng.randint(int(h * 0.2), int(h * 0.8))
        srad = rng.randint(40, 90)
        odraw.ellipse([sx - srad, sy - srad, sx + srad, sy + srad], fill=(160, 130, 80, 50))
        res = Image.alpha_composite(res.convert("RGBA"), overlay).convert("RGB")
        params["stain_radius"] = srad
        
    elif quality_class == "shadow_phone_photo":
        # Dark corner shadow
        arr = np.array(res).astype(np.float32)
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt(X**2 + Y**2) / np.sqrt(w**2 + h**2)
        shadow_map = 1.0 - (0.45 * (1.0 - dist))[:, :, np.newaxis]
        arr = np.clip(arr * shadow_map, 0, 255).astype(np.uint8)
        res = Image.fromarray(arr)
        params["shadow_type"] = "top_left_phone_shadow"
        
    elif quality_class == "cropped_edges":
        # Crop 3-5% margin
        crop_m = int(min(w, h) * 0.04)
        cropped = res.crop((crop_m, crop_m, w - crop_m, h - crop_m))
        res = cropped.resize((w, h), Image.Resampling.BILINEAR)
        params["crop_margin_px"] = crop_m

    elif quality_class == "faded_text":
        # Simulate thermal/carbon copy ink fading by compressing dynamic range towards paper background
        arr = np.array(res).astype(np.float32)
        faded_arr = np.where(arr < 180, arr * 0.45 + 130, arr)
        res = Image.fromarray(np.clip(faded_arr, 0, 255).astype(np.uint8))
        params["fading_intensity"] = "moderate_carbon_fade"
        
    else:
        # Default fallback
        params["fallback"] = True
        
    return res, params
