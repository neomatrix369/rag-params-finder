# Slice 44: Frontend Test Coverage + Coverage in Gate Summary

> Scenario: Brownfield + Growing Requirement (Flow D) | MoSCoW: Should

**Target time:** ~2–3 h · **Estimated Pomos:** `2 (~50 min) [Walking Skeleton]` — end-to-end: measure → floor → gate wire → docs (tests ratchet in same slice)
**Status:** 📋 PLANNED
**Depends on:** none (frontend/CI hygiene; independent of Supabase migration 32–38)
**Non-blocking / non-urgent:** Pure CI-hygiene parity — does not gate any backend / PCTO slice.

**Origin:** Spun out of SLICE-43 on 2026-07-26 (enhanced-flow-planner quality lens, SLAP check 3): frontend-coverage hardening is a different abstraction level from Supabase config verification. Migrated to latest plan-generator stub shape on 2026-07-26 against live codebase baseline.

**Baseline (VERIFIED 2026-07-26, `cd frontend && npm run test:coverage`):**

| Metric | Value |
|--------|-------|
| Tests | **16** across **3** files (`storageLabels`, `ExperimentsScreen`, `ExperimentDetailScreen`) |
| Statements | 48.48% |
| Branches | 47.74% |
| Functions | 45.38% |
| Lines | **50.18%** |
| `src/services/*` | ~9.8% lines (`apiClient` ~4.5%, `fetchWithProgress` ~15%) |
| `coverage.thresholds` | **absent** in `frontend/vite.config.ts` |
| Gate path today | `quality-gates.sh` + `pre-push-gates.sh` → `npm run test`; CI frontend → `npm run verify` (= vitest **without** coverage) |

---

## Slice Workflow Bundle

- Slice name: `slice-44-frontend-coverage-gate`
- Branch: `slice/44-frontend-coverage-gate`
- Files (expected):
  - `frontend/vite.config.ts` — add `coverage.thresholds` (floor from measured baseline)
  - `frontend/package.json` — ensure gate path invokes coverage (`test:coverage` / `test:ci`; optionally extend `verify` or keep verify for typecheck+build and run coverage separately)
  - `scripts/quality-gates.sh` — frontend step uses coverage-enabled command
  - `scripts/pre-push-gates.sh` — frontend step uses coverage-enabled command
  - `.github/workflows/ci.yml` — frontend job emits coverage table (replace or supplement bare `verify` test leg)
  - new `frontend/src/**/*.test.ts(x)` for Must/Should modules below
  - `CLAUDE.md` / `docs/contributor-guide/development.md` — baseline line + embedded-report note
- Exit criteria: frontend gate (quality-gates + pre-push + CI) runs with coverage enabled, prints a coverage table, and fails below the configured floor; new tests keep measured coverage ≥ floor; baseline logged in PROGRESS Decision Log.
- Commit pattern: `test(slice-44): add frontend coverage floor and embed report in gate`

## Branch

`slice/44-frontend-coverage-gate`

---

## Goal

Bring the frontend quality gate to parity with the backend: backend embeds coverage (`pytest --cov-report=term-missing --cov-fail-under=…`) while frontend still runs bare Vitest. Coverage tooling already exists (`vite.config.ts` v8 + `test:coverage` / `test:ci`) but is never invoked by quality-gates, pre-push, or CI — so there is no report or floor in the gate summary.

---

## In-scope work (MoSCoW for this slice)

| Priority | Item | Detail |
|----------|------|--------|
| **Must** | Embed coverage in local + CI gates | §2 — `quality-gates.sh`, `pre-push-gates.sh`, `.github/workflows/ci.yml` emit coverage table |
| **Must** | Configure honest floor | §2 — `coverage.thresholds` in `vite.config.ts` starts at measured baseline (lines ≈50%; confirm on Before-Check re-measure) |
| **Must** | Record baseline in docs + Decision Log | §2 — `CLAUDE.md` / `development.md` + PROGRESS Decision Log row |
| **Should** | Tests for high-value untested / low-coverage modules | §1 — services, `experimentStatus`, key components |
| **Won’t (44)** | 100% whole-tree frontend coverage; e2e/browser tests; ESLint/Vite major bumps (TRAIL Deferred Work) | Separate toolchain / e2e slices |

---

## Spec (GWT / User Story)

```
Scenario: Frontend gate embeds coverage like the backend
  Given the frontend quality-gate path (quality-gates.sh, pre-push-gates.sh, and CI frontend job)
  When tests run with coverage enabled
  Then the summary includes a coverage table (v8 text reporter)
  And the run fails when measured coverage is below the configured thresholds floor

Scenario: New tests keep measured coverage at or above the floor
  Given the newly added service / util / component tests (Should)
  When the coverage report is generated under the gated command
  Then measured coverage is at or above the configured threshold
  And previously green suites remain green
```

---

## Residual issues

### 1. Untested / low-coverage high-value modules (Should)

Only 3 frontend test files today; services and several utilities/components carry little or no direct coverage.

**Acceptance**
- [ ] Add tests for: `services/apiClient.ts`, `services/fetchWithProgress.ts`, `utils/experimentStatus.ts`
- [ ] Add tests for key components: `VectorDbStatsPanel`, `ConfirmDeleteModal`, `ExperimentControlButtons`
- [ ] After adds, `npm run test:coverage` stays ≥ configured floor (ratchet note in Decision Log if floor raised)

### 2. Coverage not embedded in the gate (Must)

| Surface | Today (VERIFIED) | Target |
|---------|------------------|--------|
| `scripts/quality-gates.sh` §8 | `npm run test` | coverage-enabled (`test:coverage` or `test:ci`) |
| `scripts/pre-push-gates.sh` | `npm run test` | same |
| CI `frontend` job | `npm run verify` (vitest **sans** coverage) | coverage table + threshold fail |
| `vite.config.ts` | provider + reporters only | + `coverage.thresholds` |

