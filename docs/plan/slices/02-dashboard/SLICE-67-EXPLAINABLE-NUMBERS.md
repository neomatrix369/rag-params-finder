# SLICE-67 — Correct and Explainable Dashboard Numbers

**Status:** 📋 PLANNED
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

- Given an experiment with 1×5×3×2×1×4 dimensions, When the Detail screen renders, Then the header reads `1 model × 5 chunking methods × 3 sizes × 2 overlaps × 1 padding × 4 retrievers = 120 configurations` and equals the Total tile.
- Given `paddings: []`, When it renders, Then the padding factor is 1, never 0.
- Given a Bayesian experiment, When it renders, Then the header carries the "varies chunk size × overlap only" note.
- For every `FormulaLine` fixture, the product of the terms equals the displayed total.

### 67B · Backend single source of truth (Must, ~6–8 h)

- In `server/models/config.py` beside `expand_sweep`: pure `sweep_plan(config)` returning `dimension_counts`, `full_grid_count` (= `len(expand_sweep)`), `searchable_space` (Bayesian only), `planned_runs`, `search_strategy`, `warnings` (overlap ≥ size, padding > size).
- Move `resolve_bayesian_n_trials` and the grid helper into `config.py`; `experiments_lifecycle.py` and `orchestrator.py` import from there (no circular or heavy import). Keep `_resolve_bayesian_n_trials` re-exported from the orchestrator (`test_bayesian_finalise.py:18` imports it).
- **Leave `grid_equivalent_count` untouched** (documented as "Bayesian search space").
- Compute `sweep_plan` on read from `doc["config"]`; add an optional `retrievers` label list to `sweep_summary`. Call sites: `experiments.py:181/216/248/473/478`, `experiments_lifecycle.py:28`, `orchestrator.py:440`; `sweep.py:185` keeps new fields optional.
- Mirror types in `frontend/src/types/index.ts` and `experimentDetail/types.ts`; the frontend falls back to the 67A derivation for responses without the new fields.

**Oracle (GWT):**

- Property test: `total_configurations == len(expand_sweep(cfg))` (empty paddings, duplicate retrievers, rerankers).
- Given `n_trials` larger than `sizes × overlaps`, the Bayesian stop condition behaves as today.
- Given an old stored experiment without the new fields, the read path returns a correct `sweep_plan`.
- Existing `test_bayesian_finalise.py` and the storage contract tests still pass untouched.

### 67C · Reusable explain UI (Should, ~4–5 h)

- `components/chrome/InfoTip.tsx`: dependency-free; button with `aria-describedby`; Escape closes; target ≥ 44 px; tap toggles at 390 px.
- `StatTile.hint` renders through `InfoTip`; `explain` prop added to `StatTile`, `StatCard` and `CollapsibleCard.headerExtra`; explanatory native `title=` uses replaced.

**Oracle (GWT):** keyboard (Tab, Enter, Escape), touch toggle, `aria-describedby` wiring, no duplicate screen-reader announcement; Vitest floors 95/90/95/95 hold.

### 67D · Apply to every card and fix the formulas the tips describe (Should, ~10–14 h)

- Fix D, E and F **before or together with** the tips so no tooltip documents a wrong formula: one shared Bayesian not-started helper for list and detail; progress and ETA count failed and interrupted runs as finished work (or the tip states the real rule); Bayesian cards reconcile with Discarded shown separately.
- Apply `FormulaLine` / `InfoTip` to every row of the inventory table: Detail stat cards, Sweep Dimensions chips, Explorer ("N of M planned have results"; Bayesian M = `planned_runs`), list screen (including "120 experiments" and pagination), VectorDb and footprint ("est." plus the estimate formula and a scope label), Compare and Walkthru (score normalisation, lone-run = 100, rank, dedup note, percentage baselines).
- One glossary surfaced in the UI.

**Oracle (GWT):** on grid, Bayesian, failed, partial and empty-padding fixtures, the Detail header, the Total tile and the Explorer planned total agree; no count is computed as JSX arithmetic (lint or grep guard); every inventory row is explained or marked self-explanatory.

---

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

📋 PLANNED — stub. Gate evidence (`docs/plan/gate-evidence/slice-67.json`) is written by the executor, never pre-created.

---

## Appendix — number inventory (completed in 67A; `FormulaLine` shipped in 67A, tips land in 67C/67D)

| Screen | Card or number | Source | Verdict | Fix lands in |
|---|---|---|---|---|
| Detail | Sweep Dimensions header (was "N combinations") | `ExperimentDetailScreen.tsx` | ✅ fixed in 67A: `FormulaLine`, retrievers included, `paddings.length \|\| 1`, Bayesian note | 67A |
| Detail | Total / Successful / Failed / Interrupted / Not started / In progress | `utils/experimentStatus.ts` | ✅ grid, ❌ Bayesian sums | 67D |
| Detail | Duration, progress %, ETA | `experimentDetailProgress.ts` | ⚠️ ignores failed and interrupted | 67D |
| Detail | Bayesian summary "X/Y trials" | `ExperimentDetailScreen.tsx:624` | ⚠️ `run_count` over `grid_equivalent_count` | 67D |
| List | "N experiments" header, "N runs configured", RUNS, "N failed", Bayesian counts | `ExperimentsScreen.tsx:381,520,563` | ⚠️ planned vs executed, double subtraction | 67D |
| Explorer | "(N total configurations)" and the Cartesian line | `ExplorePanels.tsx` | ⚠️ now rendered by shared `FormulaLine` (67A); still observed from completed configs, not planned | 67D |
| Explorer | tied count, score %, per-query counts, `top_k` | `ExplorePanels.tsx` | ⚠️ two definitions, unexplained normalisation | 67D |
| Stats | Experiments, Query Results, DB Used, Chunks (Est.), MB | `VectorDbStatsPanel.tsx`, `ExperimentStoredFootprint.tsx` | ⚠️ scope and estimate unlabeled | 67D |
| Compare | Similarity score, Rank, overlap note, dedup | `CrossStoreLeaderboard.tsx` | ⚠️ lone run = 100, silent dedup | 67D |
| Walkthru | Improvement percentages, "across N runs" | `ImprovementPanel.tsx` | ⚠️ baseline unstated, primary store only | 67D |
| List | "120 experiments" header count and pagination ("Showing X–Y of N", page size) | `ExperimentsScreen.tsx`, `chrome/Pagination.tsx` | ⚠️ total of stored experiments vs. filtered/visible rows is unlabeled | 67D |
| Detail | Sweep Dimensions chips (models, methods, sizes, overlaps, paddings, retrievers) | `ExperimentDetailScreen.tsx` `DimensionBadge` | ✅ values listed; counts now in the formula line | 67A |
