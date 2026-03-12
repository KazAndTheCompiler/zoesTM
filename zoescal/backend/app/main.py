import os
import time
import uuid
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .errors import ApiError, error_payload
from .routers import calendar, google_auth
from .db import conn
from pathlib import Path
from .services.google_integration import google_sync_loop
from .services.zoestm_sync import zoestm_sync_loop


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def run_migrations():
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    with conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.commit()
        applied = {r[0] for r in c.execute("SELECT name FROM _migrations").fetchall()}

    for sql_file in sorted(migrations_dir.glob("*.sql")):
        if sql_file.name not in applied:
            sql = sql_file.read_text()
            with conn() as c:
                c.executescript(sql)
                c.execute("INSERT INTO _migrations(name) VALUES(?)", (sql_file.name,))
                c.commit()
            print(f"[zoescal] Applied migration: {sql_file.name}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    stop_event = asyncio.Event()
    sync_task = asyncio.create_task(google_sync_loop(stop_event))
    zoestm_task = asyncio.create_task(zoestm_sync_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        sync_task.cancel()
        zoestm_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
        try:
            await zoestm_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="ZoesCal API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "app://.",
        "file://",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    if elapsed_ms > 500:
        print(
            json.dumps(
                {
                    "event": "slow_route",
                    "path": request.url.path,
                    "elapsed_ms": elapsed_ms,
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
        message = detail.get("message", str(code))
        details = detail.get("details")
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


app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(google_auth.router, prefix="/auth/google", tags=["google-auth"])


@app.get("/health")
def health():
    db_ok = True
    try:
        with conn() as c:
            c.execute("SELECT 1").fetchone()
    except Exception:
        db_ok = False
    return {"ok": db_ok, "app": "zoescal", "version": "0.1.0"}
