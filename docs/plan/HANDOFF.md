# Handoff — 2026-07-26

## Where We Are

**37** ✅ COMPLETE on `slice/37-postgres-local-cloud-parity`. Evidence: [`gate-evidence/slice-37.json`](gate-evidence/slice-37.json). Next Must = **38** (cutover + ADR-004). PR: [#117](https://github.com/neomatrix369/rag-params-finder/pull/117).

## What's Done (recent)

- `0be2764` — mode resolver / four-flag grid / `ensure_env` by mode
- `3fc9c98` — operator docs (Engine × Location, four-flag vocabulary)
- `c966479` — config↔server 422, supabase→postgres normalize, persist `storage_mode`, compose profile aliases
- `f30c31d` — COMPLETE gate evidence after local `postgres-local` smoke
- Live local smoke: `1903dc76-…` → `complete` / `storage_mode=postgres-local`
- Live hosted Supabase smoke: `49c23d41-…` → `complete` / `storage_mode=postgres-cloud` (842 chunks + 77 dense queries)
- `SUPABASE_URI` optional alias for `DATABASE_URL` (**IMPLEMENTED** + unit-tested; **VERIFIED** via hosted path using `DATABASE_URL`)

## What's Next

1. Commit + push staged Slice 37 follow-up (`SUPABASE_URI` + hosted smoke evidence + docs sync) onto PR #117
2. Merge #117 when CI/review green
3. Start **38** → then **22**

## Blockers / Open Questions

- None for 37. Optional cleanup: delete smoke experiments `1903dc76-…` (local) and `49c23d41-…` (hosted Supabase) when convenient.

## Context for Next Session

- Spec: `docs/plan/slices/SLICE-38-CUTOVER-ADR-004.md`
- 37 artifacts: `server/core/config_backend_guard.py`, `scripts/lib/storage_mode.sh`, `tests/test_config_backend_guard.py`, `tests/test_supabase_uri_alias.py`
- Axes: `STORAGE_BACKEND` × `storage_mode`; Atlas/Supabase = cloud shorthand only
- Canonical URI: `DATABASE_URL`; optional product alias: `SUPABASE_URI` (unused when `DATABASE_URL` set)