**Acceptance**
- [ ] Pre-push + quality-gates + CI frontend job: coverage table in gate output
- [ ] `coverage.thresholds` in `vite.config.ts` — floor starts at measured baseline; ratchet intent logged
- [ ] Baseline frontend line in `CLAUDE.md` / `development.md` records the floor + notes the embedded report
- [ ] PROGRESS Decision Log row captures the chosen baseline number and ratchet intent

**Refs:** `frontend/package.json` scripts; `frontend/vite.config.ts` coverage block; `scripts/quality-gates.sh` §8; `scripts/pre-push-gates.sh` frontend step; `.github/workflows/ci.yml` `frontend` job.

---

## Before-Checks [GATE]

- [ ] Branch `slice/44-frontend-coverage-gate` created
- [ ] Existing frontend suite green (`npm run test`, `npm run typecheck`, `npm run build`)
- [ ] Re-measure coverage (`npm run test:coverage`) and lock the floor number in the Decision Log (do not invent a number from memory)
- [ ] Confirm which npm script CI will call (`test:ci` preferred if JUnit + coverage both required; do not pass Vitest `--reporter=junit` without `outputFile` — already configured in `vite.config.ts`)

---

## TDD Execution

**Style:** outside-in for gate behaviour (acceptance: gate command fails below floor) + unit tests for services/utils; component tests via Testing Library for UI Should items.

**Sequence:** RED → GREEN → REFACTOR PROD → REFACTOR TESTS → VERIFY+COVERAGE

**VERIFY+COVERAGE command (frontend):**

```bash
cd frontend && npm run test:coverage
# or npm run test:ci when JUnit artifact is required
```

Do **not** pass Vitest CLI `--reporter=junit` without a configured `outputFile` — it replaces `test.reporters` and drops the JUnit write already set in `vite.config.ts`.

**Authoritative test-writing rules:** `~/.cursor/rules/test-writing-practices.mdc` + structure/naming + craft-quality siblings.

**Test organisation:**
- Colocate `*.test.ts(x)` next to modules under `frontend/src/` (existing convention)
- Function / describe names read as GWT sentences
- GWT section markers in bodies (`// -- Given --` / `### Given` style per project frontend tests)
- Invalid-input / error-path tables first for `apiClient` / `fetchWithProgress`
- No logic in test bodies (3-strikes → parametrize)

**VERIFY+COVERAGE gate confirms:**
1. **Specification coverage** — every GWT clause above has ≥1 test (gate failure below floor + table present; new-module behaviours if Should landed)
2. **Product branch/line floor** — Vitest `coverage.thresholds` fail_under = measured baseline (not whole-tree 100% — see Won’t)
3. **Mutation testing** — waive local Stryker for this CI-hygiene slice unless new pure util logic is non-trivial; log waiver in Decision Log (pattern: DECISIONS #128)

On PASS: write gate evidence → `docs/plan/gate-evidence/slice-44.json`.

---

## After-Checks [GATE]

- [ ] §1 Should tests added for named services/utils/components **or** explicitly deferred with Decision Log row + floor still honest
- [ ] §2 quality-gates + pre-push + CI emit a coverage table and enforce the floor
- [ ] Baseline logged in `CLAUDE.md` / `development.md` and PROGRESS Decision Log
- [ ] Frontend baseline in `CLAUDE.md` updated (test count + coverage floor)
- [ ] No backend / migration-track regression (`./scripts/quality-gates.sh` green)
- [ ] Code committed with `test(slice-44): …` (or conventional equivalent)
- [ ] Specification coverage: every GWT clause has ≥1 test (BDD/GWT-first); essential error paths covered (90–100% of clauses)
- [ ] Product coverage floor enforced via `coverage.thresholds`; whole-tree 100% branch **Won’t** this slice — exclusions / aspirational craft target documented in Decision Log (§12)
- [ ] Mutation testing: run if non-trivial pure logic added; else waiver row in Decision Log (§23)
- [ ] Docs updated (14-row audit below)
- [ ] `docs/plan/gate-evidence/slice-44.json` written

---

## Doc Audit (14-row checklist)

| # | Item | Check |
|---|------|-------|
| 1 | README updated | N/A — contributor/dev gates only unless README claims frontend gate shape |
| 2 | Inline comments added where non-obvious | threshold / ratchet rationale in vite config if non-obvious |
| 3 | Function signatures documented | N/A unless new exported helpers |
| 4 | Error paths documented | apiClient / fetch error paths covered by tests |
| 5 | CHANGELOG entry written | Unreleased — frontend coverage floor in gates |
| 6 | Architecture doc updated | N/A |
| 7 | API doc updated | N/A |
| 8 | Config/env vars documented | N/A |
| 9 | Examples added or updated | N/A |
| 10 | Deprecated features marked | N/A |
| 11 | Migration guide written | N/A |
| 12 | Troubleshooting section added | optional: “coverage floor failed” → how to read table / raise floor |
| 13 | Related links cross-referenced | CLAUDE.md ↔ development.md ↔ this slice |
| 14 | No orphaned file references | gate scripts + CI job paths match |

---

## Gate Status

📋 PLANNED

## What Changed

| File | Type | Reason |
|------|------|--------|
| — | — | — |

## Session Metrics

| Metric | Value |
|--------|-------|
| Estimated Pomos | 2 (~50 min) [Walking Skeleton] |
| Execution time | — |
| Blockers encountered | — |
| Next-session notes | Re-measure floor on Before-Check; prefer `test:ci` in CI if JUnit artifact still required |
