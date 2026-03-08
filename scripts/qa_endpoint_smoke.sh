#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONPATH=. ./.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from apps.backend.app.main import app
from apps.backend.app.services import webhooks

c = TestClient(app)

checks = []
checks.append(("GET /health", c.get("/health").status_code == 200))
checks.append(("GET /metrics", c.get("/metrics").status_code == 200))
checks.append(("POST /tasks/", c.post("/tasks/", json={"title": "smoke task", "priority": 2}).status_code == 200))
checks.append(("GET /calendar/view", c.get("/calendar/view?mode=day").status_code == 200))
checks.append(("POST /focus/start", c.post("/focus/start?minutes=1").status_code == 200))
checks.append(("POST /commands/preview", c.post("/commands/preview", json={"text": "add task smoke"}).status_code == 200))
checks.append(("GET /boards/kanban", c.get("/boards/kanban").status_code == 200))
checks.append(("GET /review/session", c.get("/review/session").status_code == 200))
checks.append(("POST /review/rate", c.post("/review/rate?state=new&rating=good&interval=1").status_code == 200))
checks.append(("GET /search", c.get("/search?q=smoke&types=tasks&limit=5").status_code == 200))

# webhook receipt write smoke (service-level)
h = webhooks.register("https://example.test/smoke", "smoke-secret")
res = webhooks.deliver_test(h["id"], {"kind": "smoke"})
checks.append(("webhooks.deliver_test writes receipt", res.get("status") == "delivered"))

failed = [name for name, ok in checks if not ok]
if failed:
    raise SystemExit("smoke failed: " + ", ".join(failed))

print("endpoint smoke: OK")
PY
