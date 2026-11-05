# SLICE-67 — Correct and Explainable Dashboard Numbers

**Status:** 🔨 IN PROGRESS — 67A on branch (reviewed), 67C and 67D-1/2/3 built on branches, 67B in progress; nothing merged yet (see *Execution log and amendments*)
**MoSCoW:** Must (67A, 67B) · Should (67C, 67D)
**Depends-on:** none hard · soft: SLICE-66 (Compare screen, partial), SLICE-45 (screen layout)
**Estimated effort:** ~24–31 h across all sub-slices
**Planned date:** 2026-11-05
**Input brief:** [`BRIEF-explainable-numbers.md`](../../BRIEF-explainable-numbers.md) (reviewed by `nw-solution-architect-reviewer` and `nw-product-owner-reviewer`, both "approve with changes", all amendments applied)

> Scenario: Brownfield + Growing Requirement (Flow D). Continuation mode, Add path. Docs only: this stub is a plan, not an implementation.

---

## Context

- **Stage objective:** every number the dashboard prints is correct, and each one shows how it was derived, either as a formula line (`1 model × 5 chunking methods × 3 sizes × 2 overlaps × 1 padding × 4 retrievers = 98 configurations`) or behind an (i) info icon.
- **Depends on:** none hard. Soft: SLICE-66 (Compare screen numbers, partial on `main`), SLICE-45 (screen layout, done).
- **Global invariants:** → [`docs/plan/invariants.md`](../../invariants.md) and [`DECISION-OWNERSHIP.md`](../../DECISION-OWNERSHIP.md).

Audit findings that justify the slice (code-verified on 2026-11-05):

| Id | Finding | Where |
|---|---|---|
| A | Detail "Sweep Dimensions … N combinations" omits the retriever factor; `paddings: []` gives 0 (backend treats `[]` as `[0]`) | `ExperimentDetailScreen.tsx:575-583` |
| B | Explorer Cartesian string is built from distinct values in **completed** `ranked_configs`; retrievers counted by type only; the printed "=" is often false | `ExplorePanels.tsx:255-262, 374` |
| C | `grid_equivalent_count` has two meanings (full grid at creation, `sizes × overlaps` after Bayesian finalize). It is the Bayesian sampler's control variable, so it must **not** be redefined | `experiments.py:216`, `orchestrator.py:244,379,469,530-545` |
| D | List screen double-subtracts Bayesian "not started" | `experimentList/labels.ts:54-76` |
| E | Progress ring and ETA ignore failed and interrupted runs | `ProgressSubtitle.tsx`, `experimentDetailProgress.ts` |
| F | Bayesian cards do not add up to Total (Discarded is not a run) | `ExperimentDetailScreen.tsx:405-427` |
| G | Compare and Walkthru: a lone-run group scores 100.0; silent dedup; the score label hides max-not-average; stats tiles differ per backend; MB estimate unlabeled | `CrossStoreLeaderboard.tsx`, `VectorDbStatsPanel.tsx` |

**Determinism rule (standing, all sub-slices):** every number and every explanation sentence is produced by a named pure function of its inputs (no clock, randomness, I/O, environment, or model-generated text; fixed templates plus numbers; stable ordering). Screens render these values and never compute counts in JSX. Enforced by `frontend/src/utils/deterministicNumbers.guard.test.ts` (extend its module list as helpers land) and, on the backend, by tests that call `sweep_plan()` repeatedly and with equivalent inputs.

Vocabulary decision: **run** = executed · **planned runs** = expected · **configuration** = a distinct parameter set (sweep header) · **trial** = Bayesian only. "Combination" is retired; one glossary in the UI.

## Non-goals

- Redefining `grid_equivalent_count` or changing how the Bayesian sampler stops.
- Persisting a backfill of old experiments (counts are computed on read from `doc["config"]`).
- Compare pagination hiding rows, the Explorer query dropdown shrinking, Redis/ES stats counts, CLI `display.py` (separate tickets).
- A third-party tooltip library.

## Output contract

