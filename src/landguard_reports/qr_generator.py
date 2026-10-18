"""LandGuard Verification QR Code Generator.
Generates dynamic QR code images embedding public verification URLs for inclusion
in official verification certificates, PDF dossiers, and public inspection portals.
"""

import os
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def get_public_base_url(provided_base_url: str = None) -> str:
    """Resolves the canonical public base URL:
    1. LANDGUARD_BASE_URL or PUBLIC_BASE_URL env var (if configured for remote demo or production).
    2. Validated localhost/loopback base_url (for local development).
    3. Safe default fallback to 'http://localhost:8000' (rejects arbitrary untrusted Host headers).
    """
    env_base = os.environ.get("LANDGUARD_BASE_URL") or os.environ.get("PUBLIC_BASE_URL")
    if env_base and env_base.strip():
        return env_base.strip().rstrip("/")

    if provided_base_url and provided_base_url.strip():
        from urllib.parse import urlparse
        try:
            parsed = urlparse(provided_base_url.strip())
            hostname = (parsed.hostname or "").lower()
            allowed_local_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "testserver"}
            if hostname in allowed_local_hosts:
                return provided_base_url.strip().rstrip("/")
        except Exception:
            pass

    return "http://localhost:8000"


def generate_verification_qr(
    verification_id: str,
    base_url: str = None,
    box_size: int = 8,
    border: int = 2,
) -> bytes:
    """
    Generates PNG bytes for a QR code linking to the sanitized public verification URL.
    Respects PUBLIC_BASE_URL environment variable with fallback to base_url or localhost.
    """
    clean_base = get_public_base_url(base_url)
    verification_url = f"{clean_base}/verify/public/{verification_id.strip()}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def decode_verification_qr(png_bytes: bytes) -> str:
    """
    Decodes the URL embedded in a LandGuard QR code PNG image using OpenCV.
    Useful for automated verification and regression testing.
    """
    import cv2
    import numpy as np

    nparr = np.frombuffer(png_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode PNG image bytes.")

    detector = cv2.QRCodeDetector()
    decoded_text, points, _ = detector.detectAndDecode(img)
    return decoded_text
