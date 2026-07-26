# Handoff — 2026-07-26

## Where We Are

**38** ✅ COMPLETE on `slice/38-cutover-adr-004` ([PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118)).

**ADR-004 Accepted**; local comparison VERIFIED; CI dual-backend ✅; mutation waived (#128). **No default flip** (#130 Won't) — code default stays `mongodb` permanently; backends independently selectable (#129).

**44** 📋 PLANNED — stub migrated to latest plan-generator format + live baseline (DECISIONS #131–#133). Quality-lens provisional 9/10 — awaiting user confirm on adversarial questions.

## What's Done

- Remediations #114–#119, image pins #120–#121, Postgres ops parity #122, dual health-check #123, sync-docs #124
- ADR-004 Accepted / ADR-003 Superseded (#127)
- `slice-38-quality-comparison.md` — both 120-run twins; latency ≤2× PASS; overlap informational (#129)
- `slice-38.json` — `gate_status: PASSED`; default-flip gate removed (#130)
- Slice 44 Path B revise: latest stub + measured coverage baseline (`npm run test:coverage` → lines **50.18%**, **16** tests; gates still bare Vitest)

## What's Next

1. Confirm Slice 44 quality-lens (adversarial: Must-only floor vs full Should tests; defer vs execute)
2. Path A Resume Slice **44** when ready — or continue formal gate-closure debt on tracker rows 32 / 32B / 32C / 33
3. Merge [PR #118](https://github.com/neomatrix369/rag-params-finder/pull/118) when ready
4. Slice **43** residuals (#125/#126): hosted production-claim matrix, Pro-tier ADR mandate, etc.

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
