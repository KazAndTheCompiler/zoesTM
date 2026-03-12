# AGENTS.md

## Scope
- This repo contains two products:
  - `apps/` = ZoesTM
  - `zoescal/` = ZoesCal

## Working rules
- Treat `main` as publishable code.
- Never commit `node_modules`, `.venv`, `dist`, DBs, or runtime junk.
- Use `/projects/` for clean private development copies.
- Use `/sandbox/` for dirty runtime/test copies.
- Keep `/liveprojectsonhub/` clean and release-ready.

## Product boundaries
- ZoesTM owns tasks, habits, alarms, focus, review, commands, player, and desktop workflows.
- ZoesCal owns calendar rendering, skins, calendar sync, and imported mirrors.
- Do not move calendar UI back into ZoesTM.

## Backend rules
- Run migrations automatically on startup where expected.
- Do not let external sync failures crash the server.
- Favor explicit JSON/HTTP contracts between apps.

## Frontend rules
- Keep tap targets mobile-safe.
- Keep accessibility labels in place.
- Preserve skin-token architecture in `zoescal/`.
- Do not add CSS frameworks.

## Before ending a session
- Run the relevant build(s)
- Run backend checks/tests when backend files changed
- Summarize what changed in `SUMMARY.md` if the session materially changes architecture or release state
