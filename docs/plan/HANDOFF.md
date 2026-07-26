# Handoff — 2026-07-26

## Where We Are

**37** ✅ COMPLETE on `slice/37-postgres-local-cloud-parity`. Evidence: [`gate-evidence/slice-37.json`](gate-evidence/slice-37.json). Next Must = **38** (cutover + ADR-004).

## What's Done (recent)

- `0be2764` — mode resolver / four-flag grid / `ensure_env` by mode
- `3fc9c98` — operator docs (Engine × Location, four-flag vocabulary)
- `c966479` — config↔server 422, supabase→postgres normalize, persist `storage_mode`, compose profile aliases
- Live smoke after Docker VM disk prune: experiment `1903dc76-b3ac-450f-a715-c26ae19fe8c0` → `complete` / `storage_mode=postgres-local`
- Hosted `--postgres-cloud` smoke: **documented skip** (no credentials)

## What's Next

1. Commit gate-evidence + COMPLETE status docs (if not yet committed)
2. Open / merge PR for `slice/37-postgres-local-cloud-parity`
3. Start **38** → then **22**

## Blockers / Open Questions

- None for 37. Optional: delete leftover smoke experiment `1903dc76-…` from local Postgres when convenient.
- Hosted Supabase live smoke remains optional follow-up (not a 37 blocker).

## Context for Next Session

- Spec: `docs/plan/slices/SLICE-38-CUTOVER-ADR-004.md`
- 37 artifacts: `server/core/config_backend_guard.py`, `scripts/lib/storage_mode.sh`, `tests/test_config_backend_guard.py`
- Axes: `STORAGE_BACKEND` × `storage_mode`; Atlas/Supabase = cloud shorthand only
