# SLICE 10 — Run Recovery (Failed / Interrupted Runs)

**MoSCoW:** COULD *(ops ergonomics; workarounds today are manual YAML subsets or Mongo cleanup + resubmit)*
**Target time:** ~1–2 h *(CLI + API + orchestration hooks; boot path is a small add-on if scoped narrowly)*
**Status:** 🔨 PARTIAL — boot **status reconciliation** shipped; **retry** CLI/API still planned

---

## Goal

Let operators **retry only the runs that did not succeed** inside an **existing** experiment, without re-executing **COMPLETE** runs or mutating their stored chunks or results.

Today:

- `rag-params-finder run` always creates a **new** `experiment_id` and `run_sweep` assigns a **fresh** `run_id` per sweep row.
- Partial sweeps (`on_error: continue`) yield experiment status **PARTIAL** with a mix of **COMPLETE** and **FAILED** runs.
- Cancellation marks in-flight runs **INTERRUPTED**.
- **Boot reconciliation** *(implemented)*: on server start, experiments still `running` get in-flight runs marked **INTERRUPTED** and status recomputed (`partial` / `complete` / `failed`). See `server/core/startup_reconciliation.py`.
- **`RECOVER_ON_BOOT`** retry of interrupted runs is **not** implemented yet — flag is metadata-only until Slice 10 ships.
- The only supported workflow for “redo the bad ones” is trimming YAML (or multiple YAMLs) and submitting a **new** experiment.

---

## Problem Statement

A large sweep can fail for transient reasons (rate limits, network, OOM, manual cancel). Re-submitting the full config duplicates successful work, wastes API quota, and complicates comparison across duplicate `experiment_id`s.

Data is already **scoped by `run_id`**:

- Chunks carry `run_id`; `chunk_id` is `{run_id}_{i}` in the orchestrator.
- Results are associated with `run_id` and `experiment_id`.
- `run_status` documents record the full parameter tuple per run (embedding model, chunking, sizes, retrieval, rerank).

Recovery should **reuse the same `run_id`** for a retried run so dashboards, URLs, and mental models stay stable; **delete only** artifacts tied to that `run_id` before re-execution.

---

## Acceptance Criteria *(implementation exit)*

- [ ] **CLI**: `rag-params-finder recover --experiment-id <uuid> [--dry-run] [--include-interrupted]` *(exact flag names finalized at implement time; `--dry-run` lists `run_id`s + phases that would be retried)*.
- [ ] **Default scope**: runs with `phase` **FAILED** only. **INTERRUPTED** included only when **`--include-interrupted`** *(or equivalent)* is passed — avoids surprising retries for deliberately cancelled work.
- [ ] **Never** retry runs in **COMPLETE** unless an explicit **danger** flag is added *(default off)* — document why in PROGRESS Decision Log if omitted.
- [ ] **Server API**: e.g. `POST /experiments/{experiment_id}/recover` with JSON body mirroring CLI options *(CLI calls this; keeps one implementation path)*.
- [ ] **Pre-run cleanup** for each targeted `run_id`: delete `chunks` and `results` documents where `run_id` matches; reset `run_status` to a clean **QUEUED** baseline *(preserve parameter fields; clear `error_message` / phase timestamps as needed)*.
- [ ] **Execution**: reuse `_run_single(experiment_id, run_id, params)` after building `RunParams` from the existing `run_status` row **or** from deterministic reconciliation with `expand_sweep` + stored experiment `config` *(pick one approach; document)*.
- [ ] **Config source**: use the **`config`** object on the `experiments` document *(already persisted at submit time in `POST /experiments`)* — do not require the original YAML file on disk for recovery.
- [ ] **Experiment aggregate**: after recovery job finishes, recompute `status`, `failed_count`, and `completed_at` on the experiment document to reflect the updated run outcomes.
- [ ] **Concurrency**: recovery runs **sequentially** unless [Slice 16](./SLICE-16-PARALLEL-SWEEP-RUNS.md) is complete — then honor `execution.parallelism` for the recovery batch *(documented ordering)*.
- [ ] **Docs**: update [CLI Reference](../user-guide/cli-reference.md), [Troubleshooting](../user-guide/troubleshooting.md) (`RECOVER_ON_BOOT`), and [Configuration](../user-guide/configuration.md) *(cross-link: recovery vs YAML subset)*.

