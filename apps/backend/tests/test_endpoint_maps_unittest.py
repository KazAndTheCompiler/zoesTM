import unittest
from pathlib import Path


class TestEndpointMaps(unittest.TestCase):
    def test_all_router_files_have_endpoint_map_block(self):
        routers_dir = Path(__file__).resolve().parents[1] / "app" / "routers"
        missing = []
        for py in sorted(routers_dir.glob("*.py")):
            if py.name.startswith("__"):
                continue
            text = py.read_text(encoding="utf-8")
            if "# Endpoints map:" not in text or "# Owner:" not in text:
                missing.append(py.name)
        self.assertEqual(missing, [], f"Missing endpoint map or owner block in: {missing}")


if __name__ == "__main__":
    unittest.main()
