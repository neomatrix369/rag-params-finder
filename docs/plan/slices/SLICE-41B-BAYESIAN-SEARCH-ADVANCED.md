# Slice 41B — Bayesian Search: Numeric Improvements

**Status**: 📋 PLANNED

**MoSCoW**: Could

**Branch**: `slice/41b-bayesian-search-advanced` (not yet created)

**Depends on**: 41A ✅

**Target time**: ~2–3 h

**Successor**: 41C — Bayesian Search: Extended (study persistence, categorical axes, random search, dashboard card)

---

## Goal

Extend the 41A Bayesian baseline with numeric improvements that are fully unlocked:
run-level parallelism via constant liar, `padding` as a third search dimension, a correct
`n_trials` resolution formula, 3-condition stopping logic, and a fix for the 41A embedding-parallelism gap.
No open questions block any of these — A3 is already DECIDED.

---

## Scope

### 1. `bayesian.parallelism` field + constant liar run-level parallelism

Add `parallelism: int = Field(default=1, ge=1, le=4)` to `BayesianConfig`.

Implement `_run_bayesian_inner_v2()` using Optuna's ask-and-tell API with a sliding window of workers:

```python
def _run_bayesian_inner_v2(experiment_id: str, config: ExperimentConfig) -> dict:
    n_workers = config.execution.bayesian.parallelism  # capped at 4 by validator
    n_startup = _resolve_n_startup(n_trials, config)
    sampler = TPESampler(n_startup_trials=n_startup)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    trials_asked: dict[Future, optuna.Trial] = {}
    visited: set[tuple] = set()
    optuna_calls = 0
    max_optuna_calls = n_trials * 3  # safety ceiling

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        # seed initial workers
        for _ in range(min(n_workers, remaining)):
            trial = study.ask(); optuna_calls += 1
            params = _bayesian_trial_to_run_params(trial, config)
            key = _dedup_key(params)
            if key in visited:
                study.tell(trial, values=None, state=TrialState.PRUNED); continue
            visited.add(key); remaining -= 1
            future = executor.submit(_run_and_score, experiment_id, run_id, params,
                                     config.execution.parallelism)
            trials_asked[future] = trial

        while trials_asked:
            done, _ = wait(trials_asked.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                trial = trials_asked.pop(future)
                try:
                    study.tell(trial, future.result())
                except Exception:
                    study.tell(trial, float("nan"), state=TrialState.FAIL)

            # refill sliding window
            while (remaining > 0 and len(trials_asked) < n_workers
                   and optuna_calls < max_optuna_calls):
                check_control(experiment_id)
                trial = study.ask(); optuna_calls += 1
                params = _bayesian_trial_to_run_params(trial, config)
                key = _dedup_key(params)
                if key in visited:
                    study.tell(trial, values=None, state=TrialState.PRUNED); continue
                visited.add(key); remaining -= 1
                future = executor.submit(_run_and_score, experiment_id, run_id, params,
                                         config.execution.parallelism)
                trials_asked[future] = trial
```

`_run_and_score()` wraps `_run_single()` + `_compute_trial_score()` so futures return the score directly.

**Decided (A3):** `bayesian.parallelism` is a separate field — it does not conflict with `execution.parallelism` (embedding threads per run). Hard cap at 4; beyond that, constant liar degradation approaches random-search quality.

### 2. `padding` as third numeric dimension

Extend `_bayesian_trial_to_run_params()`:

```python
paddings = config.chunking.params.paddings or [0]
if len(paddings) > 1:
    padding = trial.suggest_categorical("padding", paddings)
else:
    padding = paddings[0]
```

Update `_dedup_key()` to `(chunk_size, overlap, padding)`.

Update `_compute_grid_equivalent()` to `* max(len(paddings), 1)`.

### 3. `n_trials` resolution formula

```python
def _compute_grid_equivalent(config: ExperimentConfig) -> int:
    return (
        len(config.chunking.params.chunk_sizes)
        * len(config.chunking.params.overlaps)
        * max(len(config.chunking.params.paddings or [0]), 1)
    )

def _resolve_n_trials(config: ExperimentConfig) -> int:
    grid_eq = _compute_grid_equivalent(config)
    n = config.execution.bayesian.n_trials
    if n is None:
        return grid_eq
    if n > grid_eq:
        logger.warning("bayesian n_trials=%s exceeds unique space %s — capping", n, grid_eq)
        return grid_eq
    return n

def _resolve_n_startup(n_trials: int, config: ExperimentConfig) -> int:
    if config.execution.bayesian.n_startup_trials is not None:
        return config.execution.bayesian.n_startup_trials
    return max(5, n_trials // 3)
```

Warn when `n_trials < n_startup * 2` — surrogate won't engage meaningfully.

### 4. 3-condition stopping loop

