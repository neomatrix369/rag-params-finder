# Handoff — 2026-07-29

## Where We Are

**22** ✅ COMPLETE on branch [`slice/22-sie-scooter`](https://github.com/neomatrix369/rag-params-finder) — `9805de8` (feat) + `383541b` (hermetic tests + docs sync). Spec: [`slices/04-sie/SLICE-22-SIE-SCOOTER.md`](slices/04-sie/SLICE-22-SIE-SCOOTER.md). Evidence: **VERIFIED** at unit/API-mock boundary (`/verify-slice` COMPLETE); live SIE smoke optional After-Check only.

**38** ✅ COMPLETE ([PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118)). ADR-004 Accepted; no default flip (#130). Protocol on main — formal **32 / 32C / 32B / 33** tracker debt remains **parallel**.

**44** ✅ · **45** ✅ · **40** ✅ — coverage floors #142; theme moves; theme folders `01`–`07` (#162). Slice 44 Residual §4 Nightly artifact **VERIFIED** pending run URL (#163).

## What's Done

- Remediations #114–#119, image pins #120–#121, Postgres ops parity #122, dual health-check #123, sync-docs #124
- ADR-004 Accepted / ADR-003 Superseded (#127); Slice 38 comparison VERIFIED; default-flip Won't (#130)
- Slice 44 / 45 / 40 COMPLETE (floors, theme packages, theme folders)
- **2026-07-29:** Slice 22 plan refresh — theme-folder file paths, SPLADE narrow (registry already present), persist-via-StorageBackend for best-config, Protocol-on-main Before-Checks (#166–#169)
- **2026-07-29:** Slice 22 executed — `bge-reranker` via SIE score; Tier-1 sweep history as `experiment_type=tier1_sweep`; `GET /api/v1/best-config?task=`; SPLADE sparse-only Tier-1 assert; docs sync; hermetic sweep-test patch; `/verify-slice` COMPLETE
- **2026-07-29:** Doc technology badges — Meterian live scores + toolchain/stack shields across README and guides (`a56bf87`)

## What's Next

1. Confirm create-pr draft (`yes`) and merge `slice/22-sie-scooter`; optional live SIE smoke of sweep → best-config
2. Confirm Slice **44 Residual §4** Nightly `mutation-node-*` artifact (**VERIFIED** run URL)
3. Formal gate-closure debt **32 / 32B / 32C / 33** if prioritized
4. Slice **28** (external — @cschanhniem / #49) · forward Could/Should per [`PROGRESS.md`](slices/PROGRESS.md)

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
| 166 | Resume Slice 22 — Protocol on main; 32B parallel debt |
| 167 | SPLADE registry/index = Slice 21 foundation; 22 wires/asserts only |
| 168 | Persist Tier-1 sweep via StorageBackend for best-config history |
| 169 | Slice 22 quality-lens 10/10 (plan refresh confirmed) |
| 170 | Slice 22 skills: /tdd /verify-slice /nw-execute; models unchanged |