- **Baseline:** open an experiment with 4 retrievers: Detail header says "N combinations" while the Total tile says a larger number.
- After 67A: the Detail header reads `… = N configurations` and N equals the Total tile.
- After 67B: `GET /experiments/{id}` carries `sweep_plan` (computed on read) and `total_configurations == len(expand_sweep(config))` holds.
- After 67C/67D: every card in the inventory table has a formula line, an info icon, or an explicit "self-explanatory" mark.

---

## Abstraction Views (Delta only; L1/L2 filled at sizing)

- **L1 — Context:** dashboard cards read counts from one backend `sweep_plan`, not from local arithmetic.
- **L2 — Process:** `expand_sweep` (truth) → `sweep_plan` (pure, same module) → API response → `FormulaLine` / `InfoTip`.
- **Delta:** counts move from ~5 independent derivations (3 backend, 2 frontend) to one pure function plus one rendering component.

---

## Sub-slices (order: 67A → 67B → 67C → 67D)

### 67A · Headline fix + shared FormulaLine + number inventory (Must, ~3–4 h, own PR)

- Fix the Detail header to include retrievers (`sweep_summary.retrievers ?? retrieval_methods`) and `paddings.length || 1`; render it as the Cartesian line the owner quoted, using "configurations". Bayesian wording: "varies chunk size × overlap only; uses the first model, method, padding and retriever".
- Extract the Explorer inline formula into a shared `FormulaLine` (`{terms:[{count,label}], total, unit}`, one pluralizer) and use it in both places.
- Deliver the **number inventory table** (screen → card → number → code source → formula → correct or ambiguous → explanation added) in this stub's Appendix. It is the completeness checklist for 67C/67D, and it must include "120 experiments" and pagination counts on the list screen.
- Trivial docs fix rides along: `docs/user-guide/dashboard-guide.md:150` (add the padding axis).

**Oracle (GWT):**

- Given an experiment with 1×5×3×2×1×4 dimensions, When the Detail screen renders, Then the header reads `1 model × 5 chunking methods × 3 sizes × 2 overlaps × 1 padding × 4 retrievers = 120 configurations` and equals the Total tile. *(67A asserts this for grid sweeps, where Total = `run_count`. Bayesian Total/trial sums are 67D, finding F.)*
- Given `paddings: []`, When it renders, Then the padding factor is 1, never 0.
- Given a Bayesian experiment, When it renders, Then the header carries the "varies chunk size × overlap only" note.
- For every `FormulaLine` fixture **with a derived total** (no `observedTotal`), the product of the terms equals the displayed total. An `observedTotal` that differs from the product renders as `(observed)`, never as a false `=`. *(Amended 2026-11-05 after 67A review: the Explorer still passes an observed count until 67D, which removes the prop.)*

### 67B · Backend single source of truth (Must, ~6–8 h)

- In `server/models/config.py` beside `expand_sweep`: pure `sweep_plan(config)` returning `dimension_counts`, `full_grid_count` (= `len(expand_sweep)`), `searchable_space` (Bayesian only), `planned_runs`, `search_strategy`, `warnings` (overlap ≥ size, padding > size).
- Move `resolve_bayesian_n_trials` and the grid helper into `config.py`; `experiments_lifecycle.py` and `orchestrator.py` import from there (no circular or heavy import). Keep `_resolve_bayesian_n_trials` re-exported from the orchestrator (`test_bayesian_finalise.py:18` imports it).
- **Leave `grid_equivalent_count` untouched** (documented as "Bayesian search space").
- Compute `sweep_plan` on read from `doc["config"]`; add an optional `retrievers` label list to `sweep_summary`. Call sites: `experiments.py:181/216/248/473/478`, `experiments_lifecycle.py:28`, `orchestrator.py:440`; `sweep.py:185` keeps new fields optional.
- Mirror types in `frontend/src/types/index.ts` and `experimentDetail/types.ts`; the frontend falls back to the 67A derivation for responses without the new fields.

**Oracle (GWT):**

