# ZoesJournal

ZoesJournal is the mobile-first journal companion for the ZoesTM / ZoesCal split.

## What it is

- standalone journal frontend surface
- talks to ZoesTM backend journal routes over HTTP
- preserves existing journal backend contracts
- does not depend on Mission Control UI state for journal CRUD

## Runtime dependency

- ZoesTM backend on port `8000`
- journal routes under `/journal`
- existing auth scope pattern (`read:journal`, `write:journal`) when auth is enforced

## Supported repo-root commands

```bash
npm run dev:journal
npm run build:journal
npm test
```

## Run manually

```bash
# ZoesTM backend
.venv/bin/python -m uvicorn apps.backend.app.main:app --reload --port 8000

# ZoesJournal frontend
npm --prefix zoesjournal/frontend run dev -- --port 5175
```

Default frontend URL:
- `http://localhost:5175/zoesjournal/`

## Notes

- Core journal use works without opening the main ZoesTM UI.
- Backdating remains supported.
- One-entry-per-day behavior remains backend-enforced.
- Export degrades gracefully if dependent services are unavailable.
- Local first-party journal use works without scope headers unless `ZOESTM_ENFORCE_AUTH=1`.
