# Slice 41A — Bayesian Search: Simple Functional

**Status**: 📋 PLANNED

**MoSCoW**: Could

**Branch**: `slice/41a-bayesian-search-simple-functional`

**Depends on**: 16

**Target time**: ~2.5 h

## Problem

Grid sweep is currently the only strategy for `_run_sweep_inner` experiments, but the product needs an opt-in Bayesian alternative to reduce wasted runs while preserving existing behavior.

## Goal

Add `execution.search_strategy: bayesian` as an opt-in sweep mode that only tunes `chunk_size` and `overlap` via Optuna TPE, while running each trial through the existing `_run_single()` pipeline unchanged.

## PCTO-41A — Bayesian Search: Simple Functional

> Slice 41A · Could · ~2.5 h (revised from 4.5 h for first execution layer) · rag-params-finder
> Status: READY TO SPEC — all blocking questions resolved below
> Depends on: Slice 16 ✅ COMPLETE

## What This Delivers

`execution.search_strategy: bayesian` as an opt-in alternative to grid search.
Bayesian sweeps `chunk_size` and `overlap` only, using Optuna TPE.
Every trial runs through the existing `_run_single()` pipeline unchanged.
CLI prints a comparison summary at completion.

## Non-Negotiable Constraints

1. Grid search is untouched. `expand_sweep()` and the grid path in `_run_sweep_inner` are not modified.
2. `search_strategy` defaults to `grid`. All existing configs and tests pass without change.
3. `git clone && pip install` is sufficient. No external accounts, no Docker additions.

## Resolved Questions (all 14 blockers closed)

| # | Question | Decision |
|---|---|---|
| C1 | Step 0 prerequisite (per-trial objective) | `query_avg_score` already exists in `results_analyzer.py`. No prerequisite needed. |
| C2 | Trial objective field | Use per-query average score aggregation (`query_avg_score` path) per trial. |
| C3 | `retrieval_method` language stale? | Constraint remains `len(config.retrieval.retrievers) == 1`. |
| C4 | `BayesianConfig` nesting | Under `ExecutionConfig` as `execution.bayesian.n_trials`. |
| B1 | `padding` in v1 search space | Fixed to `0` in Bayesian runs. |
| B2 | `run_count` meaning | `run_count = n_trials`. Add `grid_equivalent_count` on experiment doc. |
| B3 | `BayesianConfig` location | `ExecutionConfig` under `execution.bayesian`. |
| B4 | `resume_experiment` behavior | HTTP 409 with reason: `"Bayesian experiments cannot be resumed (study state is in-memory only)"`. |
| B5 | `parallelism > 1` | Warn only; recommend `1` in example configs. |
| B6 | Failed trial score to Optuna | Use `study.tell(trial, float("nan"), state=TrialState.FAIL)` for failed trials. |
| D1 | Acceptance criteria and tests | Defined in this slice. |
| D2 | `n_trials` default value | Omit `execution.bayesian` or set `n_trials` to null: default at runtime to grid-equivalent count. If set, use explicit budget; if above grid-equivalent, cap at grid-equivalent with a warning. |
| D4 | `optuna` version pin | `optuna>=3.0` in `pyproject.toml`. |
| D5 | CLI summary format | See acceptance/output section below and persist summary in `bayesian_summary`. |

## Plan Review Feedback (to apply before implementation)

- This slice is currently planning-only; the branch should not include runtime changes until this acceptance checklist is satisfied.
- Add explicit handoff checks where Bayesian enters/exits existing code paths:
  - `orchestrator.run_sweep` dispatch branch for strategy selection.
  - Existing `_run_single()` invocation contract remains unchanged.
  - API endpoints for pause/resume/stop continue to use existing state transitions and run loop checks.
- Treat doc deliverables as mandatory deliverables, not optional:
  - usage and examples for enabling bayesian mode in user-facing docs.
  - config schema/docs reference update showing `search_strategy` + `bayesian.n_trials`.
  - changelog or slice trail note for activation/behavior changes.
- Add dashboard handoff behavior so Bayesian and grid experiments are visually distinguishable in list/detail output.
- Prefer minimal UI adaptation: strategy badge + conditional summary cards to avoid duplicating existing grid views.
- Explicitly defer: “considered vs executed vs discarded” indicator (sampler proposal history) is out of scope for Slice 41A, and if implemented later, it must only apply to Bayesian experiments.

## Planning Quality Lens [GATE]

