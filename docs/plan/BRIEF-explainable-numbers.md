# Brief — Correct and explainable dashboard numbers

> Saved 2026-11-05 from the owner request and the reviewed plan (nw-solution-architect-reviewer and nw-product-owner-reviewer, both approve with changes; all amendments applied). Input to [SLICE-67](slices/02-dashboard/SLICE-67-EXPLAINABLE-NUMBERS.md).
>
> Owner request: analyse every number printed in the UI (e.g. "120 experiments", "30 combinations") for correctness and for clarity on how it is derived; show aggregates like the Cartesian product line in all Sweep dimensions cards, and make every other card explainable via an info hover icon or a formula line.

## Context
The user wants every number in the UI ("120 experiments", "30 combinations", "98 configurations" …) audited for
correctness, and each one to show *how* it is derived, like the Search Explorer line
`1 model × 5 chunking methods × 3 sizes × 2 overlaps × 1 padding × 4 retrievers = 98 configurations`
(formula line, or an (i) hover/tap icon where space is tight). Sweep Dimensions cards should all carry such aggregates.

Four read-only audits + two nw reviews (solution-architect-reviewer, product-owner-reviewer: both "approve with changes").
This version folds in their amendments.

## Findings (code-verified unless noted)
- **A (confirmed):** Detail Sweep Dimensions header "N combinations" (`ExperimentDetailScreen.tsx:575-583`) omits retrievers;
  `paddings: []` gives 0 (backend treats `[]` as `[0]`). Disagrees with the Total tile.
- **B (confirmed):** Explorer Cartesian string (`ExplorePanels.tsx:255-262, 374`) derives factors from *completed* `ranked_configs`;
  retrievers counted by type only; "=" is often false.
- **C:** `grid_equivalent_count` has two meanings (full grid at creation `experiments.py:216`; `sizes × overlaps` after Bayesian finalize
  `orchestrator.py:379,469`). **Do NOT unify by redefining it**: it is the Bayesian sampler's control variable
  (stop condition `orchestrator.py:244`, cap/default `:530-545`, `max_optuna_calls` `:167`) and `test_bayesian_finalise.py:89,95,151` assert 6.
- **D:** List double-subtracts Bayesian "not started" (`experimentList/labels.ts:54-76`) vs Detail formula.
- **E:** Progress ring/ETA ignore failed+interrupted runs. **F:** Bayesian Total ≠ Successful+Failed+Interrupted+Not Started.
- Compare/Explorer: lone-run group scores 100.0; silent dedup; "Similarity score" label hides max-not-avg; tied-count mismatch;
  VectorDb "Experiments"/"Query Results" tiles differ per backend (Redis = 0); MB estimate unlabeled.
- No tooltip component exists (only native `title=`); `StatTile` has `hint`, `StatCard` has none.
- Vocabulary drift: run / configured / planned / combination / configuration / trial / experiment.

## Slices (each shippable alone; new branch off main, e.g. `feat/explainable-numbers`; not the current fix branch)

### Slice 0: Skateboard — fix the headline number + the audit deliverable (hours, own PR)
- Fix Detail header: include retrievers (`sweep_summary.retrievers ?? retrieval_methods`), `paddings.length || 1`,
  render as the Cartesian text the user quoted ("… = N configurations", sentence-case "configurations", not "combinations").
  Bayesian: formula says "varies chunk size × overlap only; uses the first model, method, padding, retriever".
- Extract the Explorer inline formula (`ExplorePanels.tsx:374`) into a shared `FormulaLine` (props `{terms:[{count,label}], total, unit}`,
  one pluralizer) and use it in both places. Pure frontend, reads existing fields.
- Deliver the **number inventory table** (screen → card → number → code source → formula → correct/ambiguous → explanation added)
  into the slice spec; it is the checklist proving "all cards" is covered. Seed it from the audit (list incl. "120 experiments" and pagination counts,
  detail cards, Bayesian card, Explorer incl. per-query counts/top_k/score precision, VectorDb/footprint, Compare, Walkthru percentages
  and baselines, duration/ETA units).

### Slice 1: Backend single source of truth (no behaviour change for Bayesian)
- In `server/models/config.py` beside `expand_sweep` add pure `sweep_plan(config)` plus the shared
  `resolve_bayesian_n_trials` / grid helpers (move them here; both `experiments_lifecycle.py` and `orchestrator.py` import from config.py to
  avoid a heavy/circular import; keep `_resolve_bayesian_n_trials` re-exported from orchestrator because
  `tests/server/core/pipeline/test_bayesian_finalise.py:18` imports it).
- `sweep_plan` returns: `dimension_counts {models, chunking_methods, chunk_sizes, overlaps, paddings, retrievers}`,
  `full_grid_count` (= `len(expand_sweep)`), `searchable_space` (= sizes × overlaps; Bayesian only), `planned_runs`, `search_strategy`,
  `warnings` (overlap ≥ size, padding > size counts). **Leave `grid_equivalent_count` untouched**; document it as "Bayesian search space".
