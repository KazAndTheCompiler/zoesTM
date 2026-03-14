# ZoesJournal

ZoesJournal is the mobile-first journal companion for the ZoesTM / ZoesCal split.

## What it is

- standalone journal frontend surface
- talks to ZoesTM backend journal routes over HTTP
- preserves existing journal backend contracts
- does not depend on the main ZoesTM frontend state for journal CRUD

## Runtime dependency

- ZoesTM backend on port `8000`
- journal routes under `/journal`
- existing auth scope pattern (`read:journal`, `write:journal`) when auth is enforced

## Supported repo-root commands

```bash
npm run dev:journal
npm run build:journal
npm run lint
npm run test:smoke
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

## What root validation checks

At root, ZoesJournal is validated through:
- TypeScript typecheck
- split contract tests for package/config/runtime assumptions
- smoke checks that verify standalone journal wiring remains consistent with the supported architecture

This is intentionally lighter than full browser automation, but it is no longer treated as an afterthought.

## Notes

- Core journal use works without opening the main ZoesTM UI.
- Backdating remains supported.
- One-entry-per-day behavior remains backend-enforced.
- Export should degrade gracefully if related services are unavailable.
- Local first-party journal use works without scope headers unless `ZOESTM_ENFORCE_AUTH=1`.
