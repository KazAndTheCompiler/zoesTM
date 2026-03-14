# Development Runtime Guide

This repo supports four first-class runtime surfaces in one product family:

1. **Integrated web stack** — ZoesTM backend + ZoesCal backend + ZoesTM frontend + ZoesCal frontend + ZoesJournal frontend
2. **Desktop shell** — Electron shell running against the integrated stack
3. **Standalone calendar** — ZoesCal frontend + ZoesCal backend
4. **Standalone journal** — ZoesJournal frontend + ZoesTM backend

This doc is the source of truth for setup/dev/build/test commands, runtime ownership, and what root validation actually checks.

## Ports

- ZoesTM backend: `8000`
- ZoesTM frontend: `5173`
- ZoesCal backend: `8001`
- ZoesCal frontend: `5174`
- ZoesJournal frontend: `5175`

## Canonical setup

```bash
npm run setup
```

Bootstrap currently does all of the following:

- creates `.venv`
- installs backend Python dependencies
- runs ZoesTM migrations
- seeds demo data
- installs root npm dependencies
- installs npm dependencies for:
  - `apps/frontend`
  - `apps/desktop`
  - `zoescal/frontend`
  - `zoesjournal/frontend`

If setup behavior changes, update this file and `README.md` together.

## Supported surfaces

### Integrated web path

```bash
npm run dev
```

Starts:
- ZoesTM backend
- ZoesCal backend
- ZoesTM frontend
- ZoesCal frontend
- ZoesJournal frontend

This is the default supported repo runtime path.

### Integrated desktop path

```bash
npm run dev:desktop
```

Starts the integrated stack and launches Electron.

Linux local-dev note:

```bash
ZOESTM_ELECTRON_SANDBOX=1 npm run dev:desktop
```

Without that flag, `dev:desktop-shell` uses Electron `--no-sandbox` on Linux for local development.

### Standalone calendar path

```bash
npm run dev:calendar
```

Starts:
- ZoesCal backend on `8001`
- ZoesCal frontend on `5174`

### Standalone journal path

```bash
npm run dev:journal
```

Starts:
- ZoesTM backend on `8000`
- ZoesJournal frontend on `5175`

## Backend ownership and API boundaries

### ZoesTM backend owns

- tasks, habits, alarms, focus, review, commands, player, journal
- journal export aggregation
- `/calendar/feed` as the mirror feed consumed by ZoesCal

### ZoesCal backend owns

- calendar presentation/runtime endpoints
- `/calendar/view`
- `/calendar/range`
- `/calendar/timeline`
- `/calendar/events` CRUD
- imports and sync overlays

That means tests, scripts, and docs must not call `/calendar/view` on the ZoesTM backend.

## Auth expectations

### Local first-party clients

By default, local first-party clients (`localhost`, `127.0.0.1`, `app://`, `file://`) are trusted when `ZOESTM_ENFORCE_AUTH` is not enabled.

That covers:
- ZoesTM frontend
- ZoesJournal frontend
- Electron shell

### Enforced auth mode

If you enable:

```bash
ZOESTM_ENFORCE_AUTH=1
```

protected ZoesTM routes require explicit scopes again, including journal scopes such as:
- `read:journal`
- `write:journal`

### Dev bypass

`ZOESTM_DEV_AUTH=1` still exists for explicit dev/test bypass, but it is not required for normal first-party local journal use.

## Command matrix

### Setup

| Command | Exists | Scope |
|---|---|---|
| `npm run setup` | yes | Canonical repo bootstrap |
| `npm run bootstrap` | yes | Alias to `npm run setup` |

### Development

| Command | Exists | Scope |
|---|---|---|
| `npm run dev` | yes | Integrated web path |
| `npm run dev:integrated` | yes | Explicit integrated alias |
| `npm run dev:backend` | yes | ZoesTM backend only |
| `npm run dev:frontend` | yes | ZoesTM frontend only |
| `npm run dev:desktop` | yes | Integrated stack + Electron |
| `npm run dev:desktop-shell` | yes | Electron shell only |
| `npm run dev:calendar` | yes | ZoesCal backend + frontend |
| `npm run dev:calendar-backend` | yes | ZoesCal backend only |
| `npm run dev:calendar:frontend` | yes | ZoesCal frontend only |
| `npm run dev:journal` | yes | ZoesTM backend + journal frontend |
| `npm run dev:journal:frontend` | yes | Journal frontend only |