```python
while (
    trials_completed < n_trials
    and len(visited) < grid_equivalent
    and optuna_calls < max_optuna_calls   # safety ceiling = n_trials * 3
):
```

When Optuna proposes a duplicate, use `TrialState.PRUNED` (not `TrialState.FAIL`) — FAIL poisons the region; PRUNED signals "already visited" without penalty.

### 5. 41A gap fix — embedding parallelism passed to `_run_single()`

Verify (and fix if needed) that `_run_bayesian_inner()` calls `_run_single()` with four arguments:

```python
_run_single(experiment_id, run_id, params, config.execution.parallelism)
```

Without the 4th arg, all Bayesian trials use single-threaded embedding regardless of `parallelism` config.

---

## Permanently Out of Scope for This Slice

Moved to Slice 41C:

- Study persistence (`bayesian.storage` — SQLite / MongoDB backend)
- Categorical axes (`embedding_model`, `chunking_method`, retriever via `suggest_categorical`)
- Random search (`search_strategy: random`, `n_samples`)
- Dashboard Bayesian card in `ExperimentDetailScreen`
- Default promotion evaluation (owner-set N sweeps)

Permanently eliminated (see 41B original spec):

- `optuna-dashboard` as third process
- Multi-objective optimisation (NSGA-II)
- Hyperband / Successive Halving
- Evolutionary / Genetic search

---

## Spec (GWT)

```
Scenario: Single-worker Bayesian unchanged
  Given bayesian.parallelism is unset (defaults to 1)
  When a Bayesian sweep runs
  Then behaviour is identical to 41A sequential baseline

Scenario: Multi-worker constant liar
  Given bayesian.parallelism: 2
  When a Bayesian sweep runs
  Then 2 trials execute concurrently; each completes and feeds score back to study

Scenario: parallelism cap enforced
  Given bayesian.parallelism: 5
  When the config is validated
  Then a validation error is raised (le=4)

Scenario: padding swept as third dimension
  Given chunking.params.paddings: [0, 16, 32]
  When a Bayesian sweep runs
  Then trials vary chunk_size, overlap, AND padding; dedup key includes padding

Scenario: n_trials capped at grid equivalent
  Given n_trials: 500 with only 12 unique combinations
  When _resolve_n_trials() is called
  Then 12 is returned and a warning is logged

Scenario: safety ceiling prevents infinite loop
  Given a degenerate search space where Optuna repeatedly proposes duplicates
  When optuna_calls reaches n_trials * 3
  Then the loop exits without hanging

Scenario: 41A gap fix — embedding parallelism propagated
  Given execution.parallelism: 4 and search_strategy: bayesian
  When a trial runs
  Then _run_single() receives 4 as embedding_parallelism (4th arg)
```

---

## Files Expected

- `server/core/orchestrator.py` — `_run_bayesian_inner_v2`, `_run_and_score`, `_resolve_n_trials`, `_resolve_n_startup`, `_compute_grid_equivalent`, `_dedup_key`
- `server/models/config.py` — `BayesianConfig.parallelism` field; `n_startup_trials` field
- `tests/test_bayesian_search.py` — new scenarios for parallelism, padding, n_trials, stopping conditions, 41A gap fix

---

## Before-Checks [GATE]

- [ ] Branch `slice/41b-bayesian-search-advanced` from latest `main`
- [ ] Slice 41A confirmed ✅ merged to main
- [ ] A3 DECIDED: `bayesian.parallelism` separate field, capped at 4 (no further debate)
- [ ] `./scripts/quality-gates.sh --quick` green on baseline
- [ ] `optuna>=3.6` confirmed in environment (ask-and-tell API stable)

---

## TDD Execution

1. RED — write failing tests for: `_resolve_n_trials`, `_dedup_key` with padding, `BayesianConfig.parallelism` validator, 41A gap (4-arg `_run_single` call), stopping conditions
2. GREEN — implement `_run_bayesian_inner_v2` and supporting functions; fix 41A gap
3. REFACTOR — no duplicate connection logic; extract `_run_and_score` cleanly
4. VERIFY — full suite + one manual local Bayesian sweep with `parallelism: 2`

---

## After-Checks [GATE]

- [ ] `bayesian.parallelism: 5` raises `ValidationError`
- [ ] `bayesian.parallelism: 2` produces concurrent trial submissions (verified via test or log)
- [ ] `padding` appears in `dedup_key`; `grid_equivalent` multiplied by `len(paddings)`
- [ ] `n_trials > grid_equivalent` capped with warning logged
- [ ] `optuna_calls >= max_optuna_calls` exits loop (safety ceiling test)
- [ ] `_run_single()` receives 4 args in Bayesian path (grep or test assertion)
- [ ] All 41A tests still pass unchanged
- [ ] `./scripts/quality-gates.sh` passes
- [ ] PROGRESS.md updated (status + decision log entry)

## Gate Status

📋 PLANNED
