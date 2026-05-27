# SLICE 16 — Parallel Sweep Run Execution

**MoSCoW:** SHOULD *(throughput / wall-clock time for large sweeps; not blocking core RAG correctness)*
**Target time:** ~2–4 h *(depends on Approach A vs B below)*
**Status:** 📋 PLANNED

---

## Goal

Honor `execution.parallelism` in YAML: run independent sweep slices **up to N at a time** instead of strictly sequential `_run_single()` calls, **without** sacrificing correct `run_id` / phase tracking / `on_error` / cancellation semantics already defined in Slice 3 and Slice 4.

**Current state**: `parallelism` is persisted on experiment documents but **`server/core/orchestrator.py` does not read it**; runs always execute sequentially in `_run_sweep_inner()`.

---

## Problem Statement

Large Cartesian products (`models × chunking × sizes × overlaps × retrieval`) scale wall-clock time linearly when `parallelism: 1`. Atlas and MongoDB can usually absorb concurrent writes; the main tensions are:

- **Voyage / cloud APIs**: RPM and TPM envelopes require a shared limiter across workers or processes.
- **Local models**: VRAM/RAM share + Python threads vs processes *(GIL is less restrictive for GPU-bound embedding in many setups, but still needs validation)*.
- **Cancellation**: `request_cancel()` + `_check_cancelled()` must reliably stop queued and in-flight work when parallelism > 1.
- **`on_error: stop`**: deterministically cease scheduling new runs after first failure *(including runs already queued in a worker pool)*.

---

## Acceptance Criteria *(implementation exit)*

- [ ] `_run_sweep_inner` uses `config.execution.parallelism` *(default `1`)* to cap concurrent executions of `_run_single` for runs in **that** experiment.
- [ ] Behavior with `parallelism: 1` matches existing sequential semantics *(characterization / regression checks)*.
- [ ] **`on_error: continue`**: failures in parallel runs behave like today — count failures and continue scheduling until the sweep completes or cancelled.
- [ ] **`on_error: stop`**: first failing run triggers stop — no new `_run_single` starts; in-flight siblings may finish or abort *(document chosen policy in PROGRESS Decision Log)*.
- [ ] **Cancellation**: user cancel stops new work and terminates the sweep with `CANCELLED` as reliably as today *(define whether in-flight runs are waited out or signaled)*.
- [ ] **`ExecutionConfig.parallelism`** validated: `>= 1` and upper guard *(e.g. max 16 or configurable via `settings`)* to avoid accidental fork bombs.
- [ ] **`docs/user-guide/configuration.md`** updated: remove “stored but ignored”; document limits and caveats for Voyage vs local providers.
- [ ] Optional **`settings`**: max default parallelism ceiling and/or feature flag for phased rollout *(if needed for ops)*.

---

## Architectural Approaches

| Approach | Summary | Fits current stack |
|----------|---------|---------------------|
| **A — Bounded in-process concurrency** | `concurrent.futures.ThreadPoolExecutor` *(or semaphore + manual futures)* shared across runs **inside** the existing FastAPI BackgroundTask `run_sweep` | Minimal ops change; Celery unnecessary for moderate N |
| **B — Celery + Redis *(or similar)*** | Enqueue each `run_id` / `RunParams`; workers pull jobs; experiment completion aggregated | Matches long-term roadmap in docs when global queue + horizontal scale matter |

Recommendation: prototype **Approach A** inside `orchestrator` first *(same MongoDB semantics, simplest deploy)*; move to **B** if multi-process isolation, retries, or cross-experiment fairness become requirements.

---

## Files Likely Touched *(when implemented)*

| File | Change |
|---|---|
| `server/core/orchestrator.py` | Replace strict `for`/serial loop with bounded parallel execution respecting cancel + `on_error` |
| `server/models/config.py` | Validators / bounds on `ExecutionConfig.parallelism` |
| `server/settings.py` | Optional ceilings: `SWEEP_MAX_PARALLELISM_DEFAULT`, API rate-limit coordination knobs |
| `server/core/embedder.py` (+ `local_embedder`) | Shared global limiter *(Voyage TPM/RPM)* if multiple threads hit the same provider |
| `docs/user-guide/configuration.md` | Accurate parallelism semantics |

---

## Key Decisions *(to log in PROGRESS when slicing starts)*

| Decision | Record when |
|---|---|
| Approach A vs B | Before coding |
| `on_error: stop` vs in-flight runs | Before coding |
| Voyage limiting: centralized vs per-run | Before coding |

---

## Exit Criteria *(manual QA)*

- Config `parallelism: 4` *(local provider, small sweep)* completes with same result cardinality as sequential `parallelism: 1` on the same random seed-less pipeline.
- Cancelling experiment mid-way leaves no orphaned `RUNNING` runs forever *(eventual consistency with defined timeout acceptable if documented)*.

---

## Dependencies & Ordering

| Dependency | Notes |
|---|---|
| Slice 3 ✅ | Cartesian expansion + sequential sweep baseline |
| [Slice 10](./SLICE-10-RUN-RECOVERY.md) *(optional)* | Recovery batching should honor `parallelism` and cancel/`on_error` once both slices ship |

---

## Automated quality gates

```bash
bash scripts/install-git-hooks.sh
./scripts/quality-gates.sh
```

See [`development.md`](../contributor-guide/development.md) § Git hooks.

---

## See Also

- `docs/_internal/PROGRESS.md` — roadmap row for this slice
- [`SLICE-03-SWEEP-EXPANSION.md`](./SLICE-03-SWEEP-EXPANSION.md) — baseline sequential behavior
- [`../contributor-guide/architecture.md`](../contributor-guide/architecture.md) — BackgroundTasks vs future Celery narrative
