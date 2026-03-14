# ZoesTM Apps

This folder contains the ZoesTM side of the split release.

## Scope

- `apps/backend` = ZoesTM backend
- `apps/frontend` = ZoesTM main frontend
- `apps/desktop` = Electron desktop shell

For the separate calendar app and split ADRs, see `../zoescal/`.
For the separate journal frontend, see `../zoesjournal/`.

## Supported repo-root commands

```bash
npm run setup
npm run dev
npm run dev:desktop
npm run build:web
npm run test:backend
npm test
npm run lint
```

## Important split boundary

ZoesTM does **not** own calendar presentation routes anymore.

Supported ZoesTM calendar contract:
- `GET /calendar/feed`

Not owned by ZoesTM:
- `/calendar/view`
- `/calendar/range`
- `/calendar/timeline`
- `/calendar/events`

Those belong to the ZoesCal backend.

## Validation notes

What root validation covers strongly for the ZoesTM side:
- backend unit and contract regressions
- root smoke coverage for key ZoesTM APIs
- command-surface regressions from the repo root

What remains lighter:
- desktop runtime validation is mostly static sanity checking at root, not full Electron automation

## Notes

- Journal data still lives in the ZoesTM backend.
- ZoesJournal is the standalone frontend for that journal API.
- The desktop shell is a supported surface, but desktop packaging remains a separate build path (`npm run build:desktop`).
