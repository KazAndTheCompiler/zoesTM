# ZoesJournal

ZoesJournal is the mobile-first journal companion for the ZoesTM / ZoesCal split.

## What it is

- standalone journal frontend surface
- talks to ZoesTM backend journal routes over HTTP
- preserves existing journal backend contracts
- does not depend on Mission Control UI state for journal CRUD

## What it depends on

- ZoesTM backend on port `8000`
- journal routes under `/journal`
- existing auth scope pattern (`read:journal`, `write:journal`) when auth is enforced

## What remains intentionally coupled

- backend data ownership stays in ZoesTM
- export still uses existing backend aggregation/fallback behavior
- auth remains compatible with existing ZoesTM scope headers

## What is intentionally independent

- frontend shell and navigation
- entry editor/history/export UX
- mobile-first layout and markdown preview

## Run

```bash
# ZoesTM backend
.venv/bin/python -m uvicorn apps.backend.app.main:app --reload --port 8000

# ZoesJournal frontend
npm --prefix zoesjournal/frontend run dev -- --port 5175
```

Default frontend URL:
- `http://localhost:5175/zoesjournal/`

## Notes

- Core journal use works without opening Mission Control UI.
- Backdating remains supported.
- One-entry-per-day behavior remains backend-enforced.
- Export degrades gracefully if dependent services are unavailable.
