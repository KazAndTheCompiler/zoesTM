#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Tester Bootstrap Check ==="
FAILED=0

check_cmd() {
  local cmd="$1"
  local name="$2"
  if command -v "$cmd" &>/dev/null; then
    echo "[OK] $name found: $(command -v "$cmd")"
  else
    echo "[FAIL] $name not found in PATH"
    FAILED=1
  fi
}

check_file() {
  local file="$1"
  local name="$2"
  if [ -f "$file" ]; then
    echo "[OK] $name exists: $file"
  else
    echo "[FAIL] $name missing: $file"
    FAILED=1
  fi
}

check_migrations_script() {
  if [ -f "apps/backend/scripts/migrate.py" ]; then
    echo "[OK] Migrations script exists"
  else
    echo "[FAIL] Migrations script missing"
    FAILED=1
  fi
}

echo ""
echo "Checks:"
check_cmd "python3" "Python 3"
check_cmd "node" "Node.js"
check_cmd "npm" "npm"
check_migrations_script
check_file "scripts/bootstrap_dev.sh" "Bootstrap script"

echo ""
if [ $FAILED -eq 0 ]; then
  echo "All checks passed. Canonical bootstrap: npm run setup"
  echo "Direct script equivalent: ./scripts/bootstrap_dev.sh"
  exit 0
else
  echo "Some checks failed. Install prerequisites, then rerun npm run setup (or ./scripts/bootstrap_dev.sh)."
  exit 1
fi
