# Development Runtime Guide

This repo has three frontend/runtime stories sharing the same product family:

- **Zoe'sTM desktop-integrated stack**: main TM UI + ZoesCal backend/frontend + ZoesJournal frontend + optional Electron shell
- **ZoesCal standalone**: mobile-oriented calendar client + ZoesCal backend
- **ZoesJournal standalone**: mobile-oriented journal client + ZoesTM backend journal routes

## Ports

- ZoesTM backend: `8000`
- ZoesTM main frontend: `5173`
- ZoesCal backend: `8001`
- ZoesCal frontend: `5174`
- ZoesJournal frontend: `5175`

## Canonical setup

```bash
./scripts/bootstrap_dev.sh
```

Bootstrap installs:
- root dependencies
- `apps/frontend`
- `apps/desktop`
- `zoescal/frontend`
- `zoesjournal/frontend`
- backend Python dependencies

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

This is the safest default validation path because Electron failure will not kill the whole stack.

### Desktop shell + integrated stack

```bash
npm run dev:desktop
```

Starts the integrated stack and also launches Electron.

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

Optional scope headers can still be supplied by clients through `X-Token-Scopes`.

### Dev bypass

`ZOESTM_DEV_AUTH=1` still exists for explicit test/dev bypass, but it is no longer required for normal local first-party Journal use.

## Build commands

```bash
npm run build
npm run build:calendar
npm run build:journal
npm run build:desktop
```

## Docker

Supported compose path:

```bash
docker-compose up --build
```

`container_name` was removed from compose so repeated runs do not fail on stale fixed-name containers.
