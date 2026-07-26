# Handoff — 2026-07-26

## Where We Are

**38** 🔨 IN PROGRESS on `slice/38-cutover-adr-004` ([PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118) — checkpoint only).

**ADR-004 Accepted**; CI dual-backend ✅; mutation waived (#128). **Default still `mongodb`**. Local comparison **VERIFIED** (both 120-run twins `complete`; latency PASS; overlap informational per #129).

## What's Done (this branch)

### Remediations (DECISIONS #114–#119) — commit `96316bb`
- Path A Resume after nw-platform-architect-reviewer remediations
- `export_storage_backend_for_stack` — Mongo flags override leftover `STORAGE_BACKEND=postgres`
- `compose_export_local_atlas_env` + `apply_stack_profiles` export `STORAGE_BACKEND=mongodb`
- Reject `<project-ref>` Postgres placeholders in `ensure_stack_mode_env` + `Settings.ensure_storage_ready`
- Commented out placeholder `SUPABASE_URI` in `.env.example`
- Tests: `test_storage_mode_resolve` + `test_supabase_uri_alias` green

### Image pins + FCV recovery (DECISIONS #120–#121) — commit `0f6ba2d` + follow-up
- Atlas Local pinned to `mongodb/mongodb-atlas-local:8.3.3` (not `:latest`, not `8.0.9` — FCV 8.3 volumes exit 62 on 8.0.x)
- Local pgvector pinned to `pgvector/pgvector:0.8.5-pg16` (compose + CI)
- `compose.sh` prints FCV mismatch hint on unhealthy / timeout; mongodb-setup callout
- Verified: recreate → healthy ~7s; after invalid RS / `NotPrimaryOrSecondary` → `mongodb reset` + start + restart server restores writable primary and `POST /experiments` 200
- Postgres container ops parity (#122): shared `wait_for_postgres_local_healthy`, `postgres reset` hints (not raw docker), NONINTERACTIVE `:5433` conflict messaging
- Dual-container `health-check.sh` (#123) + sync-docs operator parity (#124): QUICKSTART Path D, postgres-setup native-dev, troubleshooting, local-environment, architecture, CLAUDE indexes, mode-aware SIE footer

### Gate evidence (partial)
- ADR-004 Accepted / ADR-003 Superseded (#127)
- `gate-evidence/slice-38.json` — CI dual-backend VERIFIED (run `30218369352`; both jobs `success`; skipped ≠ green)
- Mutation waived (#128)
- `slice-38-quality-comparison.md` — **VERIFIED** both sides (`1a16eaff…` mongodb-local; `9ab49abc…` postgres-local); latency ≤2× PASS; rank overlap recorded as informational (#129)

## What's Next

1. ~~Finish local dual-backend comparison~~ ✅ VERIFIED
2. Flip defaults **only after an explicit product decision** (comparison informs; backends are independent — #129)
3. Tick PROGRESS/TRAIL COMPLETE row + finalize `slice-38.json` `gate_status` (optional flip can stay deferred)

Hosted production-claim matrix, post-flip smoke, Pro-tier ADR mandate, PRD bookkeeping, sync-docs → Slice **43** residuals (DECISIONS #125/#126) — not Slice 38 COMPLETE blockers.

## Key decisions locked

| # | Choice |
|---|---|
| 114 | Latency = QUERYING `elapsed_ms` median+max ≤2× |
| 115 | Baseline = Slice 43 mirrored 384-dim local |
| 116 | Flip surfaces include shell + compose; Mongo exports mongodb |
| 117 | Placeholder `SUPABASE_URI` commented + rejected |
| 119 | Remediations land before any silent default change; #129 clarifies backends are independent |
| 120 | Pin Atlas Local `8.3.3` + pgvector `0.8.5-pg16` |
| 121 | Healthy ≠ writable after FCV churn → reset volumes + restart server |
| 122 | Postgres container ops parity with Mongo (wait/reset/port UX) |
| 123 | `health-check.sh` probes both local DB containers when present |
| 124 | sync-docs Mongo↔Postgres operator/doc parity |
| 125 | Unrealistic 38 gates parked on Slice 43 residuals (hosted claim / PRD bookkeeping / 100% shell) |
| 126 | All non-100%-Yes 38 gates parked on 43 (post-flip smoke, Pro-tier mandate, sync-docs, …) |
| 127 | ADR-004 Accepted — dual-backend Postgres/Supabase + Mongo; ADR-003 Superseded |
| 128 | Backend mutation waived to nightly CI (same pattern as #95/#101) |
| 129 | Mongo ⟂ Postgres — neither is a fail-safe for the other; comparison = evidence for optional default flip |
