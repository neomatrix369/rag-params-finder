# Slice 41C — Bayesian Search: Extended

**Status**: 📦 PARKED — gated on open questions A1, A2, A4, D3, D7 resolved + Slice 41B ✅ complete

**MoSCoW**: Could

**Branch**: `slice/41c-bayesian-search-extended` (not yet created)

**Depends on**: 41B ✅ + open questions resolved (see below)

**Target time**: ~3–4 h

---

## Why This Is Parked

These features were split from 41B because each requires an explicit owner decision or validation
experiment before speccing the implementation. Nothing here blocks 41B. This slice opens only after:

1. Slice 41B is ✅ complete and merged to main.
2. Open questions A1, A2, A4, D3, D7 are resolved and logged in DECISIONS.md.

---

## Open Questions (resolve before opening this slice)

| # | Question | Current Stance | Needs Before Speccing |
|---|---|---|---|
| A1 | Study persistence backend: SQLite vs MongoDB | SQLite preferred (judge-friendly); MongoDB consistent with stack | Owner decision: demo path vs production path |
| A2 | Categorical axis TPE quality validation | `suggest_categorical()` is valid; quality vs random search on small categorical spaces is unproven | A/B comparison: Bayesian vs random search on same categorical space across ≥3 real datasets |
| A4 | Revisit-trigger N for default promotion | "Owner to set N" — unresolved | Owner sets N before this slice opens; suggested baseline: 20 real production Bayesian sweeps. **Time-bound**: if N sweeps not accumulated by 2026-10-01, open product decision to lower threshold or mark Won't for current cycle. |
| D3 | `sweep_summary` field for Bayesian | Currently stores lists; misleading when axes are single-value | Decide whether to add `search_strategy` and `bayesian_config` keys to `sweep_summary` |
| D6 | `max_score` as primary sort key for grid | Still primary; `query_avg_score` is tiebreaker | Not a gate — can be resolved independently. Listed for completeness. |
| D7 | Random search `n_samples` config design | Not designed; deferred from 41A | Design alongside or before this slice |

---

## Scope (fill in GWT when slice opens)

### Study Persistence (`bayesian.storage`)

Resolves A1.

Add `storage: str | None = Field(default=None)` to `BayesianConfig`:

```python
# None       = in-memory (41A/41B behaviour, no resume)
# "sqlite:///bayesian.db" = local SQLite (judge-friendly, enables resume)
# "mongodb://..." = MongoDB backend (production path)
```

When `storage` is set:
- Pass as `storage` arg to `optuna.create_study()`
- Remove the HTTP 409 resume guard introduced in 41A (Optuna's storage handles resume natively)

### Categorical Axes (requires A2 validated)

Expand `_bayesian_trial_to_run_params()` to sweep `embedding_model`, `chunking_method`, and retriever type via `suggest_categorical()`.

Remove the cross-field validator constraints from 41A enforcing single values on these axes.

**Prerequisite (A2):** TPE quality on categorical axes must be validated against random search across
≥3 real datasets before this ships. If A2 is not met, omit categorical axes from this slice.

For categorical-inclusive search, increase startup formula:

```python
n_startup = max(10, n_trials // 3)   # vs max(5, ...) for numeric-only in 41B
```

### Random Search (`search_strategy: random`)

Resolves D7.

Add `search_strategy: Literal["grid", "random", "bayesian"] = Field(default="grid")` (validated in 41A/B).

Add `RandomConfig`:

```python
class RandomConfig(BaseModel):
    n_samples: int = Field(default=20, ge=1)
```

`_run_random_inner()` samples `n_samples` configs from the Cartesian product without replacement and
runs them via the existing `ThreadPoolExecutor` at full `config.execution.parallelism` concurrency.
Random search is embarrassingly parallel — no surrogate, no quality penalty at any worker count.

> **Scope note**: random search is not a Bayesian technique. It shares the search-space config layer
> and was deferred from 41A alongside Bayesian features. Can be split to Slice 41D if preferred.

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

### Default Promotion Evaluation (post owner-N sweeps)

After owner-set N sweeps (resolves A4):

| Check | Pass condition |
|---|---|
| Config quality | Bayesian best config matches or beats grid best on same dataset |
| Trial efficiency | Bayesian converges within 50% of grid run count |
| Consistency | Holds across ≥3 different datasets |

If ≥2 of 3 pass consistently, open a product decision to promote `search_strategy: bayesian` as
recommended default for spaces > 150 combinations.

---

## Permanently Out of Scope

- `optuna-dashboard` as a third process — violates judge-friendly constraint
- Multi-objective optimisation (NSGA-II) — belongs in a RAGAS metrics slice
- Hyperband / Successive Halving — eliminated: atomic `_run_single()` cannot be pruned mid-run
- Evolutionary / Genetic search — eliminated: marginal gain, high implementation weight

---

## Gate Evidence Specification — Constant Liar Quality (≥90%) [from original 41B]

Defines how to measure TPE quality under run-level parallelism for categorical-inclusive search.

**Dataset**: existing test PDF corpus (≥100 pages; `input_data/pdfs/` fixtures used in 41A integration tests).

**Protocol**:
1. Run same config with `bayesian.parallelism: 1` → record `score_sequential`.
2. Run same config with `bayesian.parallelism: 2` → record `score_parallel_2`.
3. Run same config with `bayesian.parallelism: 4` → record `score_parallel_4`.
4. Repeat each run 3× and take the mean.

**Pass condition**:
- `score_parallel_2 / score_sequential ≥ 0.90`
- `score_parallel_4 / score_sequential ≥ 0.90`

**Fail action**: lower `le=` validator in `BayesianConfig.parallelism` to the highest passing worker count; log in DECISIONS.md.

**Evidence file**: `docs/plan/gate-evidence/slice-41C.json`

---

## Before-Checks [GATE — verify when slice opens]

- [ ] Slice 41B ✅ merged to main
- [ ] A1 resolved — storage backend chosen (SQLite or MongoDB)
- [ ] A2 resolved — categorical TPE quality validated (or explicitly waived for this slice)
- [ ] A4 resolved — owner has set N for promotion evaluation
- [ ] D3 resolved — `sweep_summary` field decision logged in DECISIONS.md
- [ ] D7 resolved — `n_samples` config design agreed
- [ ] `./scripts/quality-gates.sh --quick` green on baseline

---

## After-Checks [GATE — stub; fill in when slice opens]

- [ ] `bayesian.storage: "sqlite:///bayesian.db"` enables resume across server restarts
- [ ] HTTP 409 resume guard removed when storage is set
- [ ] Categorical axes sweep correctly when A2 validated
- [ ] `search_strategy: random` runs without Optuna dependency; embarrassingly parallel
- [ ] Dashboard Bayesian card renders; non-Bayesian experiments unaffected
- [ ] All 41A and 41B tests still pass unchanged
- [ ] `./scripts/quality-gates.sh` passes
- [ ] PROGRESS.md updated

## Gate Status

📦 PARKED
