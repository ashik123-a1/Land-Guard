"""Tests signature and seal presence detectors on synthetic document images."""

from PIL import Image, ImageDraw
from src.landguard_vision.signature_presence import detect_signature_presence
from src.landguard_vision.seal_presence import detect_seal_presence


def test_signature_and_seal_detectors():
    # 1. Blank image - should detect absence
    blank = Image.new("RGB", (600, 600), color=(255, 255, 255))
    sig_res = detect_signature_presence(blank)
    assert bool(sig_res["presence_detected"]) is False
    seal_res = detect_seal_presence(blank)
    assert bool(seal_res["presence_detected"]) is False
    
    # 2. Image with circular seal
    seal_img = Image.new("RGB", (600, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(seal_img)
    draw.ellipse([350, 350, 500, 500], outline=(30, 40, 180), width=4)
    draw.ellipse([358, 358, 492, 492], outline=(30, 40, 180), width=2)
    
    seal_detected = detect_seal_presence(seal_img)
    assert bool(seal_detected["presence_detected"]) is True
    
    # 3. Signature presence with targeted bounding box
    sig_img = Image.new("RGB", (600, 600), color=(255, 255, 255))
    sdraw = ImageDraw.Draw(sig_img)
    sbox = [400, 400, 450, 550] # y1, x1, y2, x2
    sdraw.line([(410, 420), (430, 410), (460, 430), (510, 415), (540, 425)], fill=(15, 20, 60), width=2)
    sdraw.line([(400, 440), (545, 440)], fill=(150, 150, 150), width=1)
    
    sig_targeted = detect_signature_presence(sig_img, bbox=sbox)
    assert bool(sig_targeted["presence_detected"]) is True
    
    # Empty region should detect absence
    empty_targeted = detect_signature_presence(sig_img, bbox=[100, 100, 150, 250])
    assert bool(empty_targeted["presence_detected"]) is False


def test_visual_anomaly_detector_and_controlled_tampering():
    from src.landguard_vision.visual_anomaly_baseline import detect_visual_anomalies, inject_controlled_tampering
    
    # Clean document layout with table lines (aligned grid)
    clean = Image.new("RGB", (800, 1000), color=(250, 250, 248))
    draw = ImageDraw.Draw(clean)
    # Draw aligned table header row (multiple adjacent cells)
    for col_x in [100, 250, 400, 550]:
        draw.rectangle([col_x, 150, col_x + 140, 200], outline=(60, 60, 60), width=1)
    
    clean_res = detect_visual_anomalies(clean)
    assert clean_res["has_visual_anomaly"] is False
    
    # Inject controlled isolated paste-over splice
    tampered, meta = inject_controlled_tampering(clean)
    tampered_res = detect_visual_anomalies(tampered)
    assert tampered_res["has_visual_anomaly"] is True
    assert tampered_res["anomaly_count"] >= 1


def test_signature_rejects_low_variance_paper_grain():
    import numpy as np

    rng = np.random.default_rng(12345)
    # Synthetic aged paper grain in [238..248] where naive Otsu previously triggered false positives
    grain = rng.integers(238, 249, size=(1200, 1200, 3), dtype=np.uint8)
    paper_img = Image.fromarray(grain)
    res_assisted = detect_signature_presence(paper_img, bbox=[650, 920, 1100, 1040])
    assert bool(res_assisted["presence_detected"]) is False
    res_unassisted = detect_signature_presence(paper_img, bbox=None)
    assert bool(res_unassisted["presence_detected"]) is False


def test_visual_anomaly_detects_text_adjacent_paste_over():
    from src.landguard_vision.visual_anomaly_baseline import detect_visual_anomalies, inject_controlled_tampering

    # Create dense Sale Deed style document with dark text lines right next to y=420..462
    deed = Image.new("RGB", (1000, 1200), color=(246, 245, 240))
    draw = ImageDraw.Draw(deed)
    for y_line in range(360, 500, 16):
        draw.line([(120, y_line), (850, y_line)], fill=(25, 25, 25), width=2)

    tampered_deed, _ = inject_controlled_tampering(deed)
    res = detect_visual_anomalies(tampered_deed)
    assert res["has_visual_anomaly"] is True
    assert res["anomaly_count"] >= 1

