#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$(uname -s)" = "Linux" ] && [ "${ZOESTM_ELECTRON_SANDBOX:-0}" != "1" ]; then
  echo "[dev:desktop-shell] Linux detected -> using Electron --no-sandbox for local dev"
  exec npm --prefix apps/desktop run start:linux
fi

echo "[dev:desktop-shell] starting Electron shell"
exec npm --prefix apps/desktop run start