- Exhaustive parametrized table: `sweep_plan(cfg)["full_grid_count"] == len(expand_sweep(cfg))` over the cross-product of {1, 2} models × {1, 2, 3} chunking methods × {1, 3} chunk sizes × {1, 2} overlaps × {`[0]`, `[]`, `[0, 10]`} paddings × four retriever shapes (duplicate dense, dense plus reranker, two rerankers), 288 cases, with `expand_sweep` as the independent oracle and every axis varying so dropping any factor fails. Each axis is a closed finite domain, so a table (not a generator) is the right paradigm. *(Amended 2026-11-05 after review: was worded "property test".)*
- Given the detail endpoint and a stored experiment lacking the new fields, When `GET /experiments/{id}` is called, Then the response carries `sweep_plan` and `sweep_summary.retrievers`, and a failure inside the plan computation never fails the read. *(Added after review: the endpoint wiring must have its own falsifier.)*
- Given `n_trials` larger than `sizes × overlaps`, the Bayesian stop condition behaves as today.
- Given an old stored experiment without the new fields, the read path returns a correct `sweep_plan`.
- Existing `test_bayesian_finalise.py` and the storage contract tests still pass untouched.

### 67C · Reusable explain UI (Should, ~4–5 h)

- `components/chrome/InfoTip.tsx`: dependency-free; button with `aria-describedby`; Escape closes; target ≥ 44 px; tap toggles at 390 px.
- `StatTile.hint` renders through `InfoTip`; an `explain` prop is added to `StatTile`, `StatCard` and `CollapsibleCard` (on `CollapsibleCard` the tip is a sibling of the toggle, not inside `headerExtra`, which would nest buttons). The tip keeps 8 px inside the viewport (`clampShift`) and closes on resize or orientation change. Explanatory native `title=` uses live in the screens and `ExplorePanels`, so replacing them moves to 67D. *(Amended 2026-11-05 after review.)*

**Oracle (GWT):** the trigger is a native `<button type="button">` in the tab order (not disabled, focusable) whose activation toggles the tip, and Escape closes it leaving focus on the trigger; touch toggle; `aria-describedby` wiring (the tooltip pattern, no `aria-expanded`); no duplicate screen-reader announcement (one tip node, no `aria-live`, the button name does not repeat the tip text); the viewport clamp has literal-number tests; Vitest floors 95/90/95/95 hold. Enter and Space activation is user-agent behaviour that jsdom does not simulate (`user-event` is not a dependency); it is observed once in the real-browser keyboard-only pass. *(Amended 2026-11-05 after review: the stub promised Tab and Enter in an executable test, which jsdom cannot honestly provide.)*

### 67D · Apply to every card and fix the formulas the tips describe (Should, ~10–14 h)

- Fix D, E and F **before or together with** the tips so no tooltip documents a wrong formula: one shared Bayesian not-started helper for list and detail; progress and ETA count failed and interrupted runs as finished work (or the tip states the real rule); Bayesian cards reconcile with Discarded shown separately.
- Apply `FormulaLine` / `InfoTip` to every row of the inventory table: Detail stat cards, Sweep Dimensions chips, Explorer ("N of M planned have results"; Bayesian M = `planned_runs`), list screen (including "120 experiments" and pagination), VectorDb and footprint ("est." plus the estimate formula and a scope label), Compare and Walkthru (score normalisation, lone-run = 100, rank, dedup note, percentage baselines).
- One glossary surfaced in the UI.

**Oracle (GWT):** on grid, Bayesian, failed, partial and empty-padding fixtures, the Detail header, the Total tile and the Explorer planned total agree; no count is computed as JSX arithmetic (lint or grep guard); every inventory row is explained or marked self-explanatory.

---

## Execution log and amendments (2026-11-05)

Recorded after execution began, so the plan matches what was built and decided. Authoritative per-branch state lives in git; this section explains the deviations from the stub above.

### Standing rules added during execution

