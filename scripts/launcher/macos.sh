#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
PY="./.venv/bin/python"
echo "[macOS] starting Zoe'sTM backend API (dev)"
$PY -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000
