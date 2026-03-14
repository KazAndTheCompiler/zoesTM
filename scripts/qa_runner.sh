#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export PYTHONPATH=.
PY="./.venv/bin/python"

# Isolated test DB so local dev DB state doesn't affect results
TMP_DB="$(mktemp -u /tmp/zoestm-test-XXXXXX.db)"
export DB_PATH="$TMP_DB"
trap 'rm -f "$TMP_DB"' EXIT

$PY apps/backend/scripts/migrate.py >/dev/null

echo "[qa] lint"
./scripts/qa_lint.sh

echo "[qa] unit and contract tests"
$PY -m unittest -q apps.backend.tests.test_endpoint_maps_unittest
$PY -m unittest -q apps.backend.tests.test_services_unittest
$PY -m unittest -q apps.backend.tests.test_prototype_batch_unittest
$PY -m unittest -q apps.backend.tests.test_qa_round1_unittest
$PY -m unittest -q apps.backend.tests.test_qa_round2_unittest
$PY -m unittest -q apps.backend.tests.test_integration_outbox_unittest
$PY -m unittest -q apps.backend.tests.test_qa_round3_unittest
$PY -m unittest -q apps.backend.tests.test_task_filtering_pagination_unittest
$PY -m unittest -q apps.backend.tests.test_auth_runtime_contract_unittest
$PY -m unittest -q apps.backend.tests.test_zoesjournal_split_unittest
$PY -m unittest -q apps.backend.tests.test_zoescal_split_unittest
$PY -m unittest discover -s tests -p "test_*.py" -q

echo "[qa] smoke"
./scripts/test_smoke.sh

echo "qa runner: OK"
