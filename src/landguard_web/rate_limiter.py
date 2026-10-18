"""LandGuard Lightweight In-Memory Rate Limiter.
Provides thread-safe sliding-window rate limiting per client IP or user token.
Zero external Redis or database dependency, works cleanly in multi-threaded FastAPI workers.
"""

import os
import time
import threading
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status


class SlidingWindowRateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """Checks if a request key exceeds max_requests within window_seconds.
        Returns True if allowed, False if limit exceeded.
        """
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            # Clean up timestamps older than window
            timestamps = [t for t in self._requests[key] if t > cutoff]
            if len(timestamps) >= max_requests:
                self._requests[key] = timestamps
                return False
            timestamps.append(now)
            self._requests[key] = timestamps
            return True

    def reset(self):
        """Resets all tracked rate limit buckets (useful for tests)."""
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting X-Forwarded-For only if explicitly configured."""
    trust_forwarded = os.getenv("LANDGUARD_TRUST_FORWARDED_FOR", "").lower() in ("1", "true", "yes")
    if trust_forwarded:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def enforce_rate_limit(
    request: Request,
    scope: str,
    max_requests: int = 15,
    window_seconds: int = 60,
):
    """Enforces rate limit for a specific endpoint scope.
    Respects test mode bypass unless LANDGUARD_ENFORCE_TEST_RATE_LIMIT=1 is set.
    """
    if os.getenv("LANDGUARD_TEST_MODE") == "1" and os.getenv("LANDGUARD_ENFORCE_TEST_RATE_LIMIT") != "1":
        return

    ip = get_client_ip(request)
    key = f"{scope}:{ip}"
    allowed = rate_limiter.check_rate_limit(key, max_requests=max_requests, window_seconds=window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {scope}. Please wait before making more requests.",
            headers={"Retry-After": str(window_seconds)},
        )


check_rate_limit = enforce_rate_limit