---

## `RECOVER_ON_BOOT` Semantics *(narrow scope)*

**Already shipped (status only):** `server/main.py` lifespan calls `reconcile_orphaned_experiments()` on **every** boot — not gated by `RECOVER_ON_BOOT`. This fixes MongoDB status when the process died mid-sweep; it does **not** re-execute runs.

**Still planned (retry):** When `RECOVER_ON_BOOT=true`, enqueue the same recovery engine as the CLI to **retry INTERRUPTED** runs only *(process died mid-sweep)* — **not** all historical **FAILED** rows.

---

## Files Likely Touched *(when implemented)*

| File | Change |
|---|---|
| `cli/main.py` | `recover` Typer command |
| `cli/api_client.py` | POST recover endpoint |
| `server/api/experiments.py` | `POST /experiments/{id}/recover`; BackgroundTask for recovery sweep |
| `server/core/orchestrator.py` | `recover_failed_runs(...)` or extend `run_sweep` with a “recovery mode”; shared cleanup helper |
| `server/core/startup_reconciliation.py` | ✅ Boot status fix *(shipped)* — mark orphans `interrupted`, recompute experiment status |
| `server/api/experiments_shared.py` *(or new db helper)* | Bulk delete chunks/results by `run_id`; experiment status recomputation |
| `docs/user-guide/cli-reference.md` | Document `recover` |
| `docs/slices/PROGRESS.md` | Mark slice complete; decision log |

---

## Key Decisions *(log in PROGRESS when slicing starts)*

| Decision | Notes |
|---|---|
| Rebuild `RunParams` from `run_status` vs re-expand sweep | Prefer **run_status** as source of truth to avoid ordering drift |
| API idempotency | Second recover while job running → `409` or no-op *(choose one)* |
| `COMPLETE` overwrite | Default **forbidden** without explicit flag |

---

## Exit Criteria *(manual QA)*

- Create a sweep with `on_error: continue`; force one run to fail; run `recover --experiment-id …`; **COMPLETE** runs unchanged in Mongo; failed run reaches **COMPLETE**; experiment leaves **PARTIAL** or becomes **COMPLETE** as appropriate.
- `--dry-run` prints only; no Mongo writes.

---

## Dependencies & Ordering

| Dependency | Notes |
|---|---|
| Slices 3–4 ✅ | Sweep + `run_status` / phases |
| Slice 16 *(optional)* | Parallel recovery batching; cancel + `on_error` interaction |

---

## After-Checks

- [ ] `./scripts/quality-gates.sh` pass
- [ ] Specification coverage: every GWT clause has ≥1 test; interrupted and partial-recovery paths covered
- [ ] Branch coverage: 100% target; exclusions documented (test-writing-craft-quality.mdc §12)
- [ ] Mutation testing: survival budget met if slice is feature-complete (§23)
- [ ] Manual: kill server mid-run → restart → confirm interrupted run is recoverable or cleanly marked failed

---

## Automated quality gates

```bash
bash scripts/install-git-hooks.sh   # once — essential checks on commit and push
./scripts/quality-gates.sh          # full CI mirror before PR
```

See [`development.md`](../contributor-guide/development.md) § Git hooks and § When checks run.

---

## See Also

- [`docs/slices/PROGRESS.md`](./PROGRESS.md) — roadmap
- [`SLICE-03-SWEEP-EXPANSION.md`](./SLICE-03-SWEEP-EXPANSION.md) — sweep expansion
- [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](./SLICE-16-PARALLEL-SWEEP-RUNS.md) — parallelism vs recovery
