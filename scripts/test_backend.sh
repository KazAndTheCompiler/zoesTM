#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "[test:backend] missing $PY (run npm run setup first)"
  exit 1
fi

export PYTHONPATH=.
TMP_DB="$(mktemp -u /tmp/zoestm-backend-XXXXXX.db)"
export DB_PATH="$TMP_DB"
trap 'rm -f "$TMP_DB"' EXIT

echo "[test:backend] migrate isolated DB: $DB_PATH"
"$PY" apps/backend/scripts/migrate.py >/dev/null

echo "[test:backend] apps/backend/tests"
"$PY" -m unittest discover -s apps/backend/tests -p 'test_*.py' -q

echo "[test:backend] repo-root regression tests"
"$PY" -m unittest discover -s tests -p 'test_*.py' -q

echo "test:backend OK"
