#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="./.venv/bin/python"

echo "[lint] backend python compile"
$PY -m py_compile $(find apps/backend/app -name '*.py')

echo "[lint] backend tests compile"
$PY -m py_compile $(find apps/backend/tests -name '*.py')

echo "[lint] frontend static checks"
grep -q "createRoot" apps/frontend/src/main.tsx
grep -q "function App" apps/frontend/src/App.tsx

./scripts/audit_endpoint_maps.sh

echo "lint: OK"
