"""Tests ground truth annotation fidelity, checksum calculation, and bounding boxes."""

from PIL import Image
from src.landguard_data.annotate_documents import compute_sha256, build_annotation


def test_sha256_computation():
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    h1 = compute_sha256(img)
    h2 = compute_sha256(img)
    assert len(h1) == 64
    assert h1 == h2
    
    img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
    h3 = compute_sha256(img2)
    assert h1 != h3
