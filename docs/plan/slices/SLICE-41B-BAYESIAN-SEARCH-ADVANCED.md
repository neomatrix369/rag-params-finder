# Slice 41B — Bayesian Search: Advanced

**Status**: 📦 PARKED — implement after 41A ships and real sweep data exists

**MoSCoW**: Could

**Branch**: `slice/41b-bayesian-search-advanced` (not yet created)

**Depends on**: 41A ✅ + production usage evidence (owner-set N sweeps, see A4)

**Target time**: ~4–6 h (estimated)

---

## Why This Is Parked

Everything in this slice is deliberately deferred from 41A. The PCTO-41B document captures a full architecture debate, codebase analysis, and parallelism deep-dive so the analysis is not lost. Nothing here blocks or delays 41A. This slice opens only after:

1. 41A is ✅ PASSED and merged to main.
2. Real production Bayesian sweep data exists (owner-set N sweeps; suggested baseline: 20 runs).
3. Open questions A1–A4 and D3, D6, D7 below are resolved.

---

## Deferred Questions (resolve before speccing this slice)

| # | Question | Current Stance | Needs Before Speccing |
|---|---|---|---|
| A1 | Study persistence backend: SQLite vs MongoDB | SQLite preferred (judge-friendly); MongoDB consistent with stack | Owner decision: demo path vs production path |
| A2 | Categorical axis TPE quality validation | `suggest_categorical()` is valid; quality vs random search on small categorical spaces is unproven | A/B comparison: Bayesian vs random search on same categorical space across ≥3 real datasets |
| A3 | Bayesian run-level parallelism field | **Decided**: use separate `bayesian.parallelism` field (see `BayesianConfig` in Scope section). Field is named, typed, and capped at 4. Remaining question: confirm the name does not confuse users who already set `execution.parallelism` — validate in user-guide examples before this slice opens. | User-guide review; no code question remains. |
| A4 | Revisit-trigger N for default promotion | "Owner to set N" — unresolved | Owner sets N before this slice opens; suggested baseline: 20 real production Bayesian sweeps. **Time-bound**: if N sweeps are not accumulated by 2026-10-01, open a product decision to either lower the threshold or mark this slice Won't for the current cycle. |
| D3 | `sweep_summary` field for Bayesian | Currently stores lists; misleading when axes are single-value | Decide whether to add `search_strategy` and `bayesian_config` keys to `sweep_summary` |
| D6 | `max_score` as primary sort key for grid | Still primary; `query_avg_score` is tiebreaker | **Not a gate for this slice** — can be resolved independently at any time. Listed here for completeness (carried from PCTO-41B); does not block opening this slice. |
| D7 | Random search `n_samples` config design | Not designed; deferred from 41A | Design alongside or before this slice |

---

## Parallelism — Full Architecture Record

This section supersedes the brief parallelism notes in 41A and the unified PCTO. It is the consolidated record from the architecture debate and codebase review sessions.

### The Two-Layer Architecture (`executors.py` + `orchestrator.py`)

**Layer 1 — Outer: `SWEEP_EXECUTOR` (one experiment at a time globally)**

```python
# server/core/executors.py
SWEEP_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rag-sweep")
```

One experiment runs at a time across the whole process. Bayesian uses this unchanged — fire-and-forget via `schedule_sweep()`, same as grid.

**Layer 2 — Inner: run concurrency + embedding threads per run**

Inside `_run_sweep_inner`, `config.execution.parallelism` does **two jobs simultaneously**:

```python
# Job 1: how many runs execute concurrently (sliding window)
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    for _ in range(max_workers):
        _submit_next()
    while futures:
        done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
        # as each run finishes → _submit_next() immediately refills that slot

# Job 2: passed INTO _run_single as embedding thread count
executor.submit(
    _run_single,
    experiment_id,
    run_id,
    params,
    config.execution.parallelism,   # ← 4th arg = embedding_parallelism
)
```

So `parallelism: 4` in grid means **4 runs in flight concurrently, each using 4 embedding threads** (up to 16 total threads). The pattern is a **sliding window**: as each run completes, `_submit_next()` immediately refills that slot.

### How Bayesian Interacts With Both Layers

