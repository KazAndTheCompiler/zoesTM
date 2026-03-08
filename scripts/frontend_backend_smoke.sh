#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[smoke] api integration paths"
./.venv/bin/python -m unittest -q apps.backend.tests.test_prototype_batch_unittest

echo "[smoke] frontend behavior checks"
./scripts/frontend_behavior_smoke.sh

echo "frontend/backend smoke: OK"
