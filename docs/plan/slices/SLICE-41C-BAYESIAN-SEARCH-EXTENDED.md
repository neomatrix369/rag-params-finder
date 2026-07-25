# Slice 41C — Bayesian Search: Extended

**Status**: 📋 PLANNED — all open questions resolved; blocked only on Slice 41B ✅ complete

**MoSCoW**: Could

**Branch**: `slice/41c-bayesian-search-extended` (not yet created)

**Depends on**: 41B ✅

**Target time**: ~3–4 h

---

## Decisions Log (resolved 2026-07-25)

| # | Question | Decision | Rationale |
|---|---|---|---|
| A1 | Study persistence backend | **SQLite** (`"sqlite:///bayesian.db"` default) | Judge-friendly, no extra infra, upgradeable later |
| A2 | Categorical TPE quality validation | **Waived** — implement `suggest_categorical()` without A/B gate | Gate was research-level; add doc note that quality on small categorical spaces is not empirically validated; revisit if users report poor results |
| A4 | Default promotion trigger N | **N = 20** production Bayesian sweeps; time-bound: if not reached by 2026-10-01, mark default-promotion Won't for current cycle | Suggested baseline in spec; owner confirmed |
| D3 | `sweep_summary` field | **Add both keys**: `search_strategy` and `bayesian_config` | Self-describing payload; small change, big readability win |
| D6 | `max_score` primary sort key | Already decided: `max_score` primary, `query_avg_score` tiebreaker | No action needed |
| D7 | Random search `n_samples` | **`RandomConfig(n_samples: int = Field(default=20, ge=1, le=500))`** | Mirrors `BayesianConfig` pattern; cap at 500 matches `n_trials` ceiling |

---

## Scope

### Study Persistence (`bayesian.storage`)

**Decision A1: SQLite default.**

Add `storage: str | None = Field(default=None)` to `BayesianConfig`:

```python
# None                     = in-memory (41A/41B behaviour, no resume)
# "sqlite:///bayesian.db"  = local SQLite — default when persistence wanted (judge-friendly)
# "mongodb://..."          = MongoDB backend (future production path)
```

