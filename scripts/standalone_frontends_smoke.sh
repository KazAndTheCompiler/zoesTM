#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONPATH=. ./.venv/bin/python - <<'PY'
import json
from pathlib import Path

root = Path('.')

checks = []

journal_pkg = json.loads((root / 'zoesjournal' / 'frontend' / 'package.json').read_text(encoding='utf-8'))
journal_vite = (root / 'zoesjournal' / 'frontend' / 'vite.config.ts').read_text(encoding='utf-8')
journal_api = (root / 'zoesjournal' / 'frontend' / 'src' / 'api.ts').read_text(encoding='utf-8')
journal_app = (root / 'zoesjournal' / 'frontend' / 'src' / 'App.tsx').read_text(encoding='utf-8')
checks.extend([
    ('journal has vite dev script', journal_pkg.get('scripts', {}).get('dev') == 'vite'),
    ('journal has build script', 'build' in journal_pkg.get('scripts', {})),
    ('journal vite base path', "base: '/zoesjournal/'" in journal_vite),
    ('journal vite port 5175', 'port: 5175' in journal_vite),
    ('journal targets ZoesTM backend', "http://127.0.0.1:8000" in journal_vite and '/journal/by-date/' in journal_app and '/journal/export/' in journal_app),
    ('journal preserves scope header support', 'X-Token-Scopes' in journal_api),
    ('journal exposes history/export views', "'history' | 'export'" in journal_app),
])

calendar_pkg = json.loads((root / 'zoescal' / 'frontend' / 'package.json').read_text(encoding='utf-8'))
calendar_vite = (root / 'zoescal' / 'frontend' / 'vite.config.ts').read_text(encoding='utf-8')
calendar_api = (root / 'zoescal' / 'frontend' / 'src' / 'api.ts').read_text(encoding='utf-8')
calendar_hook = (root / 'zoescal' / 'frontend' / 'src' / 'hooks' / 'useCalendar.ts').read_text(encoding='utf-8')
checks.extend([
    ('calendar has vite dev script', calendar_pkg.get('scripts', {}).get('dev') == 'vite'),
    ('calendar has build script', 'build' in calendar_pkg.get('scripts', {})),
    ('calendar vite base path', "base: '/zoescal/'" in calendar_vite),
    ('calendar vite port 5174', 'port: 5174' in calendar_vite),
    ('calendar targets ZoesCal backend', "http://127.0.0.1:8001" in calendar_vite),
    ('calendar reads /calendar/view', '/calendar/view?mode=' in calendar_hook),
    ('calendar writes /calendar/events', "/calendar/events" in calendar_hook and 'jpost' in calendar_hook),
    ('calendar file mode fallback uses direct backend URL', "http://127.0.0.1:8001" in calendar_api),
])

failed = [name for name, ok in checks if not ok]
if failed:
    raise SystemExit('standalone frontends smoke failed: ' + ', '.join(failed))

print('standalone frontends smoke: OK')
PY
