"""Assert that all agent models are whitelisted in the lockdown config."""
import json
import os
import unittest

CONFIG_PATH = "config/openclaw.lockdown.json"

class TestModelLockdown(unittest.TestCase):
    def test_agents_in_whitelist(self):
        self.assertTrue(os.path.exists(CONFIG_PATH), f"Lockdown config missing: {CONFIG_PATH}")
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        whitelist = set(cfg.get("whitelist", []))
        agents = cfg.get("agents", {})
        for aid, amodel in agents.items():
            self.assertIn(amodel, whitelist, f"Agent {aid} model {amodel} not in whitelist")

if __name__ == "__main__":
    unittest.main()

