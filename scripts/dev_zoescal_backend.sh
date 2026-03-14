#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"
URL="http://127.0.0.1:8001/health"

if [ ! -x "$PY" ]; then
  echo "[dev:calendar-backend] missing $PY (run ./scripts/bootstrap_dev.sh first)"
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "[dev:calendar-backend] reusing existing ZoesCal backend on :8001"
    while true; do sleep 3600; done
  fi
fi

echo "[dev:calendar-backend] starting ZoesCal backend on :8001"
exec "$PY" -m uvicorn zoescal.backend.app.main:app --reload --port 8001
