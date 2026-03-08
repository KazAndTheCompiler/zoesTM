Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot "../..")
Write-Host "[windows] starting Zoe'sTM backend API (dev)"
$venvPython = Join-Path (Get-Location) ".venv/Scripts/python.exe"
if (Test-Path $venvPython) {
  & $venvPython -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000
} else {
  python -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000
}