### Build

| Command | Exists | Scope |
|---|---|---|
| `npm run build` | yes | TM + calendar + journal web builds |
| `npm run build:web` | yes | ZoesTM frontend build |
| `npm run build:calendar` | yes | ZoesCal frontend build |
| `npm run build:journal` | yes | ZoesJournal frontend build |
| `npm run build:desktop` | yes | Electron packaging |
| `npm run build:all` | yes | Web builds + desktop packaging |

### Test and lint

| Command | Exists | Scope |
|---|---|---|
| `npm test` | yes | Canonical QA path |
| `npm run test:qa` | yes | Same as `npm test` |
| `npm run test:backend` | yes | Isolated backend + repo-root regression path |
| `npm run test:smoke` | yes | Fast smoke scripts only |
| `npm run lint` | yes | Fast static/type/syntax checks |

## What root validation checks

### Fully covered enough to trust for day-to-day hardening

- backend unit and contract regressions
- repo-root command surface regressions
- ZoesTM API smoke coverage
- ZoesCal backend smoke coverage
- standalone journal frontend contract/config assumptions
- standalone calendar frontend contract/config assumptions
- frontend TypeScript typechecks for TM, calendar, and journal

### Covered lightly on purpose

- desktop runtime behavior from root
  - currently static sanity checks for Electron entrypoints and script wiring
  - not full GUI/Electron automation
- frontend runtime UX
  - smoke checks validate supported contracts and key assumptions
  - not pseudo-E2E browser automation

That tradeoff is intentional: fast checks that catch real split regressions without turning QA into a slow, fragile monster.

## Quick test vs QA path

Use these rules:

- **Quick backend-safe check:** `npm run test:backend`
- **Full repo validation:** `npm test`
- **Fast contract/smoke-only check:** `npm run test:smoke`

`npm run test:backend` now uses the same root assumptions as the QA path:
- isolated temp DB
- root `PYTHONPATH=.`
- migrations applied before running tests
- repo-root regression tests included

So the quick path is still smaller than full QA, but it should not be misleadingly different.

## How to debug regressions

### Auth / scope failures

Look first at:
- `ZOESTM_ENFORCE_AUTH`
- `ZOESTM_DEV_AUTH`
- `zoesjournal/frontend/src/api.ts`
- backend auth contract tests in `apps/backend/tests/test_auth_runtime_contract_unittest.py`

If journal calls suddenly 401 in local dev, check whether explicit scope headers are now required.

### CORS / preflight failures

Look first at:
- the relevant frontend `vite.config.ts`
- whether the frontend is using `/api` proxy mode vs direct `file:` fallback mode
- backend route ownership: ZoesTM vs ZoesCal

If calendar hits the wrong backend, preflight symptoms are often just a routing mistake in disguise.

### Split frontend config problems

Look first at:
- `zoescal/frontend/vite.config.ts`
- `zoesjournal/frontend/vite.config.ts`
- `zoescal/frontend/src/hooks/useCalendar.ts`
- `zoesjournal/frontend/src/api.ts`

Common breakage pattern:
- wrong `base`
- wrong proxy target
- wrong backend ownership assumption

### Setup / bootstrap misses

Look first at:
- `scripts/bootstrap_dev.sh`
- missing `.venv`
- missing `node_modules` in one of the frontend surfaces
- root docs claiming setup installed a package it no longer installs

If one surface fails immediately after setup, confirm bootstrap actually installs that surface's dependencies.

### Root script mismatch problems

Look first at:
- `package.json`
- `README.md`
- this file
- `scripts/test_backend.sh`
- `scripts/qa_runner.sh`
- `scripts/qa_lint.sh`

If docs and scripts disagree, trust `package.json` first, then fix the docs.

## Docker

Supported compose path:

```bash
docker-compose up --build
```

`container_name` was removed from compose so repeated runs do not collide on stale fixed-name containers.