| # | Principle | Status | Rationale |
|---|---|---|---|
| 1 | Simple Design: Fewest Elements | ✅ | Scoped to one user-visible behavior change: Bayesian opt-in for chunk parameters. |
| 2 | YAGNI | ✅ | No general optimization framework; only Bayesian TPE for one existing sweep axis set. |
| 3 | SLAP | ✅ | Single abstraction level: planning behavior + seam checks, with execution details deferred. |
| 4 | Walking Skeleton | ✅ | Can be delivered as a thin slice by planning + validation + API/summary behavior checks. |
| 5 | Composability | ✅ | Depends only on completed Slice 16 and existing run pipeline. |
| 6 | Rule of 3 | ✅ | No new abstraction introduced; reuses existing `expand_sweep`/`_run_single` model. |
| 7 | Specification-First | ✅ | GWT scenarios are present before execution-task details. |
| 8 | API First | ✅ | API-level behavior (`resume`/planned-count/plumbing) is called out in gates before impl details. |
| 9 | Overengineering Flag | ✅ | Requirement is explicit and bounded to Sweep strategy opt-in; no plugin/framework expansion. |
| 10 | Artifact Path Harmonization | ✅ | Slice paths and status are aligned in TRAIL + PROGRESS + DECISIONS. |

## Gate Evidence

- `docs/plan/gate-evidence/slice-41A.json`

## Acceptance criteria

- [ ] `ExperimentConfig` with `search_strategy: grid` or omitted `search_strategy` behaves exactly as today and existing tests pass unchanged.
- [ ] `ExperimentConfig` with `search_strategy: bayesian` plus multi-value `embedding.models`, `chunking.methods`, or `retrieval.retrievers` fails parsing with a `ValidationError`.
- [ ] `ExperimentConfig` with `search_strategy: bayesian` plus single fixed axes (`len(...) == 1`) and list ranges for `chunking.params.chunk_sizes` and `overlaps` passes parsing.
- [ ] Submitting a Bayesian experiment creates exactly `n_trials` run entries in `run_status`.
- [ ] `experiment_doc.run_count == config.execution.bayesian.n_trials`.
- [ ] `experiment_doc.grid_equivalent_count == len(chunk_sizes) × len(overlaps)`.
- [ ] Duplicate `(chunk_size, overlap)` suggestions are de-duplicated and marked as `TrialState.PRUNED` (or equivalent) without advancing trial-completion counters.
- [ ] Mid-sweep pause and cancel preserve current semantics (`pause` or `stop` takes effect at the next trial boundary; `_run_single()` completes or interrupts as today).
- [ ] `POST /experiments/{id}/resume` returns HTTP 409 for Bayesian experiments.
- [ ] Completion prints Bayesian comparison summary with best config/score and grid-equivalent efficiency.
- [ ] Dashboard and list/detail output adapt cleanly to both strategies:
  - Bayesian experiments show `search_strategy`, `grid_equivalent_count`, and `bayesian_summary` in context.
  - Non-Bayesian experiments preserve current output fields and layout (no Bayesian-only cards/metrics).
- [ ] Dashboard and API output shape remain backward compatible:
  - New fields are additive (`bayesian_summary`, `grid_equivalent_count`) when strategy is bayesian.
  - Non-bayesian outputs remain unchanged and do not require dashboard special-casing beyond hiding bayesian blocks.
- [ ] `optuna>=3.0` is added to dependency set without additional infra requirements.
- [ ] Usage docs include: minimal config diff required to activate Bayesian mode and an end-to-end "expected run" sample.
- [ ] `configs/example-mongodb-unified-retrievers-bayesian.yaml` and
  `configs/example-mongodb-local-bayesian.yaml` are added and documented as activation examples.
  - Unified variant derives from `example-mongodb-unified-retrievers.yaml` and uses
    `experiment_name: example-mongodb-unified-retrievers-bayesian`.
  - Local variant derives from `example-mongodb-local.yaml` and uses
    `experiment_name: example-mongodb-local-bayesian`.
  - Both files add `execution.search_strategy: bayesian` and `execution.bayesian.n_trials`,
    while constraining the Bayesian search axes as required.
