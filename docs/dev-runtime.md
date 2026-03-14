# Development Runtime Guide

This repo supports four first-class runtime surfaces in one product family:

- **Integrated web stack**: ZoesTM backend + ZoesCal backend + ZoesTM frontend + ZoesCal frontend + ZoesJournal frontend
- **Desktop shell**: Electron shell running against the integrated stack
- **Standalone calendar**: ZoesCal frontend + ZoesCal backend
- **Standalone journal**: ZoesJournal frontend + ZoesTM backend

## Ports

- ZoesTM backend: `8000`
- ZoesTM main frontend: `5173`
- ZoesCal backend: `8001`
- ZoesCal frontend: `5174`
- ZoesJournal frontend: `5175`

## Canonical setup

```bash
npm run setup
```

Bootstrap installs:
- root dependencies
- `apps/frontend`
- `apps/desktop`
- `zoescal/frontend`
- `zoesjournal/frontend`
- backend Python dependencies
- ZoesTM migrations and seed data

## Canonical development flows

### Integrated stack (recommended default)

```bash
npm run dev
```

Starts:
- ZoesTM backend
- ZoesCal backend
- ZoesTM frontend
- ZoesCal frontend
- ZoesJournal frontend

This is the default supported dev/runtime path.

### Desktop shell + integrated stack

```bash
npm run dev:desktop
```

Starts the integrated stack and launches Electron.

On Linux, `dev:desktop-shell` defaults to Electron `--no-sandbox` for local dev unless:

```bash
ZOESTM_ELECTRON_SANDBOX=1 npm run dev:desktop
```

### Standalone calendar

```bash
npm run dev:calendar
```

Starts:
- ZoesCal backend (`8001`)
- ZoesCal frontend (`5174`)

### Standalone journal

```bash
npm run dev:journal
```

Starts:
- ZoesTM backend (`8000`)
- ZoesJournal frontend (`5175`)

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

That means tests and docs must not call `/calendar/view` on the ZoesTM backend.

## Auth expectations

### Local first-party clients

By default, the repo trusts local first-party clients (`localhost`, `127.0.0.1`, `app://`, `file://`) when `ZOESTM_ENFORCE_AUTH` is not enabled.

That means:
- ZoesTM frontend
- ZoesJournal frontend
- Electron shell

can call protected ZoesTM routes locally without manually injecting `X-Token-Scopes`.

### Enforced auth mode

If you enable:

```bash
ZOESTM_ENFORCE_AUTH=1
```

then protected routes require explicit scopes again, including Journal routes such as:
- `read:journal`
- `write:journal`

### Dev bypass

`ZOESTM_DEV_AUTH=1` still exists for explicit test/dev bypass, but it is not required for normal local first-party Journal use.

## Build commands

```bash
npm run build
npm run build:web
npm run build:calendar
npm run build:journal
npm run build:desktop
npm run build:all
```

`npm run build` is the canonical web build path for the three supported frontend surfaces.

## Test commands

```bash
npm test
npm run test:qa
npm run test:backend
npm run test:smoke
```

`npm test` runs the supported repo QA path: backend quality pass, split contract regressions, and smoke coverage for ZoesTM plus ZoesCal.

## Docker

Supported compose path:

```bash
docker-compose up --build
```

`container_name` was removed from compose so repeated runs do not fail on stale fixed-name containers.
