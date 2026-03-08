#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="./.venv/bin/python"

echo "[smoke] syntax"
$PY -m py_compile $(find apps/backend/app -name '*.py')

echo "[smoke] unittests"
$PY -m unittest -q apps.backend.tests.test_services_unittest
$PY -m unittest -q apps.backend.tests.test_integration_outbox_unittest

echo "release smoke: OK"
