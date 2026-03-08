#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[audit] endpoint maps in routers"
missing=0
for f in $(find apps/backend/app/routers -name '*.py'); do
  if ! grep -q '# Endpoints map:' "$f"; then
    echo "Missing '# Endpoints map:' in $f"
    missing=1
  fi
  if ! grep -q '# Owner:' "$f"; then
    echo "Missing '# Owner:' in $f"
    missing=1
  fi
done
if [ $missing -ne 0 ]; then
  exit 1
fi
echo "Endpoint map audit: OK"
