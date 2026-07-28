# Handoff — 2026-07-28

## Where We Are

**38** ✅ COMPLETE on `slice/38-cutover-adr-004` ([PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118)).

**ADR-004 Accepted**; local comparison VERIFIED; CI dual-backend ✅; mutation waived (#128). **No default flip** (#130 Won't) — code default stays `mongodb` permanently; backends independently selectable (#129).

**44** ✅ COMPLETE on `slice/44-frontend-coverage-gate` — **#142**: FE **95/90/95/95**; BE **95/90/n/a/95** (`fail_under=95` + `scripts/ci/check_backend_coverage_floors.py`); measured FE ≈98.4 / 93.11 / 100 / 99.69; BE stmts ≈98.6 / br ≈95.2 / TOTAL ≈97.7; **261** FE / **338** BE unit tests (**VERIFIED**). **Residual §4 IMPLEMENTED** (#163) — narrow Nightly mutate to utils/services/hooks; local Stryker **~8m**; Nightly artifact **VERIFIED** pending run URL.

**45** ✅ COMPLETE on `slice/45-module-theme-separation` ([PR #130](https://github.com/neomatrix369/rag-params-finder/pull/130)) — hotspots 1–5 **IMPLEMENTED**; FE/BE craft; scripts themes; Could leftovers #161 (docstrings, coverage drift guard, GWT-on-touch); mutation #160; evidence [`slice-45.json`](gate-evidence/slice-45.json).

## What's Done

- Remediations #114–#119, image pins #120–#121, Postgres ops parity #122, dual health-check #123, sync-docs #124
- ADR-004 Accepted / ADR-003 Superseded (#127)
- `slice-38-quality-comparison.md` — both 120-run twins; latency ≤2× PASS; overlap informational (#129)
- `slice-38.json` — `gate_status: PASSED`; default-flip gate removed (#130)
- Slice 44 + #142: FE **95/90/95/95**; BE **95/90/n/a/95** via fail_under + JSON floor checker; gate-evidence PASSED
- Slice 44 §3 taxonomy: [`module-theme-map.md`](../contributor-guide/module-theme-map.md)
- Slice 45: theme packages + craft + scripts folders; [`SLICE-45-MODULE-THEME-SEPARATION.md`](slices/SLICE-45-MODULE-THEME-SEPARATION.md); Gate Status ✅

## What's Next

1. Confirm Slice **44 Residual §4** Nightly finish + `mutation-node-*` artifact via `workflow_dispatch`/cron (**VERIFIED** run URL) — config already **IMPLEMENTED**
2. Slice **40** — theme folders `01`–`07` + plan/slices SSOT (#162) when prioritized
3. Formal gate-closure debt on tracker rows 32 / 32B / 32C / 33 if prioritized
4. Forward-roadmap Could/Should items (export, SSE, recovery, etc.) per [`PROGRESS.md`](slices/PROGRESS.md)

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
| 139 | Phase B FE floor ≥95% stmts/funcs/lines + ≥90% branches (`all: true`) — product floors via #140/#141/#142 |
| 140 | Uniform overall ≥90% (BE fail_under=90; FE briefly 90/90/90/90) — superseded by #141/#142 |
| 141 | Fair floors: FE **95/90/95/95**; BE policy briefly 92/85 — superseded by #142 |
| 142 | FE **95/90/95/95**; BE **95/90/n/a/95** via `fail_under=95` + `check_backend_coverage_floors.py` |
| 159 | `scripts/{ci,docker,release,security}/` + flat shims for one minor |
| 160 | Slice 45 mutation waived to nightly CI |
| 161 | FE↔pyproject coverage drift guard + FE docstring / BE GWT-on-touch Could leftovers |
| 162 | Slice specs → numbered theme folders `01`–`07` (delivery wave); PROGRESS + gate-evidence stay flat (Slice 40) |
| 163 | Slice 44 Residual §4 — Nightly Stryker after suite growth (narrow mutate to utils/services/hooks) |
