"""Repo-level regression checks for the split command surface."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestSplitCommandSurface(unittest.TestCase):
    def test_root_package_exposes_canonical_commands(self):
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        for name in [
            "setup",
            "dev",
            "dev:desktop",
            "dev:calendar",
            "dev:journal",
            "build",
            "build:web",
            "build:calendar",
            "build:journal",
            "test",
            "test:qa",
            "test:backend",
            "test:smoke",
        ]:
            self.assertIn(name, scripts)

    def test_runtime_guide_mentions_all_first_class_surfaces(self):
        runtime = (ROOT / "docs" / "dev-runtime.md").read_text(encoding="utf-8")
        for phrase in [
            "Integrated web stack",
            "Desktop shell",
            "Standalone calendar",
            "Standalone journal",
            "/calendar/feed",
            "/calendar/view",
        ]:
            self.assertIn(phrase, runtime)


if __name__ == "__main__":
    unittest.main()