| | Grid | Bayesian v1 (41A) | Bayesian v2 (this slice) |
|---|---|---|---|
| Run concurrency | `parallelism` runs in flight | Fixed at 1 — sequential by design | `bayesian.parallelism` workers (capped at 4) |
| Embedding threads per run | `parallelism` threads | `parallelism` threads — unchanged | `parallelism` threads — unchanged |
| `_run_single()` 4th arg | `config.execution.parallelism` | `config.execution.parallelism` | `config.execution.parallelism` |

**Key insight:** even with Bayesian run concurrency fixed at 1, each trial still benefits from multi-threaded local embedding by passing `config.execution.parallelism` as `embedding_parallelism` to `_run_single()`. This is a free win requiring zero extra code — `parallelism: 4` in a Bayesian config means single-run-at-a-time but 4-threaded embedding inside each trial.

### Known Gap in PCTO-41A (must be fixed before 41A ships)

The `_run_bayesian_inner()` implementation must call `_run_single()` with four arguments:

```python
# Correct — must match grid's call pattern
_run_single(experiment_id, run_id, params, config.execution.parallelism)
```

Without the fourth argument, all Bayesian trials use single-threaded embedding regardless of the `parallelism` config value. This is a bug in 41A to verify/fix before merge.

### Run-Level Parallelism for Bayesian (v2 — this slice)

Bayesian is inherently sequential at the run level — each trial's score feeds the surrogate before the next trial is proposed. However, Optuna's ask-and-tell API supports limited run-level parallelism via the **constant liar strategy**: when Worker 2 asks, the surrogate temporarily assumes in-flight trials will return the current best score (the "liar"). This preserves most surrogate quality while allowing bounded concurrency.

**Quality degradation by worker count** (empirical pattern from Optuna documentation and TPE literature; see After-Check gate for validation approach):

| Workers | Bayesian quality vs sequential | Verdict |
|---|---|---|
| 1 | 100% — full surrogate benefit | Sequential baseline |
| 2–4 | ~90–95% — practical sweet spot | ✅ Worth it |
| 8+ | Approaches random search quality | ❌ Paying Bayesian cost for random search output |

**Hard cap at 4 workers.** Beyond that, constant liar degradation means you pay Bayesian implementation complexity for random search quality. Grid and random search are embarrassingly parallel at any N — if you need more than 4 workers, use those.

### Implementation Pattern for v2 Run-Level Parallelism

```python
def _run_bayesian_inner_v2(experiment_id: str, config: ExperimentConfig) -> dict:
    n_workers = config.execution.bayesian.parallelism  # capped at 4
    n_startup = max(5, config.execution.bayesian.n_trials // 3)
    sampler = TPESampler(n_startup_trials=n_startup)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    trials_asked: dict[Future, optuna.Trial] = {}
    run_ids: list[str] = []
    remaining = config.execution.bayesian.n_trials

    visited: set[tuple] = set()
    optuna_calls = 0
    max_optuna_calls = config.execution.bayesian.n_trials * 3  # safety ceiling

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        for _ in range(min(n_workers, remaining)):
            trial = study.ask()
            optuna_calls += 1
            params = _bayesian_trial_to_run_params(trial, config)
            dedup_key = (params["chunk_size"], params["overlap"], params.get("padding", 0))
            if dedup_key in visited:
                study.tell(trial, values=None, state=TrialState.PRUNED)
                continue
            visited.add(dedup_key)
            run_id = str(uuid.uuid4())
            run_ids.append(run_id)
            remaining -= 1
            future = executor.submit(
                _run_and_score,
                experiment_id, run_id, params, config.execution.parallelism
            )
            trials_asked[future] = trial

        while trials_asked:
            done, _ = wait(trials_asked.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                trial = trials_asked.pop(future)
                try:
                    score = future.result()
                    study.tell(trial, score)
                except Exception:
                    study.tell(trial, float("nan"), state=TrialState.FAIL)

            while remaining > 0 and len(trials_asked) < n_workers and optuna_calls < max_optuna_calls:
                try:
                    check_control(experiment_id)
                except (ExperimentCancelledError, ExperimentPausedError):
                    break
                trial = study.ask()
                optuna_calls += 1
                params = _bayesian_trial_to_run_params(trial, config)
                dedup_key = (params["chunk_size"], params["overlap"], params.get("padding", 0))
                if dedup_key in visited:
                    study.tell(trial, values=None, state=TrialState.PRUNED)
                    continue  # not counted toward remaining
                visited.add(dedup_key)
                run_id = str(uuid.uuid4())
                run_ids.append(run_id)
                remaining -= 1
                future = executor.submit(
                    _run_and_score,
                    experiment_id, run_id, params, config.execution.parallelism
                )
                trials_asked[future] = trial
```

