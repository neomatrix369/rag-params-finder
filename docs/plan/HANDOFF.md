# Handoff — 2026-07-26

## Where We Are

**38** 🔨 IN PROGRESS on `slice/38-cutover-adr-004`.

Review remediations (BLOCKER-1/4) landed in code; **default still `mongodb`** until comparison gates PASS.

## What's Done (this session)

- Path A Resume after nw-platform-architect-reviewer remediations
- `export_storage_backend_for_stack` — Mongo flags override leftover `STORAGE_BACKEND=postgres`
- `compose_export_local_atlas_env` + `apply_stack_profiles` export `STORAGE_BACKEND=mongodb`
- Reject `<project-ref>` Postgres placeholders in `ensure_stack_mode_env` + `Settings.ensure_storage_ready`
- Commented out placeholder `SUPABASE_URI` in `.env.example`
- Tests: 29/29 green (`test_storage_mode_resolve` + `test_supabase_uri_alias`)

## What's Next

1. Run Slice 43–shaped dual-backend comparison (384-dim local, mirrored configs)
2. Write `gate-evidence/slice-38-quality-comparison.md` (QUERYING elapsed_ms median+max ≤2×)
3. ADR-004 + supersede ADR-003
4. Flip defaults (settings / storage_mode.sh / compose) **only if** gates PASS
5. `/sync-docs` + gate-evidence `slice-38.json`

## Key decisions locked

| # | Choice |
|---|---|
| 114 | Latency = QUERYING `elapsed_ms` median+max ≤2× |
| 115 | Baseline = Slice 43 mirrored 384-dim local |
| 116 | Flip surfaces include shell + compose; Mongo exports mongodb |
| 117 | Placeholder `SUPABASE_URI` commented + rejected |
| 119 | Remediations land before flip; flip remains fail-closed |