- **Determinism rule** (see Context): every number and explanation sentence comes from a named pure function; the clock is an injected argument, never read inside; screens render values and never compute counts in JSX. Enforced by `frontend/src/utils/deterministicNumbers.guard.test.ts` (fails on `Date`/`Math.random`/storage/network/DOM in the listed pure modules, and on `.length *` in the two screens). Known limits, accepted: the guard cannot catch every way to multiply counts (`const n = a.length; n * m`) or impurity reached through an import; its module lists are hand-kept and each sub-slice must extend them.
- **Bundling:** 67D-1, 67D-2 and 67D-3 ship in **one** 67D PR (owner decision). 67A, 67B and 67C stay separate PRs (67B changes the API shape and needs its own data-flow review).
- **Parallel execution:** 67B, 67C, 67D-1, 67D-2 and 67D-3 were built in parallel in isolated git worktrees off `main` (branches `slice/67b-sweep-plan`, `slice/67c-infotip`, `slice/67d1-bayesian-not-started`, `slice/67d2-progress-eta`, `slice/67d3-compare-stats-labels`) with disjoint file ownership; 67A is `slice/67a-explainable-headline`. Remaining 67D work (screen wiring, fix F, tips on every card, glossary) waits for 67A, 67B and 67C to land because it edits `ExperimentDetailScreen.tsx`.

### 67A — implemented, with these changes to the stub

- `frontend/src/utils/sweepFormula.ts` (new, pure): `pluralize`, `formulaProduct`, `sweepFormulaFromSummary`, `sweepNote`, `BAYESIAN_SWEEP_NOTE`. Mirrors `expand_sweep`: `paddings []` counts as 1, no retrievers counts as one dense retriever, and an empty `retrievers` list falls back to the legacy `retrieval_methods`.
- `frontend/src/components/chrome/FormulaLine.tsx` (new): derived total is always the product of the terms. The stub's `total` prop became **`observedTotal`**: when it differs from the product the line reads `… = N configurations (observed)` instead of a false `=`. The Explorer passes it until 67D removes the prop. (`SweepFormula` no longer carries a `total`, so there is a single derivation.)
- Detail header uses `FormulaLine` plus a fixed Bayesian note: *"Bayesian: varies chunk size × overlap only; uses the first model, method, padding and retriever. The grid above is not run in full."* (the last sentence was added in review so the grid product is not read as a run count).
- Oracle clauses 1 and 4 amended (see Sub-slices); the Total-tile equality is asserted for grid sweeps (`Total = run_count`) in the Detail test.
- Out-of-scope fix riding on the branch as its own commit: `tests/server/db/redis/test_preflight.py` built a parametrize list from a set, so pytest-xdist workers collected different tests and the quality gates failed before running any test. Fixed with `sorted(...)`; safe to split out of the 67A PR.
- Verification so far: full `quality-gates.sh` green; real-browser check on a real 1×5×3×2×1×4 sweep (header = `120 configurations` = Total tile, no sideways overflow at 1280 px and 390 px); two independent reviews, acceptance reviewer APPROVED, code-quality re-review pending.
- Open suggestions taken into the 67D backlog: a test that the Explorer renders the `(observed)` line; widen the guard's impurity patterns and derive its module lists from a glob.

### 67B — implemented on branch `slice/67b-sweep-plan`, four reviews approved