`_run_and_score()` is a thin wrapper combining `_run_single()` and `_compute_trial_score()` so the future returns the score directly.

---

## `n_trials` Design — Full Specification

### Summary

`n_trials` is **optional**. When omitted, Bayesian runs the same number of experiments as grid search (the `grid_equivalent` count). When set, it acts as a custom budget cap.

```python
class BayesianConfig(BaseModel):
    n_trials:         int | None = Field(default=None, ge=1, le=500)
    n_startup_trials: int | None = Field(default=None, ge=1)
```

Resolution at experiment start:

```python
def _compute_grid_equivalent(config: ExperimentConfig) -> int:
    return (
        len(config.chunking.params.chunk_sizes)
        * len(config.chunking.params.overlaps)
        * max(len(config.chunking.params.paddings), 1)
    )

def _resolve_n_trials(config: ExperimentConfig) -> int:
    grid_equivalent = _compute_grid_equivalent(config)
    n_trials = config.execution.bayesian.n_trials
    if n_trials is None:
        return grid_equivalent
    if n_trials > grid_equivalent:
        logger.warning(
            "bayesian n_trials=%s exceeds unique search space of %s "
            "combinations — capping at %s",
            n_trials, grid_equivalent, grid_equivalent,
        )
        return grid_equivalent
    return n_trials

def _resolve_n_startup(n_trials: int, config: ExperimentConfig) -> int:
    if config.execution.bayesian.n_startup_trials is not None:
        return config.execution.bayesian.n_startup_trials
    return max(5, n_trials // 3)
```

### Warn when n_trials is too small for the surrogate to engage

```python
if n_trials < n_startup * 2:
    logger.warning(
        "bayesian n_trials=%s is below 2× n_startup_trials=%s — the surrogate "
        "will not engage meaningfully. Increase n_trials or use grid search.",
        n_trials, n_startup,
    )
```

### Behaviour by Configuration

| `n_trials` setting | Result |
|---|---|
| Omitted (default) | Runs `grid_equivalent` unique combos in surrogate-guided order |
| `< grid_equivalent` | Budget mode — runs that many unique combos chosen by surrogate |
| `> grid_equivalent` | Warned and capped at `grid_equivalent` |

---

## Stopping Conditions and Deduplication

### The Three Stopping Conditions

```python
while (
    trials_completed < n_trials
    and len(visited) < grid_equivalent
    and optuna_calls < max_optuna_calls   # safety ceiling = n_trials * 3
):
```

| Condition | When | Meaning |
|---|---|---|
| `trials_completed >= n_trials` | Budget reached | Custom `n_trials` exhausted |
| `len(visited) >= grid_equivalent` | Space exhausted | All unique combinations run |
| `optuna_calls >= max_optuna_calls` | Safety ceiling | Guards against infinite duplicate-propose loops |

### Deduplication Pattern

Track `visited: set[tuple]`. When Optuna proposes a duplicate, use `TrialState.PRUNED` (not `TrialState.FAIL`) — `FAIL` poisons the region, `PRUNED` signals "already visited" without penalizing it:

```python
if key in visited:
    study.tell(trial, values=None, state=TrialState.PRUNED)
    continue  # not counted toward trials_completed
```

---

## Scope When This Slice Opens

### Study Persistence

Add `bayesian.storage` to `BayesianConfig`:

```python
class BayesianConfig(BaseModel):
    n_trials:         int | None = Field(default=None, ge=1, le=500)
    n_startup_trials: int | None = Field(default=None, ge=1)
    parallelism:      int = Field(default=1, ge=1, le=4)
    storage:          str | None = Field(default=None)
    # None = in-memory (41A behaviour, no resume)
    # "sqlite:///bayesian.db" = local SQLite (judge-friendly, enables resume)
    # "mongodb://..." = MongoDB backend (production path)
```

When `storage` is set, the HTTP 409 resume guard from 41A can be removed. See `SLICE-41A-BAYESIAN-SEARCH-SIMPLE-FUNCTIONAL.md` → "Resume / 409 guard" for the current implementation that this supersedes.

### Categorical Dimensions in Search Space (requires A2 validated)

