#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="./.venv/bin/python"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[lint] missing required command: $1"
    exit 1
  fi
}

require_file() {
  if [ ! -f "$1" ]; then
    echo "[lint] missing expected file: $1"
    exit 1
  fi
}

require_cmd npm
require_cmd node

if [ ! -x "$PY" ]; then
  echo "[lint] missing $PY (run npm run setup first)"
  exit 1
fi

require_file package.json
require_file apps/frontend/package.json
require_file apps/desktop/package.json
require_file zoescal/frontend/package.json
require_file zoesjournal/frontend/package.json

echo "[lint 1/8] backend python compile"
"$PY" -m py_compile $(find apps/backend/app -name '*.py' | sort)

echo "[lint 2/8] backend test compile"
"$PY" -m py_compile $(find apps/backend/tests -name '*.py' | sort)

echo "[lint 3/8] root helper scripts syntax"
for f in scripts/*.sh; do
  bash -n "$f"
done
"$PY" -m py_compile scripts/run_supervisor.py

echo "[lint 4/8] desktop helper sanity"
node --check apps/desktop/main.js
node --check apps/desktop/preload.js
node - <<'NODE'
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('apps/desktop/package.json', 'utf8'));
if (!pkg.scripts || !pkg.scripts.start || !pkg.scripts.build) {
  console.error('[lint] desktop package.json must define start and build scripts');
  process.exit(1);
}
const main = fs.readFileSync('apps/desktop/main.js', 'utf8');
if (!main.includes('http://127.0.0.1:5173')) {
  console.error('[lint] desktop main.js must target the integrated TM frontend dev server on :5173');
  process.exit(1);
}
NODE

echo "[lint 5/8] TM frontend typecheck"
npm --prefix apps/frontend run typecheck -- --pretty false

echo "[lint 6/8] calendar frontend typecheck"
npm --prefix zoescal/frontend run typecheck -- --pretty false

echo "[lint 7/8] journal frontend typecheck"
npm --prefix zoesjournal/frontend run typecheck -- --pretty false

echo "[lint 8/8] split boundary audits"
./scripts/audit_endpoint_maps.sh
"$PY" -m unittest -q apps.backend.tests.test_zoesjournal_split_unittest
"$PY" -m unittest -q apps.backend.tests.test_zoescal_split_unittest

echo "lint: OK"
