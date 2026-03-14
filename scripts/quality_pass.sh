#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PY="./.venv/bin/python"

# Isolated test DB so repeated runs are deterministic
TMP_DB="$(mktemp -u /tmp/zoestm-quality-XXXXXX.db)"
export DB_PATH="$TMP_DB"
trap 'rm -f "$TMP_DB"' EXIT

$PY apps/backend/scripts/migrate.py >/dev/null

echo "[1/4] Backend syntax compile"
$PY -m py_compile $(find apps/backend/app -name '*.py' | sort)

echo "[2/4] Endpoint map presence check"
$PY -m unittest -q apps.backend.tests.test_endpoint_maps_unittest

echo "[3/4] Service tests"
$PY -m unittest -q apps.backend.tests.test_services_unittest

echo "[4/4] Integration harness"
$PY -m unittest -q apps.backend.tests.test_integration_outbox_unittest

echo "Quality pass: OK"