Expand `_bayesian_trial_to_run_params()` to sweep `embedding_model`, `chunking_method`, and retriever type via `suggest_categorical()`. Remove the cross-field validator constraints from 41A enforcing single values on these axes.

**Prerequisite (A2):** TPE quality on categorical axes must be validated against random search across ≥3 real datasets before this ships.

Note: for categorical-inclusive search, increase startup formula:
```python
n_startup = max(10, n_trials // 3)   # vs max(5, ...) for numeric-only
```

### `padding` in Search Space

Add `padding` as a third numeric dimension:

```python
paddings = config.chunking.params.paddings or [0]
if len(paddings) > 1:
    padding = trial.suggest_categorical("padding", paddings)
else:
    padding = paddings[0]
```

Update `grid_equivalent` calculation to include paddings (already documented above).

### Random Search

> **Scope note**: random search is not a Bayesian technique. It is included here because it shares the search-space config layer and was deferred from 41A alongside Bayesian features. If the owner prefers narrower scope, random search can be split into a separate Slice 41C with minimal impact.

Add `search_strategy: random` as a third option. Random search is embarrassingly parallel — same sliding window model as grid, no surrogate, no quality penalty at any worker count:

```python
search_strategy: Literal["grid", "random", "bayesian"] = Field(default="grid")

class RandomConfig(BaseModel):
    n_samples: int = Field(default=20, ge=1)
```

`_run_random_inner()` samples `n_samples` configs from the Cartesian product without replacement and runs them via the existing `ThreadPoolExecutor` pool at full `config.execution.parallelism` concurrency.

### Dashboard Bayesian Card

Surface the CLI summary from 41A as a card in `ExperimentDetailScreen` when `search_strategy == "bayesian"`:

```
┌──────────────────────────────────────────┐
│ Search Strategy: Bayesian                │
│ Best: chunk_size=512  overlap=50         │
│ Score: 0.847                             │
│ 45 trials · surrogate active from #16   │
│ vs 90 grid equivalent (50% fewer runs)  │
└──────────────────────────────────────────┘
```

Requires `bayesian_summary` field stored by 41A — no backend change.

### Default Promotion Evaluation (post owner-N sweeps)

After N real sweeps (owner to set N per A4):

| Check | Pass condition |
|---|---|
| Config quality | Bayesian best config matches or beats grid best on same dataset |
| Trial efficiency | Bayesian converges within 50% of grid run count |
| Consistency | Holds across ≥3 different datasets |

If ≥2 of 3 pass consistently, open a product decision to promote `search_strategy: bayesian` as recommended default for spaces > 150 combinations.

---

## Permanently Out of Scope

These items are **permanently eliminated** from Bayesian consideration and should not be revisited:

- `optuna-dashboard` as a third process — violates judge-friendly constraint
- Multi-objective optimisation (NSGA-II) — belongs in a RAGAS metrics slice
- Hyperband / Successive Halving — eliminated: atomic `_run_single()` cannot be pruned mid-run
- Evolutionary / Genetic search — eliminated: marginal gain, high implementation weight

---

## Relationship to 41A

| Item | 41A (must verify before 41A ships) | 41B (this slice) |
|---|---|---|
| `embedding_parallelism` passed to `_run_single()` | **Known gap — verify 4-arg call before 41A merges** | Documents the correct pattern |
| Run-level parallelism | Warn if `parallelism > 1`; recommend `1` | Full constant liar implementation, capped at 4 workers |
| `n_trials` | Fixed at 12 in early plan; auto-derived from 41A spec | Formula fully specified here |
| `n_startup_trials` | Not mentioned in 41A | Explicit formula; scales with `n_trials` and search space type |
| Sequential vs sliding window | Sequential for-loop | Sliding window mirroring grid pattern |
| Categorical axes | Cross-field validator blocks multi-value models/methods | `suggest_categorical()` for model, method, retriever (after A2) |
| `padding` axis | Fixed at 0 | Full third dimension with dedup tracking |
| Study persistence | In-memory only; HTTP 409 on resume | `bayesian.storage` field; resume guard removed when set |
| Random search | Not present | `search_strategy: random` with `n_samples` |
| Dashboard Bayesian card | `bayesian_summary` in payload | Full card in `ExperimentDetailScreen` |

---

## Planning Quality Lens [GATE — resolve when slice opens]

