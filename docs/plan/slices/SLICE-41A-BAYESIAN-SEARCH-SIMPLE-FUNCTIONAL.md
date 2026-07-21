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

## Implementation details

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

- [ ] Specification coverage: all GWT clauses covered by tests (BDD/GWT-first) and edge clauses (parallelism > 1 warning, NaN fail trials, resume 409).
- [ ] Branch coverage target for touched functions is 100% where practical; exclusions documented.
- [ ] Test coverage checks pass for the existing slice and new/adjusted tests.
- [ ] `docs/plan/TRAIL.md` and `docs/plan/slices/PROGRESS.md` contain this slice as `📋 PLANNED`.
- [ ] `DECISIONS.md` includes planning and dependency entry for Slice 41A.
