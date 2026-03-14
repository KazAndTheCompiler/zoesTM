#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[dev:desktop] starting integrated stack + desktop shell"
echo "[dev:desktop] if Electron exits on your Linux sandbox, the stack will keep running"
exec npx concurrently -n stack,desktop -c cyan,magenta "npm run dev:stack" "npm run dev:desktop-shell"
