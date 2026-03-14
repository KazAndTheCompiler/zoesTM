#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[smoke] api integration paths"
./.venv/bin/python -m unittest -q apps.backend.tests.test_prototype_batch_unittest

echo "frontend/backend smoke: OK"
