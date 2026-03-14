#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"
URL="http://127.0.0.1:8000/health"

if [ ! -x "$PY" ]; then
  echo "[dev:backend] missing $PY (run npm run setup first)"
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "[dev:backend] reusing existing backend on :8000"
    while true; do sleep 3600; done
  fi
fi

echo "[dev:backend] starting uvicorn on :8000"
exec "$PY" -m uvicorn apps.backend.app.main:app --reload --port 8000
