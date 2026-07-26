# Handoff — 2026-07-26

## Where We Are

**37** ✅ COMPLETE on `slice/37-postgres-local-cloud-parity`. Evidence: [`gate-evidence/slice-37.json`](gate-evidence/slice-37.json). Next Must = **38** (cutover + ADR-004). PR: [#117](https://github.com/neomatrix369/rag-params-finder/pull/117).

## What's Done (recent)

- Four-flag grid + config↔server 422 + supabase normalize + `SUPABASE_URI` + hosted/local Postgres smoke
- Removed CLI flag aliases `--local`/`-l`/`--postgres`/`-p` → generic `Unknown option` (DECISIONS #108/#109; env `RAG_LOCAL_*` still warn)
- Review follow-up: `test_storage_mode_resolve.py` → 22 cases (`_clean_env` isolation, `RAG_*` selectors, empty `DATABASE_URL`, hint non-leak)
- Review follow-up: shellcheck gates root `start-services.sh` (DECISIONS #110); SC2155 cleared
- Unit tier measured **317** backend / **16** frontend (2026-07-26)

## What's Next

1. Commit + push Slice 37 follow-up onto PR #117
2. Merge #117 when CI/review green
3. Start **38** → then **22**

## Blockers / Open Questions

- None for 37. Optional: delete smoke experiments `1903dc76-…` (local) and `49c23d41-…` (hosted).

## Context for Next Session

- Spec: `docs/plan/slices/SLICE-38-CUTOVER-ADR-004.md`
- Canonical start flags only: `--mongodb-local|cloud` / `--postgres-local|cloud`
- Canonical URI: `DATABASE_URL`; optional alias: `SUPABASE_URI`
- Shellcheck scope: `start-services.sh` + `scripts/**/*.sh`
