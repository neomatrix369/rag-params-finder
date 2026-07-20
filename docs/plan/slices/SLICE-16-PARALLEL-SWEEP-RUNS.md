# SLICE 16 — Parallel Sweep Run Execution

**MoSCoW:** SHOULD *(throughput / wall-clock time for large sweeps; not blocking core RAG correctness)*
**Target time:** 2.5–3 h *(hard stop)*
**Status:** ✅ COMPLETE
**Actual time:** 2.5–3 h *(Approach A implemented directly)*

---

## Before-Checks [GATE]

- [ ] `./scripts/quality-gates.sh --quick` green on `main`
- [ ] Branch `slice/16-parallel-sweep` from latest `main`
- [ ] Characterization: `parallelism: 1` sweep baseline captured (timing + run_status rows)

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
- [ ] **SIE parallelism safeguard**: hardcode an in-process cap on concurrent SIE encode requests plus retry/backoff for transient 503-style failures.
- [ ] **Cancellation**: user cancel stops new work and terminates the sweep with `CANCELLED` as reliably as today *(define whether in-flight runs are waited out or signaled)*.
- [ ] **`ExecutionConfig.parallelism`** validated: `>= 1` and upper guard *(hardcoded max 16)* to avoid accidental fork bombs.
- [ ] **`docs/user-guide/configuration.md`** updated: remove “stored but ignored”; document limits and caveats for Voyage vs local providers.
- [ ] `ExperimentDetailScreen` elapsed/ETA subtitle reflects sweep parallelism impact through observed run throughput (`completed / elapsed`) and not a fixed per-run constant; add regression test coverage.

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
| `docs/user-guide/configuration.md` | Accurate parallelism semantics |

---

## Key Decisions *(to log in PROGRESS when slicing starts)*

| Decision | Record when |
|---|---|
| Approach A vs B | **A only** (Bounded in-process `ThreadPoolExecutor`) implemented for this slice; B explicitly out of scope today |
| SIE saturation handling | **Hardcoded in-process permit cap** + exponential backoff retries on transient 503-style SIE failures, no cross-process limiter |
| `on_error: stop` vs in-flight runs | `on_error: stop` means stop scheduling new `_run_single` runs after first failure; in-flight runs are allowed to finish |
| Voyage limiting: centralized vs per-run | Skipped for this demo slice because runs are local sentence-transformers only |

---

## Exit Criteria *(manual QA)*

- Config `parallelism: 4` *(local provider, small sweep)* completes with same result cardinality as sequential `parallelism: 1` on the same random seed-less pipeline.
- Cancelling experiment mid-way leaves no orphaned `RUNNING` runs forever *(eventual consistency with defined timeout acceptable if documented)*.
- Add a before/after wall-clock demo: run identical local-provider sweep config twice (`parallelism: 1` and `parallelism: 4`) and capture dashboard elapsed/ETA delta live.

---

## Dependencies & Ordering

| Dependency | Notes |
|---|---|
| Slice 3 ✅ | Cartesian expansion + sequential sweep baseline |
| Slice 10 *(optional, partial)* | **SKIPPED for this session** (today demo scope is parallel execution only; recovery integration left for later) |

---

## After-Checks

- [ ] `./scripts/quality-gates.sh --quick` pass
- [ ] `pytest -q tests/test_slice16_parallel_sweep.py` for bounded concurrency + on_error/cancel semantics, model bounds, and CLI timeout override checks
- [ ] `pytest -q tests/test_config_examples.py tests/test_sweep_endpoint.py` for experiment payload compatibility after executor changes
- [ ] Manual: submit identical local sweep with `parallelism: 1`, then `parallelism: 4`, capture elapsed/ETA difference from dashboard cards
- [ ] Manual: verify dashboard `12 of 120` elapsed/ETA cards converge faster with parallel sweeps as long as completed count grows faster
- [ ] Manual: exercise parallel local sweeps and confirm no sustained 503 errors in SIE logs when encode cap is in effect
- [ ] Manual: submit config with `parallelism: 2` and confirm scheduling concurrency in logs (no single-run lock step between submissions)
- [ ] Manual: `curl http://127.0.0.1:8001/health` and `curl http://127.0.0.1:8001/experiments` before each benchmark run
- [ ] Branch coverage target reviewed for touched modules `server/core/orchestrator.py` and `server/models/config.py` (`coverage report` + acceptable exclusions logged in PR notes)
- [ ] Frontend test: `frontend/src/components/ExperimentDetailScreen.test.tsx` includes elapsed/ETA throughput coverage for completion-rate behavior.

---

## Automated quality gates

```bash
bash scripts/install-git-hooks.sh
./scripts/quality-gates.sh
```

See [`development.md`](../contributor-guide/development.md) § Git hooks.

---

## See Also

- `docs/plan/slices/PROGRESS.md` — roadmap row for this slice
- [`SLICE-03-SWEEP-EXPANSION.md`](./SLICE-03-SWEEP-EXPANSION.md) — baseline sequential behavior
- [`../contributor-guide/architecture.md`](../contributor-guide/architecture.md) — BackgroundTasks vs future Celery narrative
