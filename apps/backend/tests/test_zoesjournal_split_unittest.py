import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
JOURNAL_FRONTEND = ROOT / 'zoesjournal' / 'frontend'


class TestZoesJournalSplit(unittest.TestCase):
    def test_zoesjournal_frontend_surface_exists(self):
        required = [
            'package.json',
            'index.html',
            'vite.config.ts',
            'src/App.tsx',
            'src/api.ts',
            'src/main.tsx',
            'src/styles.css',
            'src/lib/markdown.ts',
        ]
        for relative in required:
            self.assertTrue((JOURNAL_FRONTEND / relative).exists(), relative)

    def test_zoesjournal_package_has_standalone_scripts(self):
        pkg = json.loads((JOURNAL_FRONTEND / 'package.json').read_text(encoding='utf-8'))
        scripts = pkg['scripts']
        self.assertEqual(pkg['name'], 'zoesjournal-frontend')
        self.assertEqual(scripts['dev'], 'vite')
        self.assertEqual(scripts['build'], 'tsc -b && vite build')
        self.assertEqual(scripts['typecheck'], 'tsc --noEmit')

    def test_zoesjournal_vite_and_api_contract_point_at_tm_backend(self):
        vite = (JOURNAL_FRONTEND / 'vite.config.ts').read_text(encoding='utf-8')
        api = (JOURNAL_FRONTEND / 'src' / 'api.ts').read_text(encoding='utf-8')
        app = (JOURNAL_FRONTEND / 'src' / 'App.tsx').read_text(encoding='utf-8')

        self.assertIn("base: '/zoesjournal/'", vite)
        self.assertIn('port: 5175', vite)
        self.assertIn("target: 'http://127.0.0.1:8000'", vite)
        self.assertIn("'http://127.0.0.1:8000'", api)
        self.assertIn('X-Token-Scopes', api)
        self.assertIn('/journal/by-date/', app)
        self.assertIn('/journal/export/', app)
        self.assertIn('One entry per day', app)
        self.assertIn('Backdating is supported', app)

    def test_repo_root_scripts_reference_zoesjournal_consistently(self):
        pkg = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
        scripts = pkg['scripts']
        self.assertEqual(scripts['dev:journal'], 'concurrently -n api,journal -c cyan,yellow "npm run dev:backend" "npm run dev:journal:frontend"')
        self.assertEqual(scripts['dev:journal:frontend'], 'npm --prefix zoesjournal/frontend run dev')
        self.assertEqual(scripts['build:journal'], 'npm --prefix zoesjournal/frontend run build')
        self.assertIn('build:journal', scripts['build'])


if __name__ == '__main__':
    unittest.main()
