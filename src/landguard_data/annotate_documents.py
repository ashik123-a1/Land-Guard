"""Builds comprehensive, machine-readable ground truth annotations and computes SHA-256."""

import hashlib
import io
from typing import Dict, Any
from PIL import Image


def compute_sha256(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return hashlib.sha256(buf.getvalue()).hexdigest()


def build_annotation(
    image: Image.Image,
    doc: Dict[str, Any],
    variant_meta: Dict[str, Any],
    ground_truth_text: str,
    bounding_boxes: Dict[str, list],
    signature_presence: bool,
    seal_presence: bool,
    tampering_outcome: str = "CLEAN_LEGITIMATE",
    split_assignment: str = "train"
) -> Dict[str, Any]:
    sha256 = compute_sha256(image)
    
    # Assess legibility label based on quality class
    quality_class = variant_meta["image_quality_class"]
    is_poor_quality = quality_class in ["low_resolution", "blur", "compression_artifacts"]
    
    legibility = {}
    for f in doc["fields"]:
        legibility[f] = "POOR" if is_poor_quality else "CLEAR"
        
    consistency = {
        "dates_consistent": tampering_outcome != "DATE_ANOMALY",
        "plot_consistent": tampering_outcome != "PLOT_NUMBER_MISMATCH",
        "area_consistent": tampering_outcome != "AREA_DISCREPANCY",
        "owner_consistent": tampering_outcome != "OWNER_NAME_MISMATCH"
    }
    
    return {
        "image_id": variant_meta["image_id"],
        "source_document_id": doc["document_id"],
        "source_record_id": doc["canonical_record_id"],
        "scenario_id": doc.get("scenario_id", "SCN-DEFAULT"),
        "document_type": doc["document_type"],
        "language": doc["language"],
        "source_template_id": doc["template_id"],
        "ground_truth_text": ground_truth_text,
        "ground_truth_fields": doc["fields"],
        "bounding_boxes": bounding_boxes,
        "signature_presence": signature_presence,
        "seal_presence": seal_presence,
        "expected_consistency_checks": consistency,
        "expected_tampering_outcome": tampering_outcome,
        "image_quality_class": quality_class,
        "degradation_parameters": variant_meta.get("degradation_parameters", {}),
        "field_legibility_labels": legibility,
        "split_assignment": split_assignment,
        "sha256_checksum": sha256
    }
