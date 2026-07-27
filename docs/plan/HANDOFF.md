# Handoff — 2026-07-27

## Where We Are

**38** ✅ COMPLETE on `slice/38-cutover-adr-004` ([PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118)).

**ADR-004 Accepted**; local comparison VERIFIED; CI dual-backend ✅; mutation waived (#128). **No default flip** (#130 Won't) — code default stays `mongodb` permanently; backends independently selectable (#129).

**44** 📋 PLANNED — coverage Must open; taxonomy §3 published; **nw-review remediations APPLIED** (#137) — DoR APPROVED for execution (scripts locked: local `test:coverage`, CI `test:ci`).

**45** 📋 PLANNED — module theme separation; architect HIGH remediations APPLIED (#137) — **APPROVED** for phased execution after taxonomy pre-check.

## What's Done

- Remediations #114–#119, image pins #120–#121, Postgres ops parity #122, dual health-check #123, sync-docs #124
- ADR-004 Accepted / ADR-003 Superseded (#127)
- `slice-38-quality-comparison.md` — both 120-run twins; latency ≤2× PASS; overlap informational (#129)
- `slice-38.json` — `gate_status: PASSED`; default-flip gate removed (#130)
- Slice 44 Path B revise: latest stub + measured coverage baseline (`npm run test:coverage` → lines **50.18%**, **16** tests; gates still bare Vitest)
- Slice 44 §3 taxonomy: [`module-theme-map.md`](../contributor-guide/module-theme-map.md), canvas `project-structure-taxonomy.canvas.tsx`, [`SLICE-45-MODULE-THEME-SEPARATION.md`](slices/SLICE-45-MODULE-THEME-SEPARATION.md)

## What's Next

1. Path A Resume Slice **44** coverage Must — `test:coverage` in quality-gates/pre-push; `test:ci` in CI; re-measure floor on Before-Check
2. Slice 44 Should FE module tests (or defer with Decision Log)
3. Optional: Slice **45** phase 1 (`server/core/`) — taxonomy pre-check already satisfiable
4. Merge [PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118) when ready
5. Formal gate-closure debt on tracker rows 32 / 32B / 32C / 33 if prioritized over 44

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
| 126 | All non-100%-Yes 38 gates parked on 43 (Pro-tier mandate, sync-docs, …) — post-flip smoke dropped via #130 |
| 127 | ADR-004 Accepted — dual-backend Postgres/Supabase + Mongo; ADR-003 Superseded |
| 128 | Backend mutation waived to nightly CI (same pattern as #95/#101) |
| 129 | Mongo ⟂ Postgres — neither is a fail-safe for the other |
| 130 | **Won't** — no `STORAGE_BACKEND` default flip; code default stays `mongodb` permanently |
| 131 | Health Gap 8 SKIPPED for COMPLETE historical stubs |
| 132 | Path B revise Slice 44 → latest stub + live baseline |
| 133 | Slice 44 quality-lens provisional 9/10 (pending user confirm) |
| 135 | Taxonomy audit in Slice 44 Should; moves deferred to Slice 45 Could |
| 136 | sync-docs: theme map on CHANGELOG/CLAUDE/development/AGENTS; coverage floor still PROPOSED |
| 137 | nw-review remediations on SLICE-44/45 — DoR/architect APPROVED for execution |
