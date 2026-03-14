import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .errors import ApiError, error_payload
from .routers import (
    tasks,
    calendar,
    focus,
    alarms,
    habits,
    boards,
    review,
    commands,
    player,
    goggins,
    journal,
)
from .routers import integrations, meta, ops, notifications, search, health
from .routers import anki_apkg
from .services.outbox_worker import snapshot_metrics
from .services import alarm_scheduler
from .db import conn, close_connection
from .config import settings


def run_migrations():
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    with conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            r[0] for r in c.execute("SELECT name FROM schema_migrations").fetchall()
        }
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name in applied:
                continue
            c.executescript(sql_file.read_text())
            c.execute("INSERT INTO schema_migrations(name) VALUES(?)", (sql_file.name,))
        c.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    # Archive any stale alarm_trigger notifications so old ones don't fire on restart
    try:
        from .services import notifications as notif_svc

        notif_svc.clear_scope("alarm_trigger")
    except Exception:
        pass
    alarm_scheduler.start()
    yield
    alarm_scheduler.stop()
    close_connection()


app = FastAPI(title="Zoe'sTM API", version="1.0.0-rc1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    trace_id = request.headers.get("x-trace-id") or request_id
    request.state.trace_id = trace_id
    # Optional broad auth guard for non-local deployments.
    if os.getenv("ZOESTM_ENFORCE_AUTH", "0") == "1":
        public_paths = {
            "/health",
            "/health/detail",
            "/meta/openapi",
            "/meta/version",
            "/metrics",
        }
        if request.url.path not in public_paths and not request.headers.get(
            "x-token-scopes"
        ):
            payload = error_payload(
                "auth_required", "Missing authentication scopes header"
            )
            payload["error"]["request_id"] = request_id
            return JSONResponse(status_code=401, content=payload)

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-trace-id"] = trace_id
    if elapsed_ms > 500:
        print(
            json.dumps(
                {
                    "event": "slow_route",
                    "path": request.url.path,
                    "elapsed_ms": elapsed_ms,
                    "request_id": request_id,
                }
            )
        )
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    payload = error_payload(exc.code, exc.message, exc.details)
    payload["error"]["request_id"] = getattr(request.state, "request_id", "")
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "http_error")
        message = detail.get("message", str(code).replace("_", " "))
        details = detail.get("details") or {
            k: v for k, v in detail.items() if k not in ("code", "message")
        }
    else:
        code = "http_error"
        message = str(detail or "HTTP error")
        details = None
    payload = error_payload(code, message, details)
    payload["error"]["request_id"] = getattr(request.state, "request_id", "")
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    payload = error_payload("validation_error", "Validation failed", exc.errors())
    payload["error"]["request_id"] = getattr(request.state, "request_id", "")
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    payload = error_payload("internal_error", str(exc))
    payload["error"]["request_id"] = getattr(request.state, "request_id", "")
    return JSONResponse(status_code=500, content=payload)


app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(focus.router, prefix="/focus", tags=["focus"])
app.include_router(alarms.router, prefix="/alarms", tags=["alarms"])
app.include_router(habits.router, prefix="/habits", tags=["habits"])
app.include_router(boards.router, prefix="/boards", tags=["boards"])
app.include_router(anki_apkg.router, prefix="/anki-apkg", tags=["anki-apkg"])
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(commands.router, prefix="/commands", tags=["commands"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
app.include_router(meta.router, prefix="/meta", tags=["meta"])
app.include_router(ops.router, prefix="/ops", tags=["ops"])
app.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(player.router, prefix="/player", tags=["player"])
app.include_router(goggins.router, prefix="/goggins", tags=["goggins"])
app.include_router(journal.router, prefix="/journal", tags=["journal"])
app.include_router(health.router, tags=["health"])
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "static"),
    name="static",
)


@app.get("/health")
def health_status():
    m = snapshot_metrics()
    db_ok = True
    try:
        with conn() as c:
            c.execute("SELECT 1").fetchone()
    except Exception:
        db_ok = False
    return {
        "ok": db_ok,
        "dependencies": {"db": "ok" if db_ok else "error", "outbox": m},
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    m = snapshot_metrics()
    return "\n".join(
        [
            "# TYPE zoestm_outbox_pending gauge",
            f"zoestm_outbox_pending {m['outbox_pending']}",
            "# TYPE zoestm_outbox_retry_wait gauge",
            f"zoestm_outbox_retry_wait {m['outbox_retry_wait']}",
            "# TYPE zoestm_outbox_sent counter",
            f"zoestm_outbox_sent {m['outbox_sent']}",
        ]
    )