- **Compute on read from `doc["config"]`** (every doc stores `config.model_dump()`); no persisted backfill, so old stored experiments work and nothing
  can drift. Add optional `retrievers` labels to `sweep_summary` (`experiments.py:226`) so rerankers stay distinct.
  Cover all call sites: `experiments.py:181/216/248/473/478`, `experiments_lifecycle.py:28`, `orchestrator.py:440`; `sweep.py:185` (different
  `sweep_summary`) keeps new fields optional. Mirror types in `frontend/src/types/index.ts` and `experimentDetail/types.ts`.
- Frontend fallback for docs without the new fields (current derivation, with the Slice 0 fixes).
- Tests: `total_configurations == len(expand_sweep(cfg))` (property test: empty paddings, duplicate retrievers); Bayesian stop condition when
  `n_trials` > sizes × overlaps; old-doc read path; contract tests unaffected (optional fields).

### Slice 2: Reusable explain UI
- `components/chrome/InfoTip.tsx`: dependency-free, button + `aria-describedby`, Escape closes, ≥44px target, tap-to-toggle at 390px.
  The single tooltip primitive: `StatTile.hint` renders through it; replace explanatory native `title=` uses.
- `explain` prop on `StatTile`, `StatCard`, `CollapsibleCard.headerExtra`. Tests to the 95/90/95/95 floor.

### Slice 3: Apply to every card + fix the formulas the tips would describe
- Fix D/E/F **before or together with** the tips so no tooltip documents a wrong formula: one shared helper for Bayesian
  not-started used by list + detail; progress/ETA count failed+interrupted as finished work (or the tip states the real rule);
  Bayesian cards reconcile (Discarded shown separately: "sampler rejected duplicates; not a run").
- Detail: Sweep Dimensions header + per-chip counts from `dimension_counts`; Total/Successful/Failed/Interrupted/Not started/In progress/
  Duration/progress %/ETA each with an explanation. Explorer: formula from `sweep_plan` plus "N of M planned have results"
  (Bayesian M = `planned_runs`), single tied-count definition. List: "N runs configured", "120 experiments" (what is counted/excluded), pagination.
- VectorDb/footprint: "est." label + formula (chunks × dims × 4 B + 500 B/chunk), scope label (all experiments on this store vs this experiment),
  Experiments/Query Results definitions. Compare/Walkthru: Similarity score (min-max within group; lone run = 100), Rank, overlap note,
  dedup note, ImprovementPanel "primary store only", percentages state their baseline.
- Vocabulary: **run** = executed, **planned runs** = expected, **configuration** = distinct param set (sweep header), **trial** = Bayesian only.
  One glossary surfaced in the UI (not re-defined per tooltip).

### Out of scope → separate tickets
Compare pagination hiding rows, Explorer query dropdown shrinking, Redis/ES stats counts, CLI `display.py`, user-guide example
(`dashboard-guide.md:150`, add padding axis; trivial docs fix can ride with Slice 0).

## Acceptance criteria (testable)
1. Backend: `total_configurations == len(expand_sweep(cfg))` across fixtures (grid, Bayesian, empty paddings, duplicate retrievers).
2. Frontend generic test: for every `FormulaLine` fixture the product of terms equals the displayed total (grid, Bayesian, failed, partial, empty paddings).
3. Detail header == Total tile == Explorer planned total on the same fixtures; failed run still shows planned total.
4. No count computed as JSX arithmetic (lint/grep guard); every inventory-table row has an explanation or an explicit "self-explanatory" mark.
5. InfoTip keyboard (Tab/Enter/Escape) and touch tests; browser check at 1280px and 390px.

## First actions on approval (requested by the user)
1. Check `git status`; the existing uncommitted `frontend/vite.config.ts` change stays untouched and is not committed.
2. Create a new branch off `main`: `docs/explainable-numbers-plan` (never commit to main/master).
3. Run `/enhanced-flow-planner` on this plan to produce the MoSCoW-prioritised, slice-stubbed plan under `docs/plan/`
   (TRAIL.md / PROGRESS.md / SLICE stub files, per the repo's slice playbook); save this reviewed plan alongside as the input.
4. Commit docs only (Conventional Commit, no assistant attribution trailers per the user's global rule), confirm the commit succeeded.
   Implementation of Slices 0–3 starts only after a further go-ahead.

## Critical files
Backend: `server/models/config.py`, `server/api/experiments.py`, `experiments_lifecycle.py`, `server/core/pipeline/orchestrator.py`, `server/db/ports/stats_common.py`.
Frontend: `ExperimentDetailScreen.tsx`, `ExperimentsScreen.tsx`, `experimentList/labels.ts`, `explore/ExplorePanels.tsx`,
`stats/{StatTile,VectorDbStatsPanel,ExperimentStoredFootprint}.tsx`, `experiment/experimentDetail/StatCard.tsx`,
`screens/CompareScreen.tsx`, `walkthru/CrossStoreLeaderboard.tsx`, `ImprovementPanel.tsx`, `types/index.ts`.

## Verification
`uv run pytest`, `uv run ruff check .`, `uv run mypy server/ cli/`; `cd frontend && npm run lint && npm run test && npm run typecheck && npm run build`;
`./scripts/ci/quality-gates.sh`; real sweep (1×5×3×2×1×4 = 120) in browser at 1280/390 px via `/browser-ui-qa`;
update PROGRESS.md decision log, GROWTH.md, dashboard-guide.md.
