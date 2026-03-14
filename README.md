# ZoesTM + ZoesCal + ZoesJournal

> A free, local-first productivity tool built by someone with AuDHD who got tired of paying monthly for basic scaffolding.

**ZoesTM** is the execution side: tasks, habits, alarms, focus, review, commands, and the desktop shell.

**ZoesCal** is the standalone calendar side: day, week, and month views, skins, sync overlays, and imported mirrors from ZoesTM.

**ZoesJournal** is the standalone mobile-first journal companion over the existing ZoesTM journal API.

It is free. It stays free.

---

## Split release status

- `main` tracks the split architecture release line
- `release/v1.0.0` preserves the older all-in-one skeleton release
- This repo now supports four first-class surfaces:
  - integrated web path
  - integrated desktop path
  - standalone calendar path
  - standalone journal path

## Repo layout

- `apps/backend` — ZoesTM FastAPI backend
- `apps/frontend` — ZoesTM React frontend
- `apps/desktop` — Electron desktop shell
- `zoescal/backend` — ZoesCal FastAPI backend
- `zoescal/frontend` — ZoesCal React/Vite frontend
- `zoesjournal/frontend` — ZoesJournal React/Vite frontend
- `docs/dev-runtime.md` — runtime, command matrix, validation scope, and debugging notes

## Stack

| Layer | Tech |
|---|---|
| ZoesTM backend | FastAPI + SQLite |
| ZoesTM frontend | React + Vite + TypeScript |
| ZoesCal backend | FastAPI + SQLite |
| ZoesCal frontend | React + Vite + TypeScript |
| ZoesJournal frontend | React + Vite + TypeScript |
| Desktop shell | Electron |
| Testing | Python unittest + smoke scripts + frontend typechecks |

## Canonical setup

```bash
npm run setup
```

`npm run setup` is the repo bootstrap path. It currently does all of the following:

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

If that list changes, update this README and `docs/dev-runtime.md` together.

## Supported surfaces

### 1) Integrated web path

```bash
npm run dev
```

Starts:
- ZoesTM backend
- ZoesCal backend
- ZoesTM frontend
- ZoesCal frontend
- ZoesJournal frontend

This is the default repo dev path.

### 2) Integrated desktop path

```bash
npm run dev:desktop
```

Starts the integrated stack above and launches the Electron shell.

Desktop is a supported runtime surface, but root validation is lighter here than for backend and web contracts. See the validation section below.

### 3) Standalone calendar path

```bash
npm run dev:calendar
npm run build:calendar
```

Calendar runs against the **ZoesCal backend**.

### 4) Standalone journal path

```bash
npm run dev:journal
npm run build:journal
```

Journal runs against the **ZoesTM backend** journal routes.

## Build commands

```bash
npm run build
npm run build:web
npm run build:calendar
npm run build:journal
npm run build:desktop
npm run build:all
```

- `npm run build` = the canonical web build path for TM + calendar + journal
- `npm run build:all` = web builds plus desktop packaging

## Test commands

```bash
npm test
npm run test:qa
npm run test:backend
npm run test:smoke
npm run lint
```

### What each command really does

- `npm test` / `npm run test:qa`
  - runs the quality pass
  - runs backend/unit/contract checks from an isolated DB
  - runs repo-root split regression tests
  - runs smoke coverage for ZoesTM, ZoesCal, and standalone frontend contracts
- `npm run test:backend`
  - runs backend tests plus repo-root regression tests from an isolated DB
  - intended as the quick backend-safe path from repo root
- `npm run test:smoke`
  - runs the fast smoke scripts only
- `npm run lint`
  - runs backend compile checks, frontend typechecks, root helper-script syntax checks, desktop helper sanity checks, and split contract audits

## Runtime boundaries

Important ownership split:

- **ZoesTM backend owns** tasks, habits, alarms, focus, review, commands, journal, and `/calendar/feed`
- **ZoesCal backend owns** `/calendar/view`, `/calendar/range`, `/calendar/timeline`, and `/calendar/events` CRUD
- **ZoesJournal frontend** talks to ZoesTM journal routes under `/journal`

That means `/calendar/view` is not a ZoesTM route anymore.

## Validation scope: honest version

What root checks cover well:
- backend unit and contract regressions
- integrated ZoesTM API smoke coverage
- ZoesCal backend smoke coverage
- standalone calendar frontend contract assumptions
- standalone journal frontend contract assumptions
- repo-root command surface regressions

What is intentionally lighter:
- desktop validation at root is static/sanity-focused, not full Electron runtime automation
- frontend smoke checks validate supported contracts and configuration, not brittle pseudo-E2E browser flows
- docs describe the supported paths, not a promise that every path gets identical depth of automated coverage

## Debugging regressions

Start with `docs/dev-runtime.md`. It has the short version of where to look first for:
- auth and missing scope failures
- CORS / preflight failures
- split frontend config mistakes
- bootstrap misses
- root script mismatches

## Docker

```bash
docker-compose up --build
```

## Platform launchers

```bash
./scripts/launcher/linux.sh
./scripts/launcher/macos.sh
./scripts/launcher/windows.ps1
```

## License

MIT.