- `server/models/config.py`: pure `sweep_plan(config)` returning a `SweepPlan` TypedDict (`dimension_counts` in fixed key order, `full_grid_count`, `searchable_space` for Bayesian, `planned_runs`, `search_strategy`, `warnings` from fixed templates with sorted numbers). It multiplies counts and never builds the grid. `resolve_bayesian_n_trials` and `grid_equivalent_count` moved here with unchanged semantics; the orchestrator keeps the `_resolve_bayesian_n_trials` re-export that `test_bayesian_finalise.py` imports. `grid_equivalent_count` (the Bayesian sampler's control variable) is untouched.
- `server/api/experiments_lifecycle.py`: `attach_sweep_plan(doc)` decorates the detail response in place on read, from `doc["config"]`, so old experiments need no backfill. Added after review: the whole computation sits inside one `except Exception`, a failure leaves the document untouched and logs once per experiment id, and validator warnings are suppressed on the read path. The list endpoint does not attach a plan.
- Types mirrored (optional) in `frontend/src/types/index.ts` and `experimentDetail/types.ts`.
- Verification: full `quality-gates.sh` green (1293 backend tests, coverage 76.10%, floors hold); mutation checks (dropping the models or chunking-methods factor fails 241 of 306 tests; removing the attach call fails the endpoint test). Reviews: data flow, system design, acceptance coverage and code quality all APPROVED after one round of changes.
- Deferred follow-ups (reviewed and accepted): route `create_experiment`'s three `expand_sweep` calls and `_planned_run_count` through `sweep_plan` (one planned-run owner); a lenient counts path for configs that fail validation; share the overlap/padding predicates between the validators and the plan warnings; move the once-per-process log suppression onto `log_throttle`; scope `catch_warnings`; a generated property test; attach the plan on the list endpoint if 67D needs it.
- Operational note: the log wording for the Bayesian cap changed ("capping" instead of "capping at grid-equivalent"); anything searching logs for the old text stops matching.

### 67C — implemented on branch `slice/67c-infotip`, reviewed

- `components/chrome/InfoTip.tsx` (new): native button with `aria-describedby` to a `role="tooltip"` span kept in the DOM and toggled with `hidden` (announced once, no `aria-live`, no `aria-expanded`); tap toggles; Escape closes and keeps focus; an outside press, a resize or an orientation change also closes it; `min-h-11 min-w-11` target; the id is a caller `id` or React `useId`.
- `components/chrome/infoTipUtils.ts` (new, pure, in the determinism guard's module list): `clampShift(rect, viewportWidth)` and the `aboutLabel` / `explainLabel` sentence templates shared by the three consumers and their tests.
- `StatTile.hint` renders through `InfoTip`; `StatTile`, `StatCard` and `CollapsibleCard` gained an `explain` prop. **UX change (owner to confirm):** hints that were always-visible text (for example the data / index sizes and quota captions on the database stats panel) are now hidden until tapped. The compact `StatCard` label stays a direct text child so the Detail screen's Total lookup keeps working.
- Verification: full `quality-gates.sh` green (500 frontend tests, coverage 97.4 / 93.01 / 98.44 / 98.59 against 95/90/95/95); real browser at 390 px (tip stays inside the screen at the left and right edges, no sideways overflow) and 1280 px (no overflow, the tip adds no card height, `CollapsibleCard` header toggle 882 × 44 beside a 44 × 44 button), plus a keyboard-only pass (Tab, Enter, Space, Escape, focus stays on the trigger). The browser pass used temporary `explain` props that were reverted, since no screen uses them yet (67D).
- Reviews: code quality and acceptance coverage, two rounds; every requested change made.
- Deferred: when both `hint` and `explain` are set a tile shows two 44 px buttons (owner decision in 67D: one tip carrying both sentences); a duplicate-id guard for caller-supplied ids.


### 67D — first bundle implemented on branch `slice/67d-explainable-cards` (D-1, D-2, D-3, Detail wiring, finding F)

Built so far (one PR by owner decision). Tips and formula lines on every inventory row, the glossary and the Explorer planned total are still open (see backlog).

- **D-1 (finding D):** pure `bayesianNotStartedCount(planned, attempted, discarded)` in `utils/experimentStatus.ts`; the list screen and the Detail screen both use it (the backend `bayesian_summary.not_started` is already reduced, so subtracting again hid the count).
- **D-2 (finding E):** failed and interrupted runs count as finished work for the progress ring and the ETA (`calculateProgressPercent`, `countFinishedRuns`, `progressSentence` in `experimentDetailProgress.ts`; clamps keep the ring at most 100% and remaining runs at least 0). The clock is an injected `now` prop; `ProgressSubtitle` renders the fixed `FINISHED_RUN_RULE` text while a failed or interrupted run exists (running sweeps only; the ETA averages over finished runs, including fast failures).
- **D-3 (finding G, plain-text labels):** `walkthru/scoreLabels.ts` and `stats/estimateLabels.ts`. A lone-run group shows "Only run in this group" (group size comes from the unfiltered groups, so a store filter cannot cause a false claim), the score note says max-not-average, a dedup note states the rule, the stats panel and footprint show "est." with the formula (average dimensions) and a scope label, and the Walkthru improvement panel states its baseline. A Python contract test fails if the formula's 4 and 500 byte constants diverge from `stats_common.py`.
- **Finding F and one denominator:** `detailDenominator()` is the single source for every Bayesian "how many" on the Detail screen (Total tile, ring percent, subtitle, totals line, "Planned Bayesian Trials", the `N/grid trials` header and every arm of the sweep-overview sentence); grid sweeps keep `run_count`. A real divergence was found and fixed: the Total tile read `run_count` while the totals line read `planned_trials`. `bayesianTotalsLine` prints "Total 20 = 13 attempted + 4 discarded + 3 not started" and says so when the parts disagree or when the loaded run rows differ from the backend's attempted count.
- **Determinism guard widened:** the regexes live in `utils/deterministicNumbers.patterns.ts` with a positive-control test, `new Date` tokens are counted per pure module against a per-file allowance (one, in `parseSafeTimestamp`), and the new pure modules and `ProgressSubtitle` are on the lists. Selection and tie counts moved to `selectableExperimentIds` and `components/explore/scoreCounts.ts`.
- Verification: full `quality-gates.sh` green (1295 backend, 570 frontend tests, `npm audit` 0). Real browser (own dev server, API stubbed for the Bayesian fixtures, real data for the rest): a Bayesian partial fixture (run_count 25, planned_trials 20) shows 20 everywhere; a running Bayesian fixture (12 / 10) shows ring 40% and "4 of 10 runs finished" with the rule readable at 390 px; the Compare store filter keeps numeric scores; a real grid sweep still shows `120 configurations` equal to the Total tile; no sideways overflow at 1280 px or 390 px.
- Reviews: code quality and acceptance coverage, three rounds each. The last acceptance blocker (the sweep-overview sentence still used `run_count`) was fixed with per-arm mutation proof but not re-reviewed by the acceptance reviewer.
- Known and accepted: the list screen's "N runs configured" and the run-count cell still print `run_count` for Bayesian rows (at creation it equals the capped planned trial count, and changing the label would break existing assertions); `formatDuration` prints a NaN-derived string for an invalid timestamp (unchanged, out of scope).

### Added scope (owner request, not yet built)

- **Query Results breakdown by golden-dataset record.** The "Query Results" tile (`total_results`, a 6–7 digit number) must show how it decomposes. Each stored result row is one retrieved chunk for one (run, golden query) pair, so the target line is `N results = R runs × Q golden records × K results each` per experiment, and `N / Q` results per golden record at the group level. Needs: group totals to carry the golden-record count (`unique_queries` exists per experiment in `ExperimentDbStats` but not in `VectorDbGroupTotals` or the grouped summaries), computed in `stats_common.py`/the store stats helpers and rendered through `FormulaLine`. The product will not always equal the stored count (failed runs, differing `top_k_final`), so any non-matching case renders `(observed)` rather than a false `=`. Lands in 67D after 67B.

### 67F — `duplicates_collapsed` in the compare response (branch `slice/67f-duplicates-collapsed`)

- `server/core/compare.py`: pure `count_duplicates_collapsed(slot_keys)` (total `(store, group_id)` keys minus distinct keys); `build_compare` adds `duplicates_collapsed` to the response, counted over all eligible candidates before `_latest_per_store_and_group` keeps one run per slot. Runs dropped for other reasons (no results, no score, unfinished) are not duplicates and are not counted.
- `CompareResponse` gained an optional `duplicates_collapsed?: number` (type only; `dedupNote(collapsed)` in `scoreLabels.ts` already accepts it, so wiring the UI is a follow-up).
- Tests: table-driven cases (empty, one, all distinct, one pair, many in one slot, two slots duplicated) plus two `build_compare` cases and the endpoint response.

### Added to the 67D backlog (from review)

- Backend `duplicates_collapsed` in the compare response; remove the Explorer's `observedTotal` once 67B supplies the planned total.
- Apply `FormulaLine`/`InfoTip` to every inventory row, replace the explanatory native `title=` uses in the screens and `ExplorePanels`, add the glossary.
- Extend the determinism guard's module lists as each helper lands; add an Explorer test for the `(observed)` line; browser-check `InfoTip` at 390 px.

## Before-Checks [GATE]

- [ ] Read `docs/plan/slices/PROGRESS.md`, `docs/plan/invariants.md`, `docs/plan/DECISION-OWNERSHIP.md`
- [ ] New branch off `main` per sub-slice (never `main`); `bash scripts/ci/install-git-hooks.sh`
- [ ] `./scripts/ci/quality-gates.sh` green before the first edit
- [ ] Baseline observed (see Output contract)
- [ ] Harness: run harness-scout `detect_confirm` against the TRAIL embed (or honour the degradation note)

## After-Checks [GATE]

- [ ] All GWT oracles above pass; Specification coverage: every GWT clause has ≥ 1 test
- [ ] Coverage: backend floors 72/59/n/a/72 hold; frontend 95/90/95/95 hold (`check_coverage_threshold_drift.py` clean)
- [ ] Complexity evidence: policy `enforcing` (xenon `--max-absolute E --max-modules C --max-average C server/ cli/` as wired in `quality-gates.sh`); local report `scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`; no new violations
- [ ] Real-browser check at 1280 px and 390 px (`/browser-ui-qa`) on a real 1×5×3×2×1×4 sweep (DECISIONS #300: a UI slice closes with a browser smoke test)
- [ ] Docs: `dashboard-guide.md`, `CLAUDE.md` Key Files if files are added, `GROWTH.md` Delta, `CHANGELOG.md`

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data flow review (67B: response shape and read-time computation)
- [ ] `nw-documentarist-reviewer` — docs currency where docs change
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Doc Audit

README (unchanged unless UI described), `docs/user-guide/dashboard-guide.md` (example and glossary), `docs/contributor-guide/module-theme-map.md` if files move, `docs/plan/GROWTH.md` Delta entry.

## Gate Status

🔨 IN PROGRESS — see *Execution log and amendments*. Gate evidence (`docs/plan/gate-evidence/slice-67.json`) is written by the executor, never pre-created.

---

## Appendix — number inventory (completed in 67A; `FormulaLine` shipped in 67A, tips land in 67C/67D)

| Screen | Card or number | Source | Verdict | Fix lands in |
|---|---|---|---|---|
| Detail | Sweep Dimensions header (was "N combinations") | `ExperimentDetailScreen.tsx` | ✅ fixed in 67A: `FormulaLine`, retrievers included, `paddings.length \|\| 1`, Bayesian note | 67A |
| Detail | Total / Successful / Failed / Interrupted / Not started / In progress | `utils/experimentStatus.ts` | ✅ grid, ❌ Bayesian sums | 67D |
| Detail | Duration, progress %, ETA | `experimentDetailProgress.ts` | ⚠️ ignores failed and interrupted | 67D |
| Detail | Bayesian summary "X/Y trials" | `ExperimentDetailScreen.tsx:624` | ⚠️ `run_count` over `grid_equivalent_count` | 67D |
| List | "N experiments" header (e.g. "120 experiments" = stored experiments, not runs), pagination ("Showing X–Y of N", page size), "N runs configured", RUNS, "N failed", Bayesian counts | `ExperimentsScreen.tsx:381,520,563` | ⚠️ planned vs executed, double subtraction | 67D |
| Explorer | "(N total configurations)" and the Cartesian line | `ExplorePanels.tsx` | ⚠️ now rendered by shared `FormulaLine` (67A); still observed from completed configs, not planned | 67D |
| Explorer | tied count, score %, per-query counts, `top_k` | `ExplorePanels.tsx` | ⚠️ two definitions, unexplained normalisation | 67D |
| Stats | Experiments, Query Results, DB Used, Chunks (Est.), MB | `VectorDbStatsPanel.tsx`, `ExperimentStoredFootprint.tsx` | ⚠️ scope and estimate unlabeled | 67D |
| Compare | Similarity score, Rank, overlap note, dedup | `CrossStoreLeaderboard.tsx` | ⚠️ lone run = 100, silent dedup | 67D |
| Walkthru | Improvement percentages, "across N runs" | `ImprovementPanel.tsx` | ⚠️ baseline unstated, primary store only | 67D |
| Detail | Sweep Dimensions chips (models, methods, sizes, overlaps, paddings, retrievers) | `ExperimentDetailScreen.tsx` `DimensionBadge` | ✅ values listed; counts now in the formula line | 67A |
