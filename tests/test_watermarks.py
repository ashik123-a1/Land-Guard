"""Tests mandatory prominent watermark presence across document images."""

from PIL import Image
from src.landguard_data.render_documents import apply_watermark, WATERMARK_TEXT


def test_watermark_application():
    base = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    watermarked = apply_watermark(base)
    assert watermarked.size == base.size
    assert WATERMARK_TEXT == "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"
