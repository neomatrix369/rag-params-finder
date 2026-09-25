# SLICE 49B — Split-Store Data-Path Rewire + E2E Acceptance

**MoSCoW:** MUST
**Target time:** ~6–8 h
**Status:** 📋 PLANNED
**Depends on:** [49A](SLICE-49-VECTOR-STORE-PORT-SPLIT-REGISTRY.md) (`VectorStore` port, registry, composites, `get_vector_store()`, stores locked equal)
**Branch:** `slice/49b-vector-store-data-path-rewire`
**Feature:** Elasticsearch vector-store adapter (ADR-006)

> **Origin (2026-09-25, DECISIONS #240/#242):** the round-3 end-to-end desk-check showed that the original Slice 49 never moved the chunk data path onto the vector port. With vectors in ES and run state in Postgres/Mongo: chunks were written to the run-state store (`orchestrator.py:921`), queries returned 0 hits, runs finished COMPLETE with empty results and every Bayesian trial scored 0.0; `/healthz` returned 200 with ES down; stats and delete used the wrong store. This slice fixes that, proves it with an in-memory vector store before any ES code exists, and then relaxes the 49A lock to pairing rule (ii).

---

## Context

After 49A the port exists but every caller still routes chunks through `StorageBackend`. 49B moves each chunk operation to `get_vector_store()`, makes delete/stats/health/preflight/boot two-store aware, and adds the split-store acceptance test that Slices 50 (ES) and 53 (Redis) re-run against live stores. Single-store Mongo/Postgres behaviour stays byte-identical (49A characterization records).

- **Depends-on outputs:** 49A port, registry, composites, `get_vector_store()`, AST guard, characterization records.
- **Invariants pointer:** `docs/plan/invariants.md` § Vector store / split-store — chunk access only via the vector port; pairing rule (ii); delete vectors first; two-store health; one `DatabaseProvider` Literal.

## Non-goals

- Any Elasticsearch code (→ Slice 50). The split-store test uses an in-memory `VectorStore` double.
- CLI `indexes list/reset` routing (→ Slice 51 via `GET /api/stores`).
- Frontend label changes (→ Slice 51).
- Post-write chunk-count guard — **Could** (DECISIONS #245); if added, warn-only.

## Output contract

### Rewire sites (every chunk operation on exactly one port)

| # | Call site today | After 49B |
|---|---|---|
| 1 | `orchestrator.py:921` `get_storage_backend().insert_chunks(...)` | `get_vector_store().upsert_chunks(...)` |
| 2 | `search.py:50` `get_retriever_backend().search(...)` | Unchanged call; now resolved via the vector store (49A factory) — covered by the E2E test |
| 3 | `experiments_shared.py:59-60` delete | `delete_experiment_data()` use-case: **vectors first** (idempotent), then run state, counts merged |
| 4 | `experiments_shared.py:61-68` db-stats + grouped stats | Run-state facts from `StorageBackend` + chunk facts from `VectorStore.stats()`; labels from the registry |
| 5 | `mongo_store.py:231-252` cascade deletes chunks | Chunk delete removed from the run-state cascade (the vector store owns it) |
| 6 | `postgres_store.py:320-338` cascade deletes chunks | Same as #5 (single-store Postgres still ends with no chunk rows — characterization proves it) |
| 7 | `main.py` lifespan index bootstrap | `ensure_indexes()` on the vector store; run-state bootstrap stays on `StorageBackend`; no unused `chunks` index when the vector store is elsewhere |
| 8 | `settings.ensure_storage_ready()` | Checks both URIs; **fail-fast boot** when the vector store is unreachable |
| 9 | `health_check.py` `/healthz` | Two-store response (below) |
| 10 | `search_index_guard.py` preflight | Dual-store preflight: vector-store objects + run-state objects; vector-store failure reported first (moved here from Slice 50) |

### Two-store `/healthz` (DECISIONS #247)

- Returns **503 if either store is down**.
- `storage_mode` keeps meaning the **vector store** (dashboard and `health-check.sh` keep working); adds `run_state_mode` and `stores: {vector: {provider, mode, ok, latency_ms}, run_state: {…}}`. Single-store deployments report both equal.

### Pairing rule (ii) (DECISIONS #241)

The 49A equality lock is replaced by: **if the vector store `can_host_run_state`, then `VECTOR_STORE_BACKEND` must equal `STORAGE_BACKEND`.** Vector-only stores (ES, Redis) may pair with either run-state store. Rejected at settings validation with the reason (e.g. Mongo run state + Postgres vectors breaks the `schema.sql` FKs to `experiments`).

### Delete across two stores (DECISIONS #246)

- Order: vector store first, then run state. Both steps idempotent; a retry after a partial failure completes the delete and reports the true counts.
- Invariant: no vector without a run-state experiment, except transiently during a delete.
- **Should (this slice if time allows, else a CF row pointing at Slice 51):** an orphan-vector reconciler that deletes vector-store chunks whose `experiment_id` no longer exists in run state — run at boot next to `startup_reconciliation.py` and via CLI.

### Observability

- Each composite and the vector-store call sites log per-store latency and outcome with the store name (`scope_log`), and Aim run params record `vector_store` + `run_state_store` so sweeps on different stores are comparable.

### Test infrastructure

- **In-memory `VectorStore` double** (`tests/helpers/memory_vector_store.py`), registered under `memory` for tests only, `can_host_run_state=False`. It honours the three mandatory filters, `top_k`, the `(1+cos)/2` dense score scale, delete counts and a simple term-overlap sparse score.
- **`_patch_backends` helper** in `tests/helpers/pipeline_sweep.py` patches `get_storage_backend`, `get_vector_store` and `get_retriever_backend` together; the ~11 test files that patch the factories today migrate to it.
- **Anti test-theater guard:** a test fails if any test sets chunk-method expectations (`insert_chunks`, `delete_chunks_for_experiment`) on a run-state mock — those calls must now hit the vector store.

## Reuse ledger

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Stale-run boot sweep | `server/core/pipeline/startup_reconciliation.py` | **Extend** with the orphan-vector pass (Should) |
| Delete orchestration | `experiments_shared.py` delete helper | **Extend** into the two-store use-case |
| Stats assembly | `stats_common.py` neutral half | **Reuse**; the provider part comes from `VectorStore.stats()` |
| Health probe | `health_check.py` + `resolve_storage_mode()` | **Extend** to two stores |
| Pipeline test fakes | `tests/helpers/pipeline_sweep.py::_fake_storage_backend` | **Extend** with `_patch_backends` |
| Scoped logging | `server/utils/scope_log.py` | **Reuse** |
| Aim logging | `server/core/aim_logger.py` | **Reuse** — two params added |
| **Net-new (only)** | `delete_experiment_data()` use-case, pairing validator, in-memory `VectorStore` double, split-store AT, anti test-theater guard | Write new |

---

## Slice Workflow Bundle

- Slice name: `slice-49b-vector-store-data-path-rewire`
- Branch: `slice/49b-vector-store-data-path-rewire`
- Order: (1) RED split-store AT against the in-memory double — it must **fail on 49A** (proves it detects the defect); (2) migrate tests to `_patch_backends`; (3) rewire sites 1–10; (4) relax the lock to rule (ii); (5) GREEN + characterization still identical.
- Commit pattern: `feat(storage): route chunk data path through the vector-store port; split-store pairing rule`
- **Doc exit (Must):** `invariants.md` § Vector store rows verified; `architecture.md` gains the split-store data-flow diagram (ingest → vector store; runs/results → run-state store); `configuration.md` documents `VECTOR_STORE_BACKEND` + pairing rule; `/healthz` shape in `cli-reference.md`; CHANGELOG + PROGRESS/TRAIL.

---

## Spec (GWT)

```
Scenario: A split-store sweep writes, finds, reports and deletes through the vector store
  Given run state on the configured run-state store and VECTOR_STORE_BACKEND=memory
  When a sweep runs through the orchestrator and API (not adapter calls)
  Then chunks are written only to the vector store (the run-state store holds none)
    And every query returns hits and recall is above 0
    And GET /healthz shows storage_mode = the vector store and run_state_mode = the run-state store
    And db-stats counts the vector-store chunks under the vector store's label
    And DELETE reports the written chunk count and leaves both stores empty for that experiment

Scenario: The same test fails on the 49A wiring (detects the defect)
  Given the 49A code with the lock lifted in the test
  When the split-store scenario runs
  Then it fails on "chunks written to the vector store"

Scenario: Vector store down
  Given the vector store is unreachable
  When the server boots
  Then boot fails fast naming the vector-store URI setting
  When it goes down after boot
  Then /healthz returns 503 with stores.vector.ok = false
    And submitting a sweep fails preflight with the vector-store error reported first

Scenario: Partial delete is completed by a retry
  Given the vector-store delete succeeded and the run-state delete failed
  When DELETE is retried
  Then it succeeds, both stores are empty for the experiment, and the reported counts are correct

Scenario: Pairing rule (ii)
  Given STORAGE_BACKEND=mongodb and VECTOR_STORE_BACKEND=postgres
  When settings validate
  Then a clear error explains that a store able to hold run state must also hold it
  Given STORAGE_BACKEND=postgres (or mongodb) and VECTOR_STORE_BACKEND=elasticsearch
  Then settings validate

Scenario: Single-store behaviour unchanged
  Given the 49A characterization records for Mongo and Postgres
  When the same flow runs after the rewire
  Then every output matches exactly

Scenario: No test asserts chunk calls on the run-state mock
  Given the test suite
  When the anti test-theater guard runs
  Then no test sets insert_chunks / delete_chunks_for_experiment expectations on a StorageBackend mock
```

*(Parametrize handoff for `nw-distill`: the split-store scenario is parametrised over `{memory}` here; Slice 50 adds `elasticsearch` and Slice 53 adds `redis`, each against a live store. Assertions that only a live store can prove — refresh-before-return, delete-by-query counts, BM25 ranking, score scale on real vectors — belong to those live legs, not the double.)*

---

## Before-Checks [GATE]

- [ ] 49A ✅ COMPLETE; characterization records present.
- [ ] Baseline list of tests that patch the storage/retriever factories captured.
- [ ] harness-scout `detect_confirm` at slice start (touches orchestrator, API, guards, boot).

## After-Checks [GATE]

- [ ] Split-store AT green on `memory`; its RED run on 49A recorded in gate evidence.
- [ ] Characterization records unchanged for Mongo + Postgres.
- [ ] AST guard (49A) + anti test-theater guard green.
- [ ] Coverage floors hold; complexity per `./scripts/ci/quality-gates.sh` (orchestrator must not raise CC — Slice 47 target).
- [ ] `docs/plan/gate-evidence/slice-49b.json` with coverage/complexity fields.

### Closing Gates

- [ ] `nw-at-completeness-check` (gate #8)
- [ ] `nw-software-crafter-reviewer` (gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` + `nw-data-engineer-reviewer` (gate #9, parallel): each traces ingest → query → delete → stats → preflight → boot → `/healthz` through the real call sites with file:line evidence (DECISIONS #240)
- [ ] `nw-gate-evidence-validator` — 9 conditions pass
- [ ] `/verify-slice` — verdict COMPLETE

## Gate Status

📋 PLANNED — created 2026-09-25 (DECISIONS #242); confirmation review pending before AT authoring (`nw-distill`).
