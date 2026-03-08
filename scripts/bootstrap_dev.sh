#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[bootstrap] python venv"
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r apps/backend/requirements-dev.txt

echo "[bootstrap] migrations"
.venv/bin/python apps/backend/scripts/migrate.py

echo "[bootstrap] seed demo data"
.venv/bin/python apps/backend/scripts/seed.py

echo "[bootstrap] node deps"
npm install
npm --prefix apps/frontend install
npm --prefix apps/desktop install

echo "[bootstrap] done. Run: npm run dev"
