# ZoesTM + ZoesCal

> A free, local-first productivity tool built by someone with AuDHD who got tired of paying $9/month for habit tracking.

**ZoesTM** is the execution side: tasks, habits, alarms, focus, review, commands, and desktop workflows.

**ZoesCal** is the separate calendar side: day, week, and month views, skins, external calendar sync, and imported mirrors from ZoesTM.

It's free. It will stay free.

Named after a cat who remains unimpressed.

---

## Why this exists

TickTick limits you to 5 habits on the free tier. SuperProductivity hides core features behind a paywall. Both apps are well built. Both pricing models assume that the people who most need productivity scaffolding can most afford to pay for it.

That assumption is wrong.

I have AuDHD. I came out of 3 years of illness and needed tools that actually worked for my brain — habit tracking, spaced repetition, audio interrupts to break hyperfocus loops. I built ZoesTM because I needed it, and I'm giving it away because someone else probably does too.

---

## v1.0.2 Split Release

- `main` now tracks the split architecture release (`v1.0.2`)
- `release/v1.0.0` preserves the older all-in-one skeleton release
- ZoesTM and ZoesCal now live in the same repo as separate products with a shared contract
- `v1.0.2` adds post-split stabilization fixes for startup migrations, ZoesTM -> ZoesCal sync, CORS, and safer calendar date filtering

## Repo layout

- `apps/` - ZoesTM app surfaces
  - `apps/backend` - ZoesTM FastAPI backend
  - `apps/frontend` - ZoesTM React frontend
  - `apps/desktop` - desktop shell assets
- `zoescal/` - ZoesCal app
  - `zoescal/backend` - ZoesCal FastAPI backend
  - `zoescal/frontend` - ZoesCal React/Vite frontend
  - `zoescal/shared` - ADRs and contracts shared across the split

## Features

- **Task management** — quick add, tagging, filtering, Eisenhower matrix prioritization
- **Habit tracking** — unlimited (yes, unlimited) habits with streaks
- **Pomodoro timer** — focus sessions with persistence
- **Spaced repetition** — Anki-compatible review system (APKG import/export experimental)
- **Separate calendar app** — ZoesCal owns day/week/month views and skins
- **Alarms + TTS** — audio reminders via text-to-speech
- **Media player queue** — yt-dlp integration for background audio
- **Emergency dopamine button** — Goggins. You'll know when you need it.
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
| Desktop | Electron |
| Migrations | Plain SQL |
| Testing | Python unittest + Playwright e2e |

---

## Quick start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Setup

```bash
git clone https://github.com/KazAndTheCompiler/zoesTM
cd zoesTM
cp .env.example .env
./scripts/bootstrap_dev.sh
npm run dev
```

`bootstrap_dev.sh` handles the ZoesTM side. ZoesCal lives in `zoescal/` and can be started separately.

### Start the split apps manually

```bash
# ZoesTM backend
.venv/bin/python -m uvicorn apps.backend.app.main:app --reload --port 8000

# ZoesTM frontend
npm --prefix apps/frontend run dev

# ZoesCal backend
python3 -m uvicorn zoescal.backend.app.main:app --reload --port 8001

# ZoesCal frontend
npm --prefix zoescal/frontend run dev -- --port 5174
```

### Desktop app (Electron)

```bash
npm --prefix apps/desktop run start
```

### Docker

```bash
docker-compose up
```

---

## Platform launchers

```bash
# Linux
./scripts/launcher/linux.sh

# macOS  
./scripts/launcher/macos.sh

# Windows
./scripts/launcher/windows.ps1
```

---

## Development

### Run tests

```bash
# ZoesTM backend
.venv/bin/python -m unittest discover -s apps/backend/tests -p "test_*.py" -q

# ZoesTM frontend build check
npm --prefix apps/frontend run build

# ZoesCal frontend build check
npm --prefix zoescal/frontend run build

# Full quality pass
./scripts/quality_pass.sh
./scripts/qa_runner.sh
```

### Run migrations manually

```bash
.venv/bin/python apps/backend/scripts/migrate.py
```

### Seed demo data

```bash
.venv/bin/python apps/backend/scripts/seed.py
```

---

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `ZOESTM_DEV_AUTH` | `0` | Set to `1` for local dev (bypasses auth) |
| `ENABLE_WEBHOOK_HTTP_DELIVERY` | `0` | Set to `1` to enable real HTTP webhook delivery |

---

## Known intentional limits

- **APKG import/export** is experimental — uses a simplified package layout, not full Anki fidelity
- **Webhook delivery** defaults to local stub mode unless `ENABLE_WEBHOOK_HTTP_DELIVERY=1`
- **Desktop packaging/signing** is out of scope for now

---

## Roadmap

- [ ] Full calendar with skins (Still fighting polish bugs)
- [ ] Emergency dopamine button with rotating labels
- [ ] Full Anki spaced repetition fidelity
- [ ] Mobile-friendly UI

---

## Support

ZoesTM is and will always be free.

If it helps you and you want to say thanks:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-orange?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/kazandthecompiler)

Donations go toward keeping the project alive and possibly upgrading the salvaged 2011 laptop it was partly developed on.

---

## License

MIT — do whatever you want with it.

---

*Built by [KazAndTheCompiler](https://github.com/KazAndTheCompiler) — 2 months into learning, built something anyway.*