- [ ] `_planned_run_count(config)` value is documented and surfaced in planned-count UX same as existing run display behavior.
- [ ] `execution.bayesian.n_trials` can be omitted and resolves to grid-equivalent default at runtime.
- [ ] Failed trial outcomes are passed to Optuna as `TrialState.FAIL` with `NaN` to preserve resume/continuation behavior and diagnostics.
- [ ] Duplicate trial candidates do not create extra `run_status` rows and are surfaced only via Optuna prune semantics.
- [ ] Follow-up scope: exposing “considered vs executed vs discarded” counts (sampler proposal history) is explicitly deferred and is not required for Slice 41A acceptance; if implemented, it must be shown only for Bayesian experiments and never for non-Bayesian runs.

## Behavioral scenarios (GWT)

```text
Scenario: Bayesian mode runs bounded trial sweeps
  Given an experiment config sets execution.search_strategy to bayesian
  And n_trials is 12
  And chunk_sizes/overlaps contain multiple values
  When the sweep starts
  Then exactly 12 trials are generated through the Bayesian loop
  And each trial uses `_run_single()` unchanged

Scenario: Bayesian mode blocks invalid multi-axis optimization
  Given an experiment config sets search_strategy to bayesian
  And embedding.models has more than one value
  When config is parsed
  Then validation fails early
  And the user is told to configure fixed single values on all non-Bayesian axes
```

## Before-Checks [GATE]

- [ ] `results_analyzer.py` already provides per-query average score logic suitable for trial objective reuse.
- [ ] Existing sweep path (`expand_sweep()` and grid run) remains untouched and covered by unchanged tests.
- [ ] `Optuna >= 3.0` can be installed in the environment with `pip install`.

## TDD Execution Protocol [GATE]

- [ ] [GATE: RED] Write/update tests for current layer first and confirm they fail on current code.
- [ ] [GATE: GREEN] Implement only enough logic to make that layer pass.
- [ ] [GATE: REFACTOR] Optional cleanup only after GREEN remains stable.

## Implementation backlog (for /nw-execute)

- Add `BayesianConfig` under `ExecutionConfig` with `n_trials: int | None = None`.
- Add `search_strategy` and `bayesian` to `ExperimentConfig.execution`.
- Add cross-field validation enforcing single fixed axes for Bayesian runs.
- Add `_run_bayesian_inner`, `_bayesian_trial_to_run_params`, `_compute_trial_score`, `_finalise_bayesian_experiment`.
- Add `_planned_run_count(config)` in API layer and use for planned-count display.
- Add `grid_equivalent_count` and `bayesian_summary` persistence on experiment docs.
- Add `configs/example-mongodb-unified-retrievers-bayesian.yaml` and
  `configs/example-mongodb-local-bayesian.yaml`, each with a non-Bayesian base config plus
  Bayesian strategy options.
  - Unified variant derives from `example-mongodb-unified-retrievers.yaml` and uses
    `experiment_name: example-mongodb-unified-retrievers-bayesian`.
  - Local variant derives from `example-mongodb-local.yaml` and uses
    `experiment_name: example-mongodb-local-bayesian`.
- Add dashboard UI updates for strategy-aware rendering in experiment summary views and run detail tables.

## Files to update

- `server/models/config.py`
- `server/core/orchestrator.py`
- `server/api/experiments.py`
- `configs/example-mongodb-unified-retrievers-bayesian.yaml`
- `configs/example-mongodb-local-bayesian.yaml`
- `frontend/src/**/*` (strategy-aware display updates)
- `docs/plan/slices/SLICE-41A-BAYESIAN-SEARCH-SIMPLE-FUNCTIONAL.md` (new)
- `pyproject.toml`

## After-Checks [GATE]

- [GATE] Layer-01 Config Validation
  - [ ] [RED] Add/verify tests for `ExperimentConfig` validation: multi-axis Bayesian rejects; fixed-axis + sweep lists pass.
  - [ ] [GREEN] Implement validation under this gate.
- [GATE] Layer-02 Dispatch Handoff
  - [ ] [RED] Add tests for `search_strategy` dispatch and grid default path.
  - [ ] [GREEN] Implement `run_sweep` strategy branch only.
- [GATE] Layer-03 Trial Handoff
  - [ ] [RED] Add tests ensuring `_run_bayesian_inner` calls `_run_single` with same contract as existing grid trials.
  - [ ] [GREEN] Implement and preserve exact per-trial `_run_single` handoff.
- [GATE] Layer-04 API and Pause/Stop Boundary
  - [ ] [RED] Add API tests for planned count display and `resume -> 409` for bayesian.
  - [ ] [GREEN] Implement planning count + endpoint boundary behavior; preserve existing pause/stop semantics.
