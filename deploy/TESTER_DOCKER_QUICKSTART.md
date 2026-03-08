# TESTER_DOCKER_QUICKSTART

Minimal Docker path for field testers.

## Prerequisites
- Docker + Docker Compose plugin installed

## 1) Configure env
From repo root:

```bash
cp .env.example .env
```

Edit `.env` as needed (minimum recommended):

```bash
ZOESTM_DEV_AUTH=1
PORT=8000
WEBHOOK_SIGNING_KEY=change-me
ENVIRONMENT=development
```

## 2) Build and run

```bash
docker compose up --build -d
```

## 3) Verify health

```bash
curl -fsS http://localhost:${PORT:-8000}/health
```

Expected: JSON with `ok: true`.

## 4) Stop

```bash
docker compose down
```

To also remove persisted DB volume:

```bash
docker compose down -v
```

## Notes
- API is exposed on `${PORT}` (default `8000`).
- SQLite DB persists in Docker volume `zoestm-db`.
- Container startup runs migrations automatically.
