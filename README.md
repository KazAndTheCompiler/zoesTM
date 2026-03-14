# ZoesTM + ZoesCal

> A free, local-first productivity tool built by someone with AuDHD who got tired of paying $9/month for habit tracking.

**ZoesTM** is the execution side: tasks, habits, alarms, focus, review, commands, and desktop workflows.

**ZoesCal** is the separate calendar side: day, week, and month views, skins, external calendar sync, and imported mirrors from ZoesTM.

**ZoesJournal** is the separate mobile-first journal companion: day entry editing, history, export, and markdown-first journaling over the existing ZoesTM journal API.

It's free. It will stay free.

Named after a cat who remains unimpressed.

---

## Why this exists

TickTick limits you to 5 habits on the free tier. SuperProductivity hides core features behind a paywall. Both apps are well built. Both pricing models assume that the people who most need productivity scaffolding can most afford to pay for it.

That assumption is wrong.

I have AuDHD. I came out of 3 years of illness and needed tools that actually worked for my brain — habit tracking, spaced repetition, audio interrupts to break hyperfocus loops. I built ZoesTM because I needed it, and I'm giving it away because someone else probably does too.

---

## v1.0.2 Split Release

- `main` tracks the split architecture release line
- `release/v1.0.0` preserves the older all-in-one skeleton release
- ZoesTM and ZoesCal live in one repo as separate products with an explicit shared contract
- ZoesJournal is the standalone journal frontend over ZoesTM journal routes

## Repo layout

- `apps/` - ZoesTM app surfaces
  - `apps/backend` - ZoesTM FastAPI backend
  - `apps/frontend` - ZoesTM React frontend
  - `apps/desktop` - Electron desktop shell
- `zoescal/` - ZoesCal app
  - `zoescal/backend` - ZoesCal FastAPI backend
  - `zoescal/frontend` - ZoesCal React/Vite frontend
  - `zoescal/shared` - shared ADRs and contracts for the split
- `zoesjournal/` - ZoesJournal companion app
  - `zoesjournal/frontend` - ZoesJournal React/Vite frontend

## Features

- **Task management** — quick add, tagging, filtering, Eisenhower matrix prioritization
- **Habit tracking** — unlimited habits with streaks
- **Pomodoro timer** — focus sessions with persistence
- **Spaced repetition** — Anki-compatible review system (APKG import/export experimental)
- **Separate calendar app** — ZoesCal owns day/week/month views and skins
- **Separate journal app** — ZoesJournal owns phone-first journal UX
- **Alarms + TTS** — audio reminders via text-to-speech
- **Media player queue** — yt-dlp integration for background audio
- **Emergency dopamine button** — Goggins. You will know when you need it.
- **Webhook support** — opt-in HTTP delivery via `ENABLE_WEBHOOK_HTTP_DELIVERY=1`
- **Local-first** — SQLite, no cloud, no accounts, your data stays yours

---

## Stack

| Layer | Tech |
|---|---|
| ZoesTM backend | FastAPI + SQLite |
| ZoesTM frontend | React + Vite + TypeScript |
| ZoesCal backend | FastAPI + SQLite |
| ZoesCal frontend | React + Vite + TypeScript |
| ZoesJournal frontend | React + Vite + TypeScript |
| Desktop shell | Electron |
| Migrations | Plain SQL |
| Testing | Python unittest + smoke scripts + frontend build checks |

---

## Canonical commands

### Setup

```bash
npm run setup
```

Creates `.venv`, installs backend deps, installs root/frontend/desktop deps, runs migrations, and seeds demo data.

### Dev

```bash
# Integrated default: ZoesTM backend + ZoesCal backend + TM frontend + calendar frontend + journal frontend
npm run dev

# Same integrated stack plus Electron shell
npm run dev:desktop

# Standalone calendar
npm run dev:calendar

# Standalone journal
npm run dev:journal
```

### Build

```bash
# Canonical supported web builds: TM + calendar + journal
npm run build

# Individual targets
npm run build:web
npm run build:calendar
npm run build:journal
npm run build:desktop

# Everything, including desktop packaging
npm run build:all
```

### Test

```bash
# Canonical repo validation
npm test

# Direct aliases
npm run test:qa
npm run test:backend
npm run test:smoke
```

See `docs/dev-runtime.md` for ports, auth expectations, backend ownership, and Docker notes.

## Runtime model

- **Integrated web stack**: all three first-party frontends together, backed by ZoesTM + ZoesCal APIs
- **Desktop shell**: Electron shell over the integrated stack
- **Standalone calendar**: ZoesCal frontend + ZoesCal backend
- **Standalone journal**: ZoesJournal frontend + ZoesTM backend

Important backend boundary:
- ZoesTM exposes `/calendar/feed` as a mirror feed for ZoesCal
- ZoesCal owns `/calendar/view`, `/calendar/range`, `/calendar/timeline`, and event CRUD

## Docker

```bash
docker-compose up --build
```

## Platform launchers

```bash
# Linux
./scripts/launcher/linux.sh

# macOS
./scripts/launcher/macos.sh

# Windows
./scripts/launcher/windows.ps1
```

## Development notes

### Backend migrations

```bash
.venv/bin/python apps/backend/scripts/migrate.py
```

### Seed demo data

```bash
.venv/bin/python apps/backend/scripts/seed.py
```

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `ZOESTM_DEV_AUTH` | `0` | Explicit dev bypass for ZoesTM auth |
| `ZOESTM_ENFORCE_AUTH` | `0` | Require explicit scope headers even for local clients |
| `ENABLE_WEBHOOK_HTTP_DELIVERY` | `0` | Enable real HTTP webhook delivery |

## Known intentional limits

- **APKG import/export** is experimental
- **Webhook delivery** defaults to local stub mode unless explicitly enabled
- **Desktop packaging/signing** is still a separate packaging path, not part of default dev validation

## Support

ZoesTM is and will always be free.

If it helps you and you want to say thanks:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/kazandthecompiler)

## License

MIT — do whatever you want with it.

*Built by [KazAndTheCompiler](https://github.com/KazAndTheCompiler).*
