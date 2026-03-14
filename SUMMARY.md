# Session Summary

## Current release state
- `main` is the split release line
- `release/v1.0.0` preserves the older skeleton release
- tags exist for `v1.0.0`, `v1.0.1`, and `v1.0.2`

## Repo shape
- `apps/` contains ZoesTM
- `zoescal/` contains the separate calendar app

## ZoesTM updates in this pass
- added `apps/backend/static/goggins.mp3`
- added `apps/backend/app/routers/goggins.py`
- mounted `/static` from `apps/backend/static`
- registered `/goggins` router in backend `main.py`
- added frontend `FloatingGoggins.tsx`
- wired quote + audio trigger behavior
- added rotating labels and violent shake animation
- added repo-root `AGENTS.md` for the split workflow
- confirmed ZoesCal live frontend feature set is present and builds clean

## ZoesCal already present and verified
- pull-to-refresh
- swipe day/week/month navigation
- day/week/month transitions
- AddBar character counter
- mini month calendar
- offline banner
- Week number header
- print styles
- accessibility pass
- long-press create in day view

## Recent backend stabilization
- ZoesTM startup migrations run automatically
- ZoesCal imports blocks from ZoesTM feed
- ZoesCal validates ISO datetimes
- ZoesCal CORS allows `5174`
- ZoesTM sync timeout lowered to `5s`
- ZoesCal event date filtering uses SQLite `datetime()` instead of raw string compare

## Consolidation follow-up completed
- QA runner now includes split regression coverage for auth runtime, standalone journal surface, and ZoesCal backend smoke
- legacy ZoesTM calendar tests were rewritten to use the supported `/calendar/feed` bridge instead of pre-split `/calendar/view` and `/calendar/range`
- root command surface is now explicit: `npm run setup`, `npm run dev`, `npm run build`, `npm test`
- docs were aligned around four first-class surfaces: integrated web, desktop shell, standalone calendar, standalone journal
- repo-level root tests now validate the supported command surface and runtime guide instead of unrelated OpenClaw lockdown config

## Next-session suggestions
- release notes / screenshots cleanup
- optionally add UI targeting in ZoesTM for goggins quote history
- consider moving testing/runtime junk fully into `/sandbox/` while keeping `/liveprojectsonhub/` pristine
