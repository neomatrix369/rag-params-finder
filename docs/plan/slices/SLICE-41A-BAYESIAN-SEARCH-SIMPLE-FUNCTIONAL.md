# Slice 41A — Bayesian Search: Simple Functional

**Status**: 📋 PLANNED

**MoSCoW**: Could

**Branch**: `slice/41a-bayesian-search-simple-functional`

**Depends on**: 16

**Target time**: ~4.5 h

## Problem

Grid sweep is currently the only strategy for `_run_sweep_inner` experiments, but the product needs an opt-in Bayesian alternative to reduce wasted runs while preserving existing behavior.

## Goal

Add `execution.search_strategy: bayesian` as an opt-in sweep mode that only tunes `chunk_size` and `overlap` via Optuna TPE, while running each trial through the existing `_run_single()` pipeline unchanged.

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
- [ ] Mid-sweep pause and cancel preserve current semantics (`pause` or `stop` takes effect at the next trial boundary; `_run_single()` completes or interrupts as today).
- [ ] `POST /experiments/{id}/resume` returns HTTP 409 for Bayesian experiments.
- [ ] Completion prints Bayesian comparison summary with best config/score and grid-equivalent efficiency.
- [ ] `optuna>=3.0` is added to dependency set without additional infra requirements.
- [ ] Usage docs include: minimal config diff required to activate Bayesian mode and an end-to-end "expected run" sample.
- [ ] `configs/example-bayesian.yaml` is added and documented as the canonical activation example.
- [ ] A dashboard- and API-level no-regression rule is captured: old fields in `run_status` and experiment documents remain backward compatible.
- [ ] `_planned_run_count(config)` value is documented and surfaced in planned-count UX same as existing run display behavior.

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

- Add `BayesianConfig` under `ExecutionConfig` with `n_trials: int = 12`.
- Add `search_strategy` and `bayesian` to `ExperimentConfig.execution`.
- Add cross-field validation enforcing single fixed axes for Bayesian runs.
- Add `_run_bayesian_inner`, `_bayesian_trial_to_run_params`, `_compute_trial_score`, `_finalise_bayesian_experiment`.
- Add `_planned_run_count(config)` in API layer and use for planned-count display.
- Add `grid_equivalent_count` and `bayesian_summary` persistence on experiment docs.
- Add `configs/example-bayesian.yaml` with single fixed axes and sweep lists for Bayesian dimensions.
- No dashboard code changes.

## Files to update

- `server/models/config.py`
- `server/core/orchestrator.py`
- `server/api/experiments.py`
- `configs/example-bayesian.yaml`
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
  - [ ] [GREEN] Add/confirm docs gates: `docs/plan/TRAIL.md`, `docs/plan/slices/PROGRESS.md`, `DECISIONS.md`, and `configs/example-bayesian.yaml` references.
- [GATE] Layer-07 Delivery Completion
  - [ ] [RED] Run one end-to-end happy-path bayesian scenario: planned-count, n_trials runs, resume-disabled, and completion summary all pass.
  - [ ] [GREEN] Verify no regressions on existing slice-critical paths (`grid` default path and `expand_sweep` semantics).

## Handoff & Boundary Tests (explicit checklist)

- [GATE] Cross-field validation: multi-axis bayesian must fail early with clear message.
- [GATE] Sweep dispatch: bayesian path only when `execution.search_strategy == "bayesian"`, default/grid unchanged.
- [GATE] Per-trial handoff: `_run_bayesian_inner` to `_run_single` argument/state contract identical to grid path.
- [GATE] Pause/stop: interrupt still observed before next trial setup; `_run_single` completion/interruption semantics unchanged.
- [GATE] Resume boundary: `POST /experiments/{id}/resume` returns 409 with bayesian-specific rationale.
