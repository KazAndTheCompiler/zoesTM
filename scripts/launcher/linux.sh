#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "[linux] starting integrated dev stack (backend + TM + Calendar + Journal)"
exec npm run dev
