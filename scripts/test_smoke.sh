#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "[test:smoke] missing $PY (run npm run setup first)"
  exit 1
fi

export PYTHONPATH=.
TMP_DB="$(mktemp -u /tmp/zoestm-smoke-XXXXXX.db)"
TMP_ZOESCAL_DB="$(mktemp -u /tmp/zoescal-smoke-XXXXXX.db)"
export DB_PATH="$TMP_DB"
export ZOESCAL_DB_PATH="$TMP_ZOESCAL_DB"
trap 'rm -f "$TMP_DB" "$TMP_ZOESCAL_DB"' EXIT

echo "[test:smoke] migrate isolated ZoesTM DB: $DB_PATH"
"$PY" apps/backend/scripts/migrate.py >/dev/null

echo "[test:smoke] migrate isolated ZoesCal DB: $ZOESCAL_DB_PATH"
"$PY" - <<'PY'
from zoescal.backend.app.main import run_migrations
run_migrations()
PY

echo "[test:smoke] endpoint smoke"
./scripts/qa_endpoint_smoke.sh

echo "[test:smoke] frontend/backend smoke"
./scripts/frontend_backend_smoke.sh

echo "[test:smoke] frontend behavior smoke"
./scripts/frontend_behavior_smoke.sh

echo "[test:smoke] zoescal backend smoke"
./scripts/zoescal_backend_smoke.sh

echo "[test:smoke] standalone frontends smoke"
./scripts/standalone_frontends_smoke.sh

echo "test:smoke OK"
