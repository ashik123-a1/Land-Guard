#!/usr/bin/env bash
# ==============================================================================
# LandGuard AI — Fast Startup Script for GitHub Codespaces / Linux
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

echo "==============================================================================="
echo "       LANDGUARD AI - BILINGUAL STATUTORY LAND RECORD VERIFICATION             "
echo "                      GitHub Codespaces Cloud Gateway                          "
echo "==============================================================================="
echo ""
echo "[*] Checking Python environment..."
python -m pip install --quiet --upgrade pip 2>/dev/null || true

echo "[*] Starting FastAPI ASGI web server on 0.0.0.0:8000..."
echo "[*] Live Endpoint: http://0.0.0.0:8000 (Forwarded via Codespaces)"
echo ""

python -m uvicorn src.landguard_web.app:app --host 0.0.0.0 --port 8000 --reload