When `storage` is set:
- Pass as `storage` arg to `optuna.create_study()`
- Remove the HTTP 409 resume guard introduced in 41A (Optuna's storage handles resume natively)

### Categorical Axes

**Decision A2: waived — implement without empirical gate.**

Expand `_bayesian_trial_to_run_params()` to sweep `embedding_model`, `chunking_method`, and retriever
type via `suggest_categorical()`. Remove the cross-field validator constraints from 41A enforcing
single values on these axes.

Doc note: TPE quality on small categorical spaces is not empirically validated against random search;
results should be monitored after real production sweeps.

For categorical-inclusive search, increase startup formula:

```python
n_startup = max(10, n_trials // 3)   # vs max(5, ...) for numeric-only in 41B
```

### `sweep_summary` field additions

**Decision D3: add both keys.**

When `search_strategy` is `"bayesian"`, include in `sweep_summary`:

```python
{
    "search_strategy": "bayesian",
    "bayesian_config": {
        "n_trials": resolved_n_trials,
        "n_startup_trials": resolved_n_startup,
        "parallelism": config.execution.bayesian.parallelism,
        "storage": config.execution.bayesian.storage,
    },
    ...  # existing keys unchanged
}
```

Non-Bayesian strategies include `"search_strategy": "grid"` (or `"random"`) with no `bayesian_config` key.

### Random Search (`search_strategy: random`)

**Decision D7: `RandomConfig(n_samples: int = Field(default=20, ge=1, le=500))`.**

Add `search_strategy: Literal["grid", "random", "bayesian"] = Field(default="grid")` to
`ExecutionConfig` (replacing the 41A/B `search_strategy` field already defined there).

Add `RandomConfig` to `server/models/config.py`:

```python
class RandomConfig(BaseModel):
    n_samples: int = Field(default=20, ge=1, le=500)
```

`_run_random_inner()` samples `n_samples` configs from the Cartesian product without replacement
and runs them via the existing `ThreadPoolExecutor` at full `config.execution.parallelism`
concurrency. Random search is embarrassingly parallel — no surrogate, no quality penalty at any
worker count.

> **Scope note**: random search is not a Bayesian technique. It shares the search-space config layer
> and was deferred from 41A alongside Bayesian features. Can be split to Slice 41D if scope grows.

### Dashboard Bayesian Card

Surface the CLI summary from 41A as a card in `ExperimentDetailScreen` when
`search_strategy == "bayesian"`:

```
┌──────────────────────────────────────────┐
│ Search Strategy: Bayesian                │
│ Best: chunk_size=512  overlap=50         │
│ Score: 0.847                             │
│ 45 trials · surrogate active from #16   │
│ vs 90 grid equivalent (50% fewer runs)  │
└──────────────────────────────────────────┘
```

Requires `bayesian_summary` field stored by 41A — no backend change needed.

### Default Promotion Evaluation

**Decision A4: N = 20; time-bound 2026-10-01.**

After 20 real production Bayesian sweeps, evaluate:

| Check | Pass condition |
|---|---|
| Config quality | Bayesian best config matches or beats grid best on same dataset |
| Trial efficiency | Bayesian converges within 50% of grid run count |
| Consistency | Holds across ≥3 different datasets |

If ≥2 of 3 pass consistently, open a product decision to promote `search_strategy: bayesian` as
recommended default for spaces > 150 combinations. If 20 sweeps not accumulated by 2026-10-01,
mark default-promotion Won't for current cycle.

---

## Spec (GWT — stub; fill in fully before implementation)

```
Scenario: SQLite persistence enables resume
  Given bayesian.storage: "sqlite:///bayesian.db"
  When the server restarts mid-sweep
  Then the study resumes from its last completed trial
  And the HTTP 409 resume guard is not triggered

Scenario: In-memory (no storage) behaviour unchanged
  Given bayesian.storage is unset
  When a Bayesian sweep completes
  Then behaviour matches 41A/41B baseline

Scenario: Categorical axes swept
  Given embedding.models contains two values and search_strategy: bayesian
  When a Bayesian sweep runs
  Then trials vary embedding_model via suggest_categorical

Scenario: Random search runs without Optuna
  Given search_strategy: random and random.n_samples: 10
  When a sweep runs
  Then exactly 10 unique configs are sampled and run in parallel (no Optuna import required)

Scenario: sweep_summary includes search_strategy and bayesian_config
  Given search_strategy: bayesian
  When a sweep completes
  Then sweep_summary contains search_strategy: "bayesian" and bayesian_config dict

Scenario: Dashboard Bayesian card renders
  Given a completed Bayesian experiment
  When the detail screen loads
  Then the Bayesian card shows best config, score, trial count, and grid comparison
  And non-Bayesian experiments show no Bayesian card
```

---

## Permanently Out of Scope

- `optuna-dashboard` as a third process — violates judge-friendly constraint
- Multi-objective optimisation (NSGA-II) — belongs in a RAGAS metrics slice
- Hyperband / Successive Halving — eliminated: atomic `_run_single()` cannot be pruned mid-run
- Evolutionary / Genetic search — eliminated: marginal gain, high implementation weight

---

## Files Expected

- `server/models/config.py` — `BayesianConfig.storage`; `RandomConfig`; `sweep_summary` additions
- `server/core/orchestrator.py` — `_run_random_inner()`; `_run_bayesian_inner_v2` storage arg; categorical expand in `_bayesian_trial_to_run_params()`
- `frontend/src/components/ExperimentDetailScreen.tsx` — Bayesian card (conditional on `search_strategy`)
- `frontend/src/types/index.ts` — `bayesian_config` field in sweep_summary type
- `tests/test_bayesian_search.py` — new scenarios for storage, categorical, random search, sweep_summary

---

## Before-Checks [GATE]

- [ ] Slice 41B ✅ merged to main
- [ ] ✅ A1 DECIDED: SQLite default storage
- [ ] ✅ A2 WAIVED: implement categorical without empirical gate; add doc note
- [ ] ✅ A4 DECIDED: N = 20; time-bound 2026-10-01
- [ ] ✅ D3 DECIDED: add `search_strategy` + `bayesian_config` to `sweep_summary`
- [ ] ✅ D7 DECIDED: `RandomConfig(n_samples=20, ge=1, le=500)`
- [ ] Branch `slice/41c-bayesian-search-extended` from latest `main`
- [ ] `./scripts/quality-gates.sh --quick` green on baseline

---

## After-Checks [GATE]

- [ ] `bayesian.storage: "sqlite:///bayesian.db"` enables resume across server restarts
- [ ] HTTP 409 resume guard removed when storage is set; in-memory path unchanged
- [ ] Categorical axes (`embedding_model`, `chunking_method`, retriever) swept via `suggest_categorical()`
- [ ] `sweep_summary` contains `search_strategy` and `bayesian_config` for Bayesian experiments; non-Bayesian unaffected
- [ ] `search_strategy: random` runs without Optuna import; `n_samples` cap at 500 enforced
- [ ] Dashboard Bayesian card renders for Bayesian experiments; absent for grid/random
- [ ] All 41A and 41B tests still pass unchanged
- [ ] Specification coverage: every GWT clause ≥1 test; essential error paths covered
- [ ] Branch coverage: 100% target on new modules; exclusions documented
- [ ] Mutation testing: run for new port/protocol modules (or document explicit feature-complete waiver)
- [ ] `./scripts/quality-gates.sh` passes
- [ ] PROGRESS.md updated (status + decision log entry)

## Gate Status

📋 PLANNED
