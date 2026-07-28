# Slice 44: Frontend Test Coverage + Coverage in Gate Summary

> Scenario: Brownfield + Growing Requirement (Flow D) | MoSCoW: Should

**Target time:** ~3–4 h · **Estimated Pomos:** `3–4` — coverage Must (~2 Pomos) + FE Should tests + structure taxonomy Should (~1–2 Pomos)
**Status:** ✅ COMPLETE — Phase A + Phase B + ✅ APPROVED (2026-07-27 nw-software-crafter-reviewer). **Residual §4 open** — Nightly Stryker 1h timeout after suite growth (DECISIONS #163).
**Depends on:** none (external slices); requires existing frontend test harness (Vitest + `@vitest/coverage-v8` already in `frontend/`)
**Non-blocking / non-urgent:** Pure CI-hygiene parity — does not gate any backend / PCTO slice.

**Phase A (✅ 2026-07-27):** Coverage embedded in gates; floor ratcheted to ~64% lines after Should tests.
**Phase B (✅ 2026-07-27):** Floor raised to **≥95%** stmts/funcs/lines + **≥90%** branches (`all: true`) — DECISIONS #139.
**Uniform overall ≥90% (✅ 2026-07-27):** interim BE `--cov-fail-under=90` — DECISIONS #140 (**superseded** by #142).
**Fair metric floors (✅ 2026-07-27):** interim FE **95/90/95/95** + soft BE **92/85/n/a/90** — DECISIONS #141 (**superseded** by #142).
**Shared product floors (✅ 2026-07-27):** FE **95/90/95/95**; BE **95/90/n/a/95** via `fail_under=95` + `scripts/check_backend_coverage_floors.py` — DECISIONS #142. Postgres module CI gate remains ≥95%.

**Secondary goal:** Publish a Behavior | Feature | Function theme map and ranked folder-separation proposals for flat hotspots (planning only — no filesystem moves in this slice). Follow-on execution → [`SLICE-45-MODULE-THEME-SEPARATION.md`](SLICE-45-MODULE-THEME-SEPARATION.md).

**Origin:** Spun out of SLICE-43 on 2026-07-26 (enhanced-flow-planner quality lens, SLAP check 3): frontend-coverage hardening is a different abstraction level from Supabase config verification. Migrated to latest plan-generator stub shape on 2026-07-26 against live codebase baseline. Structure taxonomy Should task added 2026-07-27 (DECISIONS #135).

### Elevator Pitch (DoR Dimension 0)

**Before**: Frontend quality gate runs bare Vitest with no coverage report or threshold enforcement. Backend has `pytest --cov-fail-under` floor. Asymmetry signals incomplete CI parity.

**After**: Frontend gate embeds coverage report (v8 text formatter), prints coverage table, fails when measured coverage falls below configured floor (measured baseline: 50.18% lines).

**Decision enabled**: Contributors see whether new code maintains frontend test health; maintainers enforce baseline discipline across releases.

### Definition of Ready Waiver

This is a **CI-hygiene infrastructure slice** (non-user-facing, per DECISIONS #135). Per framework:
- **DoR Item 2 (Persona)**: WAIVED — infrastructure-only work has no user persona. Audience: contributors + maintainers (implicit).
- **DoR Item 3 (Domain examples)**: Satisfied by Before-Check re-measure gate. Concrete baseline: Lines 50.18%, Branches 47.74%, Functions 45.38% (verified 2026-07-26).
- **JTBD traceability**: N/A — no `job_id` required for @infrastructure slices.

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

## Review Summary (2026-07-27)

**Verdict**: ✅ **APPROVED** — No blocking issues.

**Scope reviewed**: All production + test changes (40 files, 7064 insertions).

**Key findings**:
- ✅ **Floors enforced across all gates**: local (quality-gates.sh), pre-push (pre-push-gates.sh), CI (.github/workflows/ci.yml) — verified end-to-end
- ✅ **Measured coverage exceeds floors**: FE 98.21/92.89/99.7/99.61 (floor 95/90/95/95); BE 98.60/95.21/98.60 (floor 95/90/95)
- ✅ **Test integrity**: No weakened assertions, no deleted tests, no testing theater (GWT structure + docstrings on all 252 tests)
- ✅ **Composition**: Primitives reusable (check_backend_coverage_floors.py as standalone CLI; test factories composable via overrides)
- ✅ **Production changes surgical**: Only ExperimentsScreen.tsx modified (6-line reorder, behavioral equiv)
- ✅ **Documentation disciplined**: DECISIONS #139–#142 logged; pyproject.toml + vite.config.ts floors paired with inline references

**Non-blocking observations**:
- FE test docstrings ~95% compliant (brownfield migration ongoing; not a gate issue)
- Backend functions metric omitted by design (coverage.py limitation; FE carries it)

**Adversarial refutation lenses**:
1. Correctness — all AC satisfied ✓
2. Does-it-reproduce — gates execute, produce reports, floors enforced ✓
3. Wiring & oracle soundness — floors enforced; configuration drift guarded by comments ✓
4. Test integrity — zero G9 violations ✓
5. Composition — primitives independently usable ✓

---

## Slice Workflow Bundle

- Slice name: `slice-44-frontend-coverage-gate`
- Branch: `slice/44-frontend-coverage-gate`
- Files (expected):
  - `frontend/vite.config.ts` — `coverage.thresholds` **95/90/95/95** (`all: true`; DECISIONS #142)
  - `frontend/package.json` — gate path: local `quality-gates`/`pre-push` use `npm run test:coverage`; CI frontend job uses `npm run test:ci` (coverage + JUnit via config `outputFile`)
  - `scripts/quality-gates.sh` — FE `test:coverage`; BE `--cov-fail-under=95` + JSON floor checker
  - `scripts/pre-push-gates.sh` — same FE/BE coverage gates as quality-gates
  - `.github/workflows/ci.yml` — frontend `test:ci`; backend unit job fail-under + checker
  - `pyproject.toml` — `fail_under=95` + `[tool.rag_params_finder.coverage_thresholds]` (95/90/95)
  - `scripts/check_backend_coverage_floors.py` — BE stmts/br/lines gate (functions n/a)
  - `tests/test_check_backend_coverage_floors.py` / `tests/test_coverage_floor_gaps.py` — checker + gap coverage
  - new `frontend/src/**/*.test.ts(x)` for Must/Should modules below
  - `CLAUDE.md` / `docs/contributor-guide/development.md` — FE+BE baseline + floor note
  - `docs/contributor-guide/module-theme-map.md` — Behavior | Feature | Function SSOT (taxonomy Should)
  - Canvas: optional IDE canvas `project-structure-taxonomy.canvas.tsx` (not required in-repo; theme map is SSOT)
  - `docs/plan/slices/SLICE-45-MODULE-THEME-SEPARATION.md` — follow-on move proposal stub (PLANNED; not executed here)
- Exit criteria: FE+BE gates enforce shared product floors (FE **95/90/95/95**, BE **95/90/n/a/95**); coverage tables print; theme map + Slice 45 stub published with **no** production import-path changes for taxonomy.
- Commit pattern: `test(slice-44): add frontend coverage floor and embed report in gate` (+ optional `docs(slice-44): publish module theme map and Slice 45 stub`)

## Branch

`slice/44-frontend-coverage-gate`

---

## Goal

Bring the frontend quality gate to parity with the backend: backend embeds coverage (`pytest --cov-report=term-missing --cov-fail-under=…`) while frontend still runs bare Vitest. Coverage tooling already exists (`vite.config.ts` v8 + `test:coverage` / `test:ci`) but is never invoked by quality-gates, pre-push, or CI — so there is no report or floor in the gate summary.

Secondary: publish a repo theme map (Behavior | Feature | Function) and ranked separation proposals for five flat hotspots, handing execution to Slice 45.

---

## In-scope work (MoSCoW for this slice)

| Priority | Item | Detail |
|----------|------|--------|
| **Must** | Embed coverage in local + CI gates | §2 — `quality-gates.sh`, `pre-push-gates.sh`, `.github/workflows/ci.yml` emit coverage table |
| **Must** | Configure honest floor | §2 — `coverage.thresholds` in `vite.config.ts` starts at measured baseline (lines ≈50%; confirm on Before-Check re-measure) |
| **Must** | Record baseline in docs + Decision Log | §2 — `CLAUDE.md` / `development.md` + PROGRESS Decision Log row |
| **Should** | Tests for modules on critical dashboard paths | §1 — apiClient, fetchWithProgress, experimentStatus, key control/stats components |
| **Should** | Project structure taxonomy audit | §3 — theme map doc + canvas + Slice 45 reorg proposal for five hotspots (planning only) |
| **Must (Phase B)** | Near-100% FE coverage floor (option 1) | `coverage.thresholds`: statements/functions/lines **≥95**, branches **≥90**; `all: true` on `src/**`; excludes: `*.test.*`, `src/test/**`, `main.tsx`, types-only |
| **Must (#142)** | Shared FE+BE product floors | FE Vitest **95/90/95/95**; BE **95/90/n/a/95** via `fail_under=95` + `scripts/check_backend_coverage_floors.py` (wired in quality-gates / pre-push / CI) |
| **Won’t (44)** | Execute folder moves / import rewrites; literal 100% branch on every UI edge; e2e/browser tests; ESLint/Vite major bumps; invent coverage.py function metric | Moves → Slice 45; e2e / toolchain → separate slices; BE functions remain n/a |

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

Scenario: Structure taxonomy is published for operators and agents
  Given the repo trees (server, cli, frontend, tests, scripts, configs, docs, root)
  When the Slice 44 Should audit task completes
  Then a Behavior|Feature|Function theme map exists in docs
  And the five flat hotspots have ranked separation proposals
  And no production import paths were changed in this slice

Scenario: Shared product floors gate FE and BE identically where tooling allows
  Given Vitest coverage.thresholds and the backend unit coverage JSON report
  When quality-gates / pre-push / CI run the coverage steps
  Then FE fails below 95/90/95/95 (stmts/br/fn/lines)
  And BE fails below 95/90/n/a/95 via fail_under plus check_backend_coverage_floors.py
```

---

## Residual issues

### 1. Untested / low-coverage modules on critical dashboard paths (Should)

Only 3 frontend test files today. Target modules are on the live polling / control path:

| Module | Why (usage) | Baseline coverage (approx) |
|--------|-------------|------------------------------|
| `services/apiClient.ts` | Imported by all experiment screens + control buttons | ~4.5% lines |
| `services/fetchWithProgress.ts` | Used by loading / large payload fetches | ~15% lines |
| `utils/experimentStatus.ts` | Status badges / terminal outcome helpers on list + detail | low / indirect |
| `VectorDbStatsPanel`, `ConfirmDeleteModal`, `ExperimentControlButtons` | List/detail UX; delete + pause/resume/cancel | mostly untested |

**Acceptance**
- [x] Add tests for: `services/apiClient.ts`, `services/fetchWithProgress.ts`, `utils/experimentStatus.ts`
- [x] Add tests for key components: `VectorDbStatsPanel`, `ConfirmDeleteModal`, `ExperimentControlButtons`
- [x] After adds, `npm run test:coverage` stays ≥ configured floor (ratchet note in Decision Log if floor raised)

### 2. Coverage not embedded in the gate (Must)

| Surface | Today (VERIFIED) | Target (LOCKED 2026-07-27 review remediation) |
|---------|------------------|-----------------------------------------------|
| `scripts/quality-gates.sh` §8 | `npm run test` | `npm run test:coverage` (v8 **text** reporter in summary) |
| `scripts/pre-push-gates.sh` | `npm run test` | `npm run test:coverage` |
| CI `frontend` job | `npm run verify` (vitest **sans** coverage) | `npm run test:ci` (+ typecheck/build as today); coverage table + threshold fail |
| `vite.config.ts` | `provider: 'v8'`, reporters `text`/`json`/`html`; **no** thresholds | + `coverage.thresholds` from Before-Check re-measure |

**Acceptance**
- [x] Pre-push + quality-gates: `test:coverage`; CI test leg: `test:ci` — coverage table (v8 text) in gate output
- [x] `coverage.thresholds` in `vite.config.ts` — floor starts at **re-measured** baseline (reference: lines **50.18%**, branches **47.74%**, functions **45.38%**, statements **48.48%** on 2026-07-26); ratchet intent logged
- [x] Baseline frontend line in `CLAUDE.md` / `development.md` records the floor + notes the embedded report
- [x] PROGRESS Decision Log row captures the chosen baseline number and ratchet intent

**Refs:** `frontend/package.json` scripts; `frontend/vite.config.ts` coverage block; `scripts/quality-gates.sh` §8; `scripts/pre-push-gates.sh` frontend step; `.github/workflows/ci.yml` `frontend` job.

### 3. Project structure taxonomy audit (Should)

Flat folders mix Behavior / Feature / Function concerns. Publish a theme map and ranked separation **proposals**; do not move files in Slice 44.

Taxonomy artifacts were **pre-published** on 2026-07-27 as planning SSOT (`module-theme-map.md`, canvas, SLICE-45 stub). After-Checks §3 `[x]` means those artifacts exist and links resolve — **not** that Slice 44 overall is COMPLETE (coverage Must remains open).

| Hotspot | Approx files | Proposed folders (proposal only) |
|---------|--------------|----------------------------------|
| `server/core/` | 24 | `pipeline/`, `embedding/`, `rerank/`, `retrieval/`, `guards/` (+ keep `chunkers/`) |
| `server/db/` | 14 | `ports/`, `mongo/`, `postgres/` |
| `tests/` | 36 top-level | mirror packages or `unit/` + existing `contract/` / `helpers/` |
| `frontend/src/components/` | 16 | `screens/`, `chrome/`, `experiment/`, `stats/` |
| `scripts/` | 16 | `ci/`, `docker/`, `release/`, `security/` (+ keep `lib/`) |

**Acceptance**
- [x] [`docs/contributor-guide/module-theme-map.md`](../../contributor-guide/module-theme-map.md) lists major trees with Behavior \| Feature \| Function tags
- [x] Interactive canvas was planned as `project-structure-taxonomy.canvas.tsx` — **not shipped in-repo**; theme map SSOT is [`module-theme-map.md`](../../contributor-guide/module-theme-map.md) (DECISIONS #135)
- [x] [`SLICE-45-MODULE-THEME-SEPARATION.md`](SLICE-45-MODULE-THEME-SEPARATION.md) exists as 📋 PLANNED with concrete move tables
- [x] No production import paths changed for taxonomy in this planning pass (DECISIONS #135)

**Theme labels**

| Level | Meaning | Examples |
|-------|---------|----------|
| **Behavior** | Runtime / lifecycle concern | pipeline phases, preflight guards, storage mode, polling |
| **Feature** | Product capability | experiments CRUD, sweep, embed/rerank providers, Search Explorer screens |
| **Function** | Layer / utility / ops | ports/factory, models, utils, quality-gates scripts, types |

### 4. Nightly Stryker timed out after suite growth (Must residual — DECISIONS #163)

**Cause (VERIFIED):** Slice 44 Phase B / PR [#121](https://github.com/neomatrix369/rag-params-finder/pull/121) expanded Vitest from **16** tests / 3 files → **~252** tests. Nightly Stryker still mutates all `src/**/*.{ts,tsx}` (~3770 mutants, `concurrency: 2`, `timeout-minutes: 60`). Post-merge Nightly jobs cancel at 1h with no `frontend/reports/mutation/` artifact ([run 30329826459](https://github.com/neomatrix369/rag-params-finder/actions/runs/30329826459/job/90182449893)). Last success (~24m) was on pre-#121 SHA with 16 dry-run tests.

Mutation was waived locally (#138) to nightly; this residual restores that nightly signal without inventing screen mutation (Slice 45 Won't / #160).

**Acceptance**

#### Must
- [ ] Narrow `frontend/stryker.config.js` `mutate` to pure logic only: `src/utils/**/*.ts`, `src/services/**/*.ts`, `src/hooks/**/*.ts` (exclude screens/components/chrome/types/main)
- [ ] Nightly `workflow_dispatch` (or next cron): Stryker finishes **without** GHA 1h cancel; `mutation-node-*` artifact present (**VERIFIED** with run URL)

#### Should
- [ ] `ignoreConstants: true` + `ignoreStringLiterals: true` (optional `ignoreStatic`)
- [ ] Raise `concurrency` (e.g. 4); add `progress` reporter for CI visibility
- [ ] Note in `docs/contributor-guide/development.md`: Nightly mutate scope = utils/services/hooks

#### Could
- [ ] Raise `mutation-tests-node` `timeout-minutes` to 90 (safety net only — not a substitute for Must)
- [ ] Pin `@stryker-mutator/core` + `@stryker-mutator/vitest-runner` in `frontend/package.json`

#### Won't / NIT
- [ ] **Won't:** Restore full-tree mutate of screens/components
- [ ] **NIT:** `actions/upload-artifact@v4` → `@v5` (Node 20 deprecation warning)

**Files:** `frontend/stryker.config.js`, `.github/workflows/nightly.yml`, optionally `frontend/package.json` + `development.md`

---

## Before-Checks [GATE]

- [x] Branch `slice/44-frontend-coverage-gate` created
- [x] Existing frontend suite green (`npm run test`, `npm run typecheck`, `npm run build`)
- [x] Confirm `frontend/vite.config.ts` already has `coverage.provider: 'v8'` and reporters including `text` (VERIFIED present 2026-07-27; thresholds still absent until this slice)
- [x] Re-measure coverage (`npm run test:coverage`) and lock the floor number in the Decision Log (do not invent a number from memory)
- [x] Gate scripts locked: local/pre-push → `test:coverage`; CI → `test:ci` (JUnit `outputFile` already in vite config — do **not** pass CLI `--reporter=junit` alone)

---

## TDD Execution

**Style:** outside-in for gate behaviour (acceptance: gate command fails below floor) + unit tests for services/utils; component tests via Testing Library for UI Should items. Taxonomy Should is documentation/planning only (no TDD for moves).

**Sequence:** RED → GREEN → REFACTOR PROD → REFACTOR TESTS → VERIFY+COVERAGE → (taxonomy already published)

**VERIFY+COVERAGE command (frontend):**

```bash
cd frontend && npm run test:coverage   # local + quality-gates + pre-push
# CI frontend test leg:
cd frontend && npm run test:ci         # coverage + JUnit via vite.config reporters
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
1. **Specification coverage** — every GWT clause above has ≥1 test (gate failure below floor + table present; new-module behaviours if Should landed); taxonomy GWT satisfied by published artifacts + Decision Log (no code test)
2. **Product metric floors (DECISIONS #142)** — FE Vitest **95/90/95/95**; BE **95/90/n/a/95** (`fail_under=95` + `check_backend_coverage_floors.py`; not whole-tree 100% — see Won’t)
3. **Mutation testing** — waive local Stryker for this CI-hygiene slice unless new pure util logic is non-trivial; log waiver in Decision Log (pattern: DECISIONS #128)

On PASS: write gate evidence → `docs/plan/gate-evidence/slice-44.json` (note audit artifacts + “no moves” scope boundary).

---

## After-Checks [GATE]

- [x] §1 Should tests added for named services/utils/components **or** explicitly deferred with Decision Log row + floor still honest
- [x] §2 quality-gates + pre-push + CI emit a coverage table and enforce the floor
- [x] §3 theme map + canvas + Slice 45 stub published; no import-path moves for taxonomy *(links resolve; does not imply Slice 44 COMPLETE)*
- [x] Baseline logged in `CLAUDE.md` / `development.md` and PROGRESS Decision Log
- [x] Frontend baseline in `CLAUDE.md` updated (test count + coverage floor)
- [x] No backend / migration-track regression (`./scripts/quality-gates.sh` green)
- [x] Code committed with `test(slice-44): …` (or conventional equivalent)
- [x] Specification coverage: every GWT clause has ≥1 test (BDD/GWT-first); essential error paths covered (90–100% of clauses); taxonomy GWT via artifacts
- [x] Product coverage floor enforced via `coverage.thresholds` / BE `fail_under` (shared **95/90/95/95** aim — DECISIONS #142); whole-tree literal 100% branch **Won’t**
- [x] **Shared FE metric floors (DECISIONS #142)** — `frontend/vite.config.ts` `coverage.thresholds` = statements **≥95**, branches **≥90**, functions **≥95**, lines **≥95**. Verify: `cd frontend && npm run test:coverage` exits 0 (reference: 98.21 / 92.89 / 99.7 / 99.61)
- [x] **Shared BE metric floors (DECISIONS #142)** — **95/90/n/a/95** (stmts/br/fn/lines): `fail_under=95` plus `scripts/check_backend_coverage_floors.py` on JSON report (pyproject `[tool.rag_params_finder.coverage_thresholds]`). Functions n/a on coverage.py. Verify: unit pytest + checker exits 0 (reference stmts ≈98.6% / br ≈95.2% / TOTAL ≈97.7%). Postgres `retriever_postgres` module gate **≥95%** remains separate
- [x] Mutation testing: run if non-trivial pure logic added; else waiver row in Decision Log (§23) — **local waive #138**; nightly broken by suite growth → residual §4 / #163
- [ ] Residual §4 Nightly Stryker budget restored (narrow mutate + artifact) — open 2026-07-28
- [x] Docs updated (14-row audit below)
- [x] `docs/plan/gate-evidence/slice-44.json` written (`fair_metric_floors` / `shared_metric_floors` + #142)
- [x] Troubleshooting note for “coverage floor failed” (how to read v8 table / raise floor) in `development.md` or troubleshooting — **Recommended**

---

## Doc Audit (14-row checklist)

| # | Item | Check |
|---|------|-------|
| 1 | README updated | N/A — contributor/dev gates only unless README claims frontend gate shape |
| 2 | Inline comments added where non-obvious | threshold / ratchet rationale in vite config if non-obvious |
| 3 | Function signatures documented | N/A unless new exported helpers |
| 4 | Error paths documented | apiClient / fetch error paths covered by tests |
| 5 | CHANGELOG entry written | Unreleased — theme map + coverage floor in gates (**VERIFIED** 2026-07-27) |
| 6 | Architecture doc updated | Pointer to `module-theme-map.md` under Module Map |
| 7 | API doc updated | N/A |
| 8 | Config/env vars documented | N/A |
| 9 | Examples added or updated | N/A |
| 10 | Deprecated features marked | N/A |
| 11 | Migration guide written | N/A — Slice 45 owns move execution notes |
| 12 | Troubleshooting section added | **Done** — “coverage floor failed” in `development.md` Frontend baseline |
| 13 | Related links cross-referenced | CLAUDE.md ↔ development.md ↔ this slice ↔ theme map ↔ Slice 45 ↔ `check_backend_coverage_floors.py` |
| 14 | No orphaned file references | gate scripts + CI job paths match; theme-map / Slice 45 / BE checker links resolve |

---

## Gate Status

✅ PASSED — Phase A/B + #142: FE **95/90/95/95** measured **98.21 / 92.89 / 99.7 / 99.61** (252 tests); BE **95/90/n/a/95** measured stmts ≈**98.6%** / br ≈**95.2%** / TOTAL ≈**97.7%** (`fail_under=95` + JSON checker; ~335 unit tests)

## What Changed

| File | Type | Reason |
|------|------|--------|
| `frontend/vite.config.ts` | config | Shared floors **95/90/95/95** (#142); `all: true` |
| `frontend/package.json` | config | `test:ci` = coverage without overriding JUnit reporters |
| `scripts/quality-gates.sh` / `pre-push-gates.sh` | ci | FE `test:coverage`; BE fail-under=95 + floor checker |
| `.github/workflows/ci.yml` | ci | frontend `test:ci`; backend unit fail-under + checker |
| `pyproject.toml` | config | `fail_under=95` + `[tool.rag_params_finder.coverage_thresholds]` |
| `scripts/check_backend_coverage_floors.py` | ci | Enforce BE stmts/br/lines **95/90/95** from coverage JSON |
| `tests/test_check_backend_coverage_floors.py` | test | Checker unit tests |
| `tests/test_coverage_floor_gaps.py` | test | Raise BE stmts/branch to clear #142 floors |
| `frontend/src/**/*.test.ts(x)` | test | Phase A critical-path + Phase B thin-module / branch push + mop-up |
| `frontend/src/components/ExperimentsScreen.tsx` | fix | Dead/unreachable loading-panel + redundant aliveRef branches trimmed for honest coverage |
| `CLAUDE.md` / `development.md` / CHANGELOG / DECISIONS / PROGRESS / HANDOFF | docs | baselines + #138–#142 + mop-up / checker |
| `docs/plan/gate-evidence/slice-44.json` | docs | gate evidence (Phase A + B + mop-up + #142) |
| `docs/contributor-guide/module-theme-map.md` | docs | Theme SSOT (§3) |
| `docs/plan/slices/SLICE-45-MODULE-THEME-SEPARATION.md` | docs | Follow-on move proposal |

## Session Metrics

| Metric | Value |
|--------|-------|
| Estimated Pomos | 3–4 Phase A + ~2–3 Phase B |
| Execution time | Phase A + Phase B + #142 floors (2026-07-27) |
| Blockers encountered | none |
| Next-session notes | Commit/push #142 checker + floors; refresh PR #121; Slice 45 owns folder moves |

---

## Remediation pass (2026-07-27)

Applied nw-documentarist + nw-product-owner findings (DECISIONS #137):

- Depends-on clarifies Vitest + coverage-v8 harness
- Locked gate scripts (`test:coverage` local / `test:ci` CI) + v8 text reporter
- Before-Checks confirm existing `vite.config.ts` coverage block
- §1 usage metrics for target modules; §2 concrete baseline numbers; §3 status vs COMPLETE clarified
- Doc Audit troubleshooting → Recommended; Elevator Pitch + DoR Waiver already present from PO review

**Updated PO path-to-approval:** remediations APPLIED → treat DoR as **APPROVED** for execution (coverage Must still PLANNED).

---

## Review Metadata

**Date**: 2026-07-27
**Reviewer**: nw-documentarist-reviewer (Quill)
**Verdict**: **APPROVED** — Ready to execute with Before-Checks clarifications
**Review ID**: `doc_rev_20260727_slice44`
**Remediation**: Findings addressed in remediation pass 2026-07-27 (#137)

### Summary

Slice specification is well-structured with clear goals, MoSCoW prioritization, and hierarchical acceptance criteria. Baseline is VERIFIED with audit trail (2026-07-26, `npm run test:coverage`). No blocking issues; one high-severity inaccuracy (line 7 "Depends on: none" omits required frontend test harness) and three medium-severity clarifications needed in Before-Checks.

### Findings

**Blocking**: None

**High**:
- Line 7: "Depends on: none" inaccurate — should note required vitest + c8 infrastructure

**Medium**:
- Before-Checks missing confirmation: Confirm vite.config.ts coverage block exists
- Lines 119–125: CI script choice (test:ci vs test:coverage) and v8 output format not locked down
- Line 201 vs. 237: Taxonomy artifacts pre-published; clarify After-Checks verifies links only

**Low**:
- Lines 127–137: Extract prose explanation before hotspot table
- Row 12 (Doc Audit): Change troubleshooting from "optional" to "Recommended"
- Line 106: Quantify "high-value" modules with usage metrics

### Recommendations (Priority Order)

1. **MUST** — Fix line 7: Change "Depends on: none" to "Depends on: none (external slices); requires: existing frontend test harness (vitest + c8 v8)"
2. **SHOULD** — Add Before-Checks gate: "Confirm vite.config.ts has coverage block with `provider: 'v8'` and reporters configured"
3. **SHOULD** — Clarify Must §2: "Confirm CI will run `npm run test:ci` [or test:coverage]; lock choice here and in vite.config.ts"
4. **SHOULD** — Extract prose before hotspot table (§3): Move "Flat folders mix…" to a context paragraph preceding the table
5. **COULD** — Update row 12 (Doc Audit) from "optional" to "Recommended" for coverage troubleshooting
6. **COULD** — Add usage metrics to line 106 (quantify "high-value" services)

### Praise

✅ VERIFIED baseline (proof audit trail included)
✅ Pre-published planning artifacts (theme map, canvas, SLICE-45) — disciplined execution
✅ Hierarchical Before/After gates prevent scope creep
✅ GWT scenarios are testable and specific
✅ Strong cross-references to related docs (PROGRESS, CLAUDE.md, module-theme-map)
✅ Decision Log integration built into spec structure

---

## Review Metadata: nw-product-owner-reviewer (Eclipse) | 2026-07-27

**Verdict: `REJECTED_PENDING_REVISIONS`** — Well-scoped CI-hygiene work. **BLOCKED** on 3 DoR hard gates before design-wave handoff.

> **Remediation 2026-07-27 (#137):** Elevator Pitch + DoR Waiver were added during this review; remaining documentarist/PO clarifications (script lock, usage metrics, §3 status) applied in remediation pass. **Superseding verdict: APPROVED for execution** (coverage Must still 📋 PLANNED).

### Definition of Ready Assessment

| Item | Status | Evidence | Severity |
|------|--------|----------|----------|
| 1. Problem statement | ✅ PASS | "Bring frontend … to parity with backend" — domain language, testable | — |
| 2. User/persona | ❌ FAIL | Infrastructure-only slice; no user persona. **WAIVABLE** for @infrastructure work. | **critical** |
| 3. Domain examples | ❌ FAIL | No Before/After metrics example (e.g., "lines 50.18% → must stay ≥50%"). **REMEDIABLE**. | **high** |
| 4. UAT format | ✅ PASS | 3 GWT scenarios with complete Given/When/Then structure (lines 76–95) | — |
| 5. AC from UAT | ✅ PASS | Acceptance checklists (§1–3) map to GWT clauses | — |
| 6. Sizing | ✅ PASS | 3–4h, 3 scenarios, single outcome | — |
| 7. Tech notes | ✅ PASS | File paths listed (lines 34–38), constraints noted (line 176–177) | — |
| 8. Dependencies | ✅ PASS | "Depends on: none" + Non-blocking claim (lines 7–8) | — |
| 9. KPIs | ✅ PASS | Floor = measured baseline (50.18%), ratchet intent in Decision Log | — |

**Pass count: 7/9**

### Hard Gates Assessment

| Gate | Status | Evidence | Severity |
|------|--------|----------|----------|
| **Dimension 0: Elevator Pitch** | ❌ FAIL | No "### Elevator Pitch" section with Before/After/Decision lines. **BLOCKING** per nw-po review framework. | **critical** |
| **JTBD Traceability** | ⏸️ WAIVED | Infrastructure-only slice; no user job_id required. Waiver must be **documented** in spec. | **high (waivable)** |

### Blocking Issues

**Issue 1: Missing Elevator Pitch (Dimension 0 hard gate)** [**CRITICAL**]
- **Location**: Start of spec (after Origin section)
- **Recommendation**: Add 3-line section:
  ```markdown
  ### Elevator Pitch

  **Before**: Frontend gate runs bare Vitest; no coverage report or threshold enforcement. Backend has `pytest --cov-fail-under` floor.
  **After**: Frontend gate embeds coverage report, prints coverage table, fails when below 50% lines floor.
  **Decision enabled**: Contributors see if new code maintains test health; maintainers enforce baseline.
  ```

**Issue 2: DoR Item 3 — No example metrics** [**HIGH**]
- **Location**: Acceptance §2 (line 119+) and/or Before-Checks
- **Recommendation**: Add concrete example:
  ```
  Example baseline metrics to maintain: Lines ≥50.18%, Branches ≥47.74%, Functions ≥45.38%.
  If new tests raise coverage, ratchet floor upward by intention (document in Decision Log why).
  ```

**Issue 3: DoR Item 2 — Persona not waived** [**HIGH**]
- **Location**: Top of spec (new subsection after Elevator Pitch)
- **Recommendation**: Add DoR Waiver section:
  ```markdown
  ### Definition of Ready Waiver

  This is a **CI-hygiene infrastructure slice**. Per DECISIONS #135:
  - **Item 2 (Persona)**: WAIVED — no user-facing feature. Audience: contributors + maintainers (implicit).
  - **Item 3 (Examples)**: Satisfied by Before-Check re-measure gate (lock floor before execution).
  - **JTBD traceability**: N/A — no user job_id for @infrastructure work.
  ```

### Antipattern Detection

| Pattern | Found | Severity | Evidence | Fix |
|---------|-------|----------|----------|-----|
| 1. Implement-X | ❌ NO | — | GWT uses outcome language (coverage table, threshold fail) | — |
| 2. Generic Data | ❌ NO | — | Real file paths + measured numbers (50.18% baseline) | — |
| 3. Technical AC | ⚠️ MIXED | low | Some AC mix file names (`vite.config.ts`) with outcome. Acceptable for ops work. | Clarify: "When vite.config.ts floor is configured → gate enforces" |
| 4. Giant Stories | ❌ NO | — | Right-sized: 3–4h, 3 scenarios | — |
| 5. No Examples | ⚠️ PARTIAL | high | GWT specific; before/after metrics missing for floor measure | Add concrete floor metrics (see Issue 2) |
| 6. Tests After Code | ⚠️ MINOR | medium | Line 83: "newly added tests (Should)" + checkboxes suggest deferred tests. **NOT** post-code deferral; TDD execution section (line 179–207) is clear. Minor phrasing clarification needed. | Rephrase §1 acceptance: "Test framework(s) selected for services/utils/components (RED–GREEN–REFACTOR)" instead of "Add tests for" |
| 7. Vague Persona | — | — | N/A for infrastructure slice | — |
| 8. Missing Edge Cases | ❌ NO | — | Covers happy (table) + edge (floor boundary) + error (fail below floor) | — |

**Antipatterns clean.** One minor TDD phrasing → clarity fix (Issue 3b, optional).

### Strengths (Radical Candor: Kind + Clear)

✅ **Clear MoSCoW + scope boundaries** — Must (coverage floor) ≠ Should (tests + taxonomy) ≠ Won't (100% coverage, e2e). Prevents scope creep.

✅ **Taxonomy Should IMPLEMENTED early** — Artifacts shipped 2026-07-27 (theme map + canvas + SLICE-45 stub). Half of Should scope de-risked before execution.

✅ **Measured baseline with re-measure gate** — 50.18% lines captured 2026-07-26 (`npm run test:coverage`). Before-Check re-measure prevents "invented floor" antipattern.

✅ **Residual issues (§1–3) scoped with acceptance checklists** — Checkbox items make PASS/FAIL objective for implementer.

✅ **GWT specs outcome-focused + testable** — Can derive automated tests directly (gate output verification, threshold fail exit code, coverage ≥ floor assertions).

✅ **Doc audit (14 rows) tailored to slice** — Not boilerplate; includes slice-specific checks (gates + CI job path matching, theme-map link resolution).

✅ **Gate evidence protocol established** — `docs/plan/gate-evidence/slice-44.json` ensures audit trail. Pattern reused across slices.

### Path to Approval

1. **Add Elevator Pitch** section (3 lines) — addresses Dimension 0 hard gate
2. **Add DoR Waiver** section (4 lines) — clarifies Item 2 & 3 treatment for infrastructure slice
3. **Add example metrics** to Acceptance §2 (1 line) — provides concrete verification targets
4. *Optional*: Clarify TDD phrasing in §1 acceptance items (1-line clarification)

**After remediations**, re-submit for approval. Expected verdict: **APPROVED**.

### Praise (Per Radical Candor)

**Kind + specific:**
- Disciplined pre-publishing of planning artifacts (DECISIONS #135 decision already locked; no thrashing in-slice).
- Reuse of existing Vitest/v8 tooling (no new deps). Leverages established `vite.config.ts` structure.
- Strong cross-references (CLAUDE.md, PROGRESS.md, module-theme-map.md, SLICE-45). Easy navigation.
- Before/After gates create natural checkpoints. High-quality control.

---

**Reviewer**: Eclipse (nw-product-owner-reviewer)
**Date**: 2026-07-27T12:08:00Z
**Review ID**: `por_rev_20260727_slice44_eclipse`
