# SLICE 44 — Frontend Test Coverage + Coverage in Gate Summary

**MoSCoW:** Should
**Target time:** ~2–3 h
**Status:** 📋 PLANNED
**Depends on:** none (frontend/CI hygiene; independent of Supabase migration 36–38)
**Non-blocking / non-urgent:** Pure CI-hygiene parity — does not gate any backend slice.

**Origin:** Spun out of SLICE-43 on 2026-07-26 (enhanced-flow-planner quality lens, SLAP check 3): frontend-coverage hardening is a different abstraction level from Supabase config verification, so it gets its own slice rather than expanding 43.

---

## Slice Workflow Bundle

- Slice name: `slice-44-frontend-coverage-gate`
- Branch: `slice/44-frontend-coverage-gate`
- Files (expected):
  - `frontend/vite.config.ts` (coverage provider + thresholds)
  - `frontend/package.json` (wire `test:coverage` / `test:ci` into the gate path)
  - `scripts/pre-push-gates.sh` (frontend step runs coverage)
  - `.github/workflows/ci.yml` (frontend job emits coverage table)
  - new `frontend/src/**/*.test.ts(x)` files for the untested modules below
  - `CLAUDE.md` / `docs/contributor-guide/development.md` (baseline line + embedded report)
- Exit criteria: frontend gate (pre-push + CI) runs with coverage enabled, prints a coverage table, and fails below a configured floor; new tests raise measured coverage above that floor; baseline logged in PROGRESS Decision Log.
- Commit pattern: `test(slice-44): add frontend coverage floor and embed report in gate`

---

## Goal

Bring the frontend quality gate to parity with the backend: the backend embeds coverage (`pytest --cov-report=term-missing --cov-fail-under=80`) while the frontend runs a bare `npm run test`. Coverage is already configured (`vite.config.ts` v8 + `test:coverage` / `test:ci`) but never invoked by pre-push or CI, so there is no report or floor in the gate summary.

---

## Residual issues

### 1. Untested high-value modules
Only 3 frontend test files today (`storageLabels`, `ExperimentsScreen`, `ExperimentDetailScreen`); services and utilities carry no direct coverage.

**Acceptance**
- [ ] Add tests for: `services/apiClient.ts`, `services/fetchWithProgress.ts`, `utils/experimentStatus.ts`
- [ ] Add tests for key components: `VectorDbStatsPanel`, `ConfirmDeleteModal`, `ExperimentControlButtons`

### 2. Coverage not embedded in the gate
Backend gate embeds coverage + fail-under; frontend gate runs bare `npm run test` — no report, no floor.

**Acceptance**
- [ ] Pre-push + CI frontend job: `npm run test` → `npm run test:coverage` (coverage table in gate output)
- [ ] `coverage.thresholds` in `vite.config.ts` — floor starts at the measured baseline, ratchets up over time
- [ ] Baseline frontend line in `CLAUDE.md` / `development.md` records the floor + notes the embedded report
- [ ] PROGRESS Decision Log row captures the chosen baseline number and ratchet intent

**Won’t:** 100% coverage; e2e / browser tests (separate slice)

**Refs:** `frontend/package.json` scripts; `frontend/vite.config.ts` coverage block; `scripts/pre-push-gates.sh` step 3/3.

---

## Spec (GWT)

```
Scenario: Frontend gate embeds coverage like the backend
  Given the frontend quality-gate / pre-push path
  When tests run with coverage enabled
  Then the summary includes a coverage table
  And the run fails below the configured floor

Scenario: New tests lift measured coverage above the floor
  Given the newly added service/util/component tests
  When the coverage report is generated
  Then measured coverage is at or above the configured threshold
```

---

## Before-Checks [GATE]

- [ ] Existing frontend suite green (`npm run test`, `npm run typecheck`, `npm run build`)
- [ ] Measure current coverage to set an honest baseline floor

---

## After-Checks [GATE]

- [ ] §1 New tests added for named services/utils/components
- [ ] §2 Pre-push + CI emit a coverage table and enforce the floor
- [ ] Baseline logged in `CLAUDE.md` / `development.md` and PROGRESS Decision Log
- [ ] Frontend baseline in `CLAUDE.md` updated (test count + coverage floor)
- [ ] No backend / migration-track regression

## Gate Status

📋 PLANNED