- [GATE] Layer-05 Persistence & Completion Summary
  - [ ] [RED] Add tests for `run_count`, `grid_equivalent_count`, and bayesian summary payload in experiment doc.
  - [ ] [GREEN] Implement persistence and summary output.
- [GATE] Layer-06 Regression and Documentation
  - [ ] [RED] Confirm existing `expand_sweep`/grid tests remain unchanged and `results_analyzer` path remains compatible.
- [ ] [GREEN] Add/confirm docs gates: `docs/plan/TRAIL.md`, `docs/plan/slices/PROGRESS.md`, `DECISIONS.md`, and both
  `configs/example-mongodb-unified-retrievers-bayesian.yaml` and `configs/example-mongodb-local-bayesian.yaml` references.
- [GATE] Layer-07 Delivery Completion
  - [ ] [RED] Run one end-to-end happy-path bayesian scenario: planned-count, n_trials runs, resume-disabled, and completion summary all pass.
  - [ ] [GREEN] Verify no regressions on existing slice-critical paths (`grid` default path and `expand_sweep` semantics).
  - [ ] [RED] Add dashboard contract tests showing both bayesian and non-Bayesian output rendering behavior.
  - [ ] [GATE] Specification coverage: every GWT clause has at least one test; all essential success and failure clauses covered.
  - [ ] [GATE] Branch coverage: 100% branch target on touched functions; accepted exclusions are documented.
  - [ ] [GATE] Mutation testing: apply mutation checks when feature-complete; no high-severity survivals.

## Dashboard Adaptation Contract (authoritative)

- `frontend` list/detail output must include strategy label:
  - `search_strategy: bayesian` for Bayesian runs.
  - `search_strategy: grid` (or omitted) for existing behavior.
- Bayesian run rows show a dedicated summary region with:
  - best candidate
  - trials run / `grid_equivalent_count`
  - best-first coverage mode and source trial summary
- Non-Bayesian runs keep existing summary ordering and fields.
- API fields consumed by dashboard must keep existing JSON keys stable when non-bayesian.

## Runtime Loop Design (authoritative)

- `_resolve_n_trials(config: ExperimentConfig) -> int`:
  - `grid_equivalent = _compute_grid_equivalent(config)`
  - If `config.execution.bayesian.n_trials is None`: return `grid_equivalent`.
  - If `n_trials > grid_equivalent`: log warning and cap to `grid_equivalent`.
  - Else return provided `n_trials`.
- Bayesian loop stopping conditions are conjunctive:
  - `trials_completed < n_trials`
  - `len(visited) < grid_equivalent`
  - `optuna_calls < max_optuna_calls` where `max_optuna_calls = n_trials * 3`.
- Duplicate suggestions handling:
  - Track `visited: set[(chunk_size, overlap)]`.
  - If duplicate suggested, call `study.tell(trial, values=None, state=TrialState.PRUNED)` and continue.
  - Duplicates do not increment `trials_completed` and do not create additional `run_status` entries.

## Handoff & Boundary Tests (explicit checklist)

- [GATE] Cross-field validation: multi-axis bayesian must fail early with clear message.
- [GATE] Sweep dispatch: bayesian path only when `execution.search_strategy == "bayesian"`, default/grid unchanged.
- [GATE] Per-trial handoff: `_run_bayesian_inner` to `_run_single` argument/state contract identical to grid path.
- [GATE] Pause/stop: interrupt still observed before next trial setup; `_run_single` completion/interruption semantics unchanged.
- [GATE] Resume boundary: `POST /experiments/{id}/resume` returns 409 with bayesian-specific rationale.

## Config/Behavior Reference (PCTO source excerpt)

- `ExecutionConfig` additions:
  - `search_strategy: Literal["grid", "bayesian"] = "grid"`
  - `bayesian: BayesianConfig` with `n_trials: int | None = None` (runtime default to grid-equivalent)
- Bayesian path contract:
  - `_execute_sweep()` dispatches by `search_strategy`.
  - Bayesian mode uses deduplicated trial suggestion on (`chunk_size`, `overlap`) only.
  - Duplicate suggestions must transition to `TrialState.PRUNED` and should not count toward `n_trials`.
  - `_run_single()` is called using the existing arguments/state contract from grid path.
- CLI completion output includes:
  - Best config and score
  - Trials run vs. unique combinations
  - Grid-equivalent count and coverage mode (full or capped)
