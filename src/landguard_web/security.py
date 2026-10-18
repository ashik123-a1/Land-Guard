"""LandGuard Security & Cryptography Utilities
Provides PBKDF2-HMAC-SHA256 password hashing, constant-time verification,
and credential protection compliant with SRS v5 Section 14.
"""

import hashlib
import hmac
import secrets
from typing import Optional


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a cryptographically
    secure 16-byte random salt.
    Format: pbkdf2_sha256$<iterations>$<salt>$<hex_digest>
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256$100000${salt}${dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored hash using constant-time comparison.
    Supports PBKDF2-HMAC-SHA256 hashes and backward-compatible verification for existing demo accounts.
    """
    if not stored_hash or not plain_password:
        return False

    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$")
        if len(parts) == 4:
            salt = parts[2]
            expected = parts[3]
            dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000)
            return hmac.compare_digest(dk.hex(), expected)

    # Legacy demo credentials backward-compatibility fallback
    return hmac.compare_digest(plain_password, stored_hash)


import os
from typing import Dict, Any

SECRET_KEY = os.getenv("SECRET_KEY", "landguard-dev-prototype-secret-key-32chars-minimum-replace-in-prod")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()


def check_production_security() -> Dict[str, Any]:
    """Validates production security requirements."""
    is_prod = ENVIRONMENT == "production"
    is_secure_secret = bool(
        SECRET_KEY
        and SECRET_KEY != "landguard-dev-prototype-secret-key-32chars-minimum-replace-in-prod"
        and len(SECRET_KEY) >= 32
    )
    demo_login_allowed = not is_prod or os.getenv("ALLOW_DEMO_LOGIN_IN_PROD", "").lower() == "true"
    return {
        "environment": ENVIRONMENT,
        "is_production": is_prod,
        "secret_key_configured": is_secure_secret if is_prod else True,
        "demo_login_enabled": demo_login_allowed,
        "ssl_required": is_prod,
    }

