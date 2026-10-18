#!/usr/bin/env bash
# ==============================================================================
# LandGuard AI — Fast Startup Script for GitHub Codespaces / Linux
# ==============================================================================

set -e

echo "=== LandGuard AI Verification Engine ==="
echo "Starting FastAPI ASGI web server on 0.0.0.0:8000..."

python -m uvicorn src.landguard_web.app:app --host 0.0.0.0 --port 8000
