import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CAL_FRONTEND = ROOT / 'zoescal' / 'frontend'


class TestZoesCalSplit(unittest.TestCase):
    def test_zoescal_frontend_surface_exists(self):
        required = [
            'package.json',
            'index.html',
            'vite.config.ts',
            'src/App.tsx',
            'src/api.ts',
            'src/main.tsx',
            'src/hooks/useCalendar.ts',
            'src/components/DayView.tsx',
            'src/components/WeekView.tsx',
            'src/components/MonthView.tsx',
        ]
        for relative in required:
            self.assertTrue((CAL_FRONTEND / relative).exists(), relative)

    def test_zoescal_package_has_standalone_scripts(self):
        pkg = json.loads((CAL_FRONTEND / 'package.json').read_text(encoding='utf-8'))
        scripts = pkg['scripts']
        self.assertEqual(pkg['name'], 'zoescal-frontend')
        self.assertEqual(scripts['dev'], 'vite')
        self.assertEqual(scripts['build'], 'tsc -b && vite build')
        self.assertEqual(scripts['typecheck'], 'tsc --noEmit')

    def test_zoescal_vite_and_api_contract_point_at_calendar_backend(self):
        vite = (CAL_FRONTEND / 'vite.config.ts').read_text(encoding='utf-8')
        api = (CAL_FRONTEND / 'src' / 'api.ts').read_text(encoding='utf-8')
        hook = (CAL_FRONTEND / 'src' / 'hooks' / 'useCalendar.ts').read_text(encoding='utf-8')
        app = (CAL_FRONTEND / 'src' / 'App.tsx').read_text(encoding='utf-8')

        self.assertIn("base: '/zoescal/'", vite)
        self.assertIn('port: 5174', vite)
        self.assertIn("target: 'http://127.0.0.1:8001'", vite)
        self.assertIn("'http://127.0.0.1:8001'", api)
        self.assertIn('/calendar/view?mode=', hook)
        self.assertIn('/calendar/events', hook)
        self.assertIn("const [mode, setMode]         = useState<CalMode>('day')", app)
        self.assertIn('<DayView', app)
        self.assertIn('<WeekView', app)
        self.assertIn('<MonthView', app)

    def test_repo_root_scripts_reference_zoescal_consistently(self):
        pkg = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
        scripts = pkg['scripts']
        self.assertEqual(scripts['dev:calendar'], 'concurrently -n cal-api,calendar -c cyan,magenta "npm run dev:calendar-backend" "npm run dev:calendar:frontend"')
        self.assertEqual(scripts['dev:calendar:frontend'], 'npm --prefix zoescal/frontend run dev')
        self.assertEqual(scripts['build:calendar'], 'npm --prefix zoescal/frontend run build')
        self.assertIn('build:calendar', scripts['build'])


if __name__ == '__main__':
    unittest.main()
