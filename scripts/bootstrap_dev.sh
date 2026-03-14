#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "[bootstrap] python3 is required"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[bootstrap] npm is required"
  exit 1
fi

echo "[bootstrap] python venv"
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r apps/backend/requirements-dev.txt

echo "[bootstrap] migrations"
.venv/bin/python apps/backend/scripts/migrate.py

echo "[bootstrap] seed demo data"
.venv/bin/python apps/backend/scripts/seed.py

echo "[bootstrap] node deps (root + all frontends + desktop)"
npm install
npm --prefix apps/frontend install
npm --prefix apps/desktop install
npm --prefix zoescal/frontend install
npm --prefix zoesjournal/frontend install

echo "[bootstrap] done. Canonical flows:"
echo "  integrated stack: npm run dev"
echo "  desktop shell + stack: npm run dev:desktop"
echo "  standalone calendar: npm run dev:calendar"
echo "  standalone journal: npm run dev:journal"
