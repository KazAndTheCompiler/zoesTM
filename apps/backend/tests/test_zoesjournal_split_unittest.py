import json
import unittest
from pathlib import Path


class TestZoesJournalSplit(unittest.TestCase):
    def test_zoesjournal_frontend_surface_exists(self):
        root = Path(__file__).resolve().parents[3]
        frontend = root / 'zoesjournal' / 'frontend'
        self.assertTrue((frontend / 'package.json').exists())
        self.assertTrue((frontend / 'index.html').exists())
        self.assertTrue((frontend / 'src' / 'App.tsx').exists())
        self.assertTrue((frontend / 'src' / 'api.ts').exists())
        self.assertTrue((frontend / 'src' / 'styles.css').exists())

    def test_zoesjournal_package_has_standalone_scripts(self):
        root = Path(__file__).resolve().parents[3]
        pkg = json.loads((root / 'zoesjournal' / 'frontend' / 'package.json').read_text())
        self.assertEqual(pkg['scripts']['dev'], 'vite')
        self.assertIn('build', pkg['scripts'])

    def test_repo_root_scripts_reference_zoesjournal(self):
        root = Path(__file__).resolve().parents[3]
        pkg = json.loads((root / 'package.json').read_text())
        self.assertIn('dev:journal', pkg['scripts'])
        self.assertIn('build:journal', pkg['scripts'])


if __name__ == '__main__':
    unittest.main()
