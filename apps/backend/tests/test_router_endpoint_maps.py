import re
import unittest
from pathlib import Path


ROUTERS_DIR = Path(__file__).resolve().parents[1] / "app" / "routers"


class TestRouterEndpointMaps(unittest.TestCase):
    def test_endpoint_map_comment_exists_in_each_router(self):
        router_files = sorted(ROUTERS_DIR.glob("*.py"))
        self.assertTrue(router_files, "No router files found")

        endpoint_line_re = re.compile(r"^#\s*(GET|POST|PUT|PATCH|DELETE)\s+/.+")

        for router_file in router_files:
            with self.subTest(router=router_file.name):
                text = router_file.read_text(encoding="utf-8")
                self.assertIn("# Endpoints map:", text)
                endpoint_lines = [line for line in text.splitlines() if endpoint_line_re.match(line)]
                self.assertGreaterEqual(
                    len(endpoint_lines),
                    1,
                    f"Expected at least one endpoint line in {router_file.name}",
                )


if __name__ == "__main__":
    unittest.main()
