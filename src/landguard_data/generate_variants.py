"""Generates controlled image variants according to the degradation schedule."""

import random
import uuid
from typing import List, Dict, Any, Tuple
from PIL import Image
from .degrade_images import apply_degradation

QUALITY_CLASSES = [
    "clean_digital",
    "clean_scan",
    "grayscale_scan",
    "low_resolution",
    "mild_rotation",
    "skewed_scan",
    "low_contrast",
    "uneven_illumination",
    "blur",
    "compression_artifacts",
    "light_noise",
    "wrinkled_paper",
    "mild_stains",
    "shadow_phone_photo",
    "cropped_edges",
    "faded_text",
]


def create_image_variant(
    clean_image: Image.Image,
    doc: Dict[str, Any],
    quality_class: str,
    rng: random.Random
) -> Tuple[Image.Image, Dict[str, Any]]:
    uid = uuid.UUID(int=rng.getrandbits(128)).hex[:8].upper()
    variant_id = f"IMG-{uid}"
    
    degraded_img, params = apply_degradation(clean_image, quality_class, rng)
    
    variant_meta = {
        "image_id": variant_id,
        "source_document_id": doc["document_id"],
        "source_record_id": doc["canonical_record_id"],
        "document_type": doc["document_type"],
        "language": doc["language"],
        "source_template_id": doc["template_id"],
        "image_quality_class": quality_class,
        "degradation_parameters": params
    }
    
    return degraded_img, variant_meta