| # | Principle | Status | Rationale |
|---|---|---|---|
| 1 | Simple Design: Fewest Elements | ⏳ PARKED | Scope is bounded; open questions A1–A4 may narrow or expand scope |
| 2 | YAGNI | ⏳ PARKED | Categorical axes depend on A2 validation — may be deferred further |
| 3 | SLAP | ✅ | Parallelism layer (infrastructure) and search space expansion (domain) are separate sub-slices |
| 4 | Walking Skeleton | ✅ | Study persistence is the skeleton — enables resume and unlocks categorical experiments |
| 5 | Composability | ✅ | Depends only on 41A (completed) and owner's data (A4) |
| 6 | Rule of 3 | ✅ | All changes are concrete: persistence, categorical, padding, random search — 4 real cases |
| 7 | Specification-First | ✅ | After-Checks serve as gate scenarios; GWT prose will be filled in when slice opens and A1–A4 are resolved — stubs are in place |
| 8 | API First | ✅ | `bayesian.storage` and `bayesian.parallelism` are config-level additions (no new API endpoints) |
| 9 | Overengineering Flag | ✅ | No framework — same `_run_single()` pipeline; only new wiring in `_run_bayesian_inner_v2` |
| 10 | Artifact Path Harmonization | ✅ | Slice paths aligned to `docs/plan/slices/` SSOT |

---

## Before-Checks [GATE — verify when slice opens]

- [ ] Slice 41A is ✅ PASSED and merged to main.
- [ ] `_run_single()` 4-arg call is **confirmed fixed in 41A before 41A merges** — the implementation must pass `config.execution.parallelism` as the fourth argument; a code review or test must demonstrate this explicitly before 41A's PR is approved.
- [ ] Owner has set N for promotion evaluation (A4).
- [ ] A2 — categorical TPE quality validated across ≥3 datasets (or explicitly waived for this slice).
- [ ] Open questions A1, A3, D3, D6, D7 resolved and logged in DECISIONS.md.
- [ ] `optuna>=3.6` (ask-and-tell API stable) confirmed in environment.

---

## After-Checks [GATE — define when slice opens]

> These are stubs. Fill in concrete GWT tests and gate evidence when the slice is specced.

- [ ] [GATE] `bayesian.parallelism` workers (1–4) produce the expected concurrent trial submissions.
- [ ] [GATE] Constant liar study quality (≥90% of sequential baseline) — see measurement spec below.
- [ ] [GATE] `bayesian.storage` enables resume across server restarts; HTTP 409 guard removed.
- [ ] [GATE] Categorical axes (model, method, retriever) sweep correctly when A2 passed.
- [ ] [GATE] `padding` included in dedup key and grid_equivalent calculation.
- [ ] [GATE] `search_strategy: random` runs without Optuna dependency; embarrassingly parallel.
- [ ] [GATE] Dashboard Bayesian card renders correctly; non-Bayesian experiments unaffected.
- [ ] [GATE] All 41A tests still pass unchanged.
- [ ] [GATE] Spec coverage, branch coverage (100%), mutation testing: no high-severity survivals.

### Gate Evidence Specification — Constant Liar Quality (≥90%)

Defines how to measure the "≥90% quality vs. sequential baseline" claim. Fill in the evidence file path below with measured results before this slice is approved.

**Dataset**: use the project's existing test PDF corpus (≥100 pages; `input_data/pdfs/` fixtures used in 41A integration tests). Do not use a new dataset — results must be reproducible from existing fixtures.

**Metric**: best `query_avg_score` across all completed trials (same field as `bayesian_summary.best_score` from 41A).

**Protocol**:
1. Run same experiment config (same PDFs, same queries, same `n_trials`) with `bayesian.parallelism: 1` → record `score_sequential`.
2. Run same config with `bayesian.parallelism: 2` → record `score_parallel_2`.
3. Run same config with `bayesian.parallelism: 4` → record `score_parallel_4`.
4. Repeat each run 3× and take the mean to average out TPE stochastic startup.

**Pass condition**:
- `score_parallel_2 / score_sequential ≥ 0.90`
- `score_parallel_4 / score_sequential ≥ 0.90`

**Fail action**: if either ratio falls below 0.90, lower the `le=` validator in `BayesianConfig` to the highest passing worker count, log the revised cap in DECISIONS.md.

**Evidence file**: `docs/plan/gate-evidence/slice-41B.json` — include the three score vectors and computed ratios.

---

## Gate Evidence

- `docs/plan/gate-evidence/slice-41B.json` (create when slice opens)
