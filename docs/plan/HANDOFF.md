# Handoff — 2026-07-27

## Where We Are

**38** ✅ COMPLETE on `slice/38-cutover-adr-004` ([PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118)).

**ADR-004 Accepted**; local comparison VERIFIED; CI dual-backend ✅; mutation waived (#128). **No default flip** (#130 Won't) — code default stays `mongodb` permanently; backends independently selectable (#129).

**44** ✅ COMPLETE on `slice/44-frontend-coverage-gate` (`dcbdf3a` / `94d3080`) — coverage Must + Should tests VERIFIED; nw-review APPROVED; thresholds lines≥64 (ratcheted from 50.18% baseline — #138).

**45** 📋 PLANNED — module theme separation; architect APPROVED (#137) — ready for phased execution (taxonomy pre-check satisfiable).

## What's Done

- Remediations #114–#119, image pins #120–#121, Postgres ops parity #122, dual health-check #123, sync-docs #124
- ADR-004 Accepted / ADR-003 Superseded (#127)
- `slice-38-quality-comparison.md` — both 120-run twins; latency ≤2× PASS; overlap informational (#129)
- `slice-38.json` — `gate_status: PASSED`; default-flip gate removed (#130)
- Slice 44: `test:coverage` in quality-gates/pre-push; `test:ci` in CI; 53 FE tests; floor 64/58/61/62; gate-evidence PASSED
- Slice 44 §3 taxonomy: [`module-theme-map.md`](../contributor-guide/module-theme-map.md), canvas `project-structure-taxonomy.canvas.tsx`, [`SLICE-45-MODULE-THEME-SEPARATION.md`](slices/SLICE-45-MODULE-THEME-SEPARATION.md)

## What's Next

1. Push `slice/44-frontend-coverage-gate` and open PR
2. Optional: Slice **45** phase 1 (`server/core/`) — taxonomy pre-check already satisfiable
3. Merge [PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118) when ready (if still open)
4. Formal gate-closure debt on tracker rows 32 / 32B / 32C / 33 if prioritized

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
| 135 | Taxonomy audit = Slice 44 Should; moves = Slice 45 |
| 137 | Slice 44/45 nw-review remediations APPLIED |
| 138 | FE coverage floor ratcheted 50.18%→64% lines after Should tests; mutation waived |
