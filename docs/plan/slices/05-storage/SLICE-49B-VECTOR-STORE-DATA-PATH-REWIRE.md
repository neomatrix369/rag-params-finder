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
| 4 | `experiments_shared.py:61-68` db-stats + grouped stats (`GET /experiments/{id}/db-stats`, `GET /experiments/vector-db-stats`) | Run-state facts from `StorageBackend` + chunk facts from `VectorStore.stats()`; labels from the registry. **Response shapes unchanged** — same fields, values now composed; no `server/api` or frontend type change (keeps Slice 53's zero-changes criterion achievable). The characterization records cover both endpoints |
| 5 | `mongo_store.py:231-252` cascade deletes chunks | Chunk delete removed from the run-state cascade (the vector store owns it) |
| 6 | `postgres_store.py:320-338` cascade deletes chunks | Same as #5 (single-store Postgres still ends with no chunk rows — characterization proves it) |
| 7 | `main.py` lifespan index bootstrap | `ensure_indexes()` on the vector store; run-state bootstrap stays on `StorageBackend`; no unused `chunks` index when the vector store is elsewhere |
| 8 | `settings.ensure_storage_ready()` | Checks both stores' configuration; boot fails on a missing or placeholder URI (see Boot behaviour) |
| 9 | `health_check.py` `/healthz` | Two-store response (below) |
| 10 | `search_index_guard.py:131-200` + `search_index_plan.py:85-153` preflight | Dual-store preflight (moved here from Slice 50) — see orchestration below |

### `StorageBackend` chunk methods — lifecycle

- `insert_chunks` and `delete_chunks_for_experiment` are **removed from the `StorageBackend` Protocol** in this slice, once every caller uses `get_vector_store()`.
- They **stay on the concrete Mongo/Postgres classes**, because the 49A composites delegate to them. No deprecation decorator is needed.
- The 49A AST guard gains a rule: no call to a chunk method through `get_storage_backend()`.
- All test modules that patch the factories today (baseline list captured in Before-Checks, ~11 files) migrate to `_patch_backends` in this slice.

### Dual-store preflight — orchestration

One entry point, `preflight_stores(config)` in `search_index_guard.py`, called where preflight runs today (the orchestrator's `_fail_experiment_preflight` path, `orchestrator.py:409`, keeps reporting):

1. Vector store: `health()`, then `plan_indexes()` / `ensure_indexes()`, then the `capabilities()` checks (dims, retrieval methods). The first failure raises the existing preflight error (HTTP 422 at submit) and **stops**, so run-state checks are not attempted.
2. Run-state store: `health()` + required run-state objects.

In single-store mode both steps hit the same database, and the characterization records prove the output is unchanged.

**No skip path (walkthrough G3, DECISIONS #253).** `preflight_store_indexes()` today returns `preflight_not_applicable()` for any backend other than mongodb/postgres (`search_index_guard.py:147-152`). That branch is removed. `preflight_stores()` dispatches only through the vector store's port, and an adapter that returns no index plan raises the preflight error (422 naming the store). A store with a missing preflight fails closed instead of passing silently.

### Engine labels (walkthrough G1/G2, DECISIONS #253)

- **New runs** already persist the YAML `database_provider` (`orchestrator.py:839`), and D2 rejects a YAML that doesn't match the vector store. A run on a vector-only store is therefore labelled with that store, and 49B keeps it that way end to end.
- **Legacy rows** (persisted before `database_provider` was recorded) fall back to `settings.default_database_provider()`, which derives from `STORAGE_BACKEND` (`settings.py:176-185`). Such rows were written when both stores were the same engine, so that value is correct. **Freeze it.** `signatures.py:46` and `results_analyzer.py:31,125` keep this run-state fallback and must **not** follow `VECTOR_STORE_BACKEND`. Following it would change legacy signatures, so resume would re-run completed runs.
- **Stats allow-list:** `normalize_stats_database_provider()` (`stats_common.py:105-112`) maps any value other than mongo/postgres/supabase to the fallback, which would erase a persisted `elasticsearch` / `redis` label. It accepts every registered provider (from the registry, not a second list), with the `supabase → postgres` alias kept.

### Two-store `/healthz` (DECISIONS #247, refined by #250)

- Returns **503 if either store is down** (today it already returns 503 when `ok` is false — `main.py:108`).
- **Every key present today stays, with today's meaning** (`health_check.py:87-120`): `ok`, `storage_backend` (the run-state store, i.e. `STORAGE_BACKEND`), `storage_mode`, and the per-engine key (`mongodb` / `postgres`, including Mongo's `"skipped"`). In a split setup `storage_mode` reports the **vector** store, which is what the dashboard label (`frontend/src/types/index.ts:312`) and `health-check.sh:88` show.
- **Added keys:** `vector_store_backend`, `run_state_mode`, and `stores: {vector: {provider, mode, ok, latency_ms}, run_state: {…}}`.

Single-store (Postgres local) — today's keys plus the additions:

```json
{"ok": true, "storage_backend": "postgres", "storage_mode": "postgres-local", "postgres": "ok",
 "vector_store_backend": "postgres", "run_state_mode": "postgres-local",
 "stores": {"vector": {"provider": "postgres", "mode": "postgres-local", "ok": true, "latency_ms": 3},
            "run_state": {"provider": "postgres", "mode": "postgres-local", "ok": true, "latency_ms": 3}}}
```

Split store (ES down, returns HTTP 503):

```json
{"ok": false, "storage_backend": "postgres", "storage_mode": "elasticsearch-local", "postgres": "ok",
 "vector_store_backend": "elasticsearch", "run_state_mode": "postgres-local",
 "stores": {"vector": {"provider": "elasticsearch", "mode": "elasticsearch-local", "ok": false, "latency_ms": null,
                       "remediation": "Check ELASTICSEARCH_URL / ./start-services.sh elasticsearch status"},
            "run_state": {"provider": "postgres", "mode": "postgres-local", "ok": true, "latency_ms": 4}}}
```

### Boot behaviour (DECISIONS #250)

- **Configuration errors fail boot:** `settings.ensure_storage_ready()` raises `ValueError` from `lifespan` for a missing or placeholder URI of **either** store. The message names the setting, e.g. "VECTOR_STORE_BACKEND=elasticsearch requires ELASTICSEARCH_URL". This extends today's check (`settings.py:149-174`), and FastAPI startup aborts with a non-zero exit.
- **Reachability does not fail boot:** an unreachable store is reported by `/healthz` 503 and by preflight 422, as today for Mongo (`main.py:32-38` logs a warning and starts). This keeps single-store boot byte-identical. It also avoids restart loops while ES is still starting, since compose marks it `required: false` and ES takes tens of seconds to become healthy.

### Pairing rule (ii) (DECISIONS #241)

The 49A equality lock is replaced by: **if the vector store `can_host_run_state`, then `VECTOR_STORE_BACKEND` must equal `STORAGE_BACKEND`.** Vector-only stores (ES, Redis) may pair with either run-state store. Rejected at settings validation with the reason. Example message: "STORAGE_BACKEND=mongodb with VECTOR_STORE_BACKEND=postgres is not supported: postgres can hold run state, so it must hold both. Set VECTOR_STORE_BACKEND=mongodb, or STORAGE_BACKEND=postgres."

### Delete across two stores (DECISIONS #246)

- Order: vector store first, then run state. Both steps idempotent; a retry after a partial failure completes the delete and reports the true counts.
- Partial-failure matrix:

  | Vector delete | Run-state delete | Result | Recovery |
  |---|---|---|---|
  | fails | not attempted | experiment intact, error returned | retry DELETE |
  | succeeds | fails | experiment row remains without chunks, error returned | retry DELETE completes it (vector step deletes 0) |
  | succeeds | succeeds | both empty | — |
  | process crash between steps | — | same as row 2 | retry DELETE, or the reconciler |

- Invariant: no vector without a run-state experiment. Orphan vectors are possible only if a run-state experiment disappears some other way (manual DB edit, a crash inside a store's own cascade).
- **Should — orphan-vector reconciler:** deletes vector-store chunks whose `experiment_id` no longer exists in run state; runs at boot next to `startup_reconciliation.py` and via `rag-params-finder reconcile-vectors`. If it doesn't fit this slice, record the CF row `CF-49B-1 | orphan-vector reconciler not built | Slice 51 | build + test the boot pass and CLI command` in DECISIONS.

### Observability

- Each composite and the vector-store call sites log per-store latency and outcome with the store name (`scope_log`), and Aim run params record `vector_store` + `run_state_store` so sweeps on different stores are comparable.

### Test infrastructure

- **In-memory `VectorStore` double** (`tests/helpers/memory_vector_store.py`), registered under `memory` for tests only, `can_host_run_state=False`. It honours the three mandatory filters, `top_k`, the `(1+cos)/2` dense score scale, delete counts and a simple term-overlap sparse score.
- **Known-answer fixture** (`tests/fixtures/split_store/`): a few short text documents plus 5 queries, each with a known relevant passage, embedded by a deterministic bag-of-words test embedder (no model download). Recall assertions are therefore meaningful, not accidental.
- **`_patch_backends` helper** in `tests/helpers/pipeline_sweep.py` patches `get_storage_backend`, `get_vector_store` and `get_retriever_backend` together; the ~11 test files that patch the factories today migrate to it.
- **Anti test-theater guard** (`tests/test_no_run_state_chunk_expectations.py`): an AST scan of `tests/` that fails, naming file:line, on any `assert_called*` / `call_count` / `return_value` / `side_effect` use of `insert_chunks` or `delete_chunks_for_experiment` outside `tests/server/db/` and `tests/contract/` (the adapter-level suites that legitimately test those methods). It is a plain test, not a pytest hook, so it runs in PR CI with everything else.
- **Test files by kind:** `tests/server/test_split_store_e2e.py` (acceptance), `tests/server/test_vector_store_pairing.py` (settings rules), `tests/server/test_single_store_characterization.py` (49A golden records, replayed).

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
- Order:
  1. **RED:** the first commit on the branch (based on the 49A commit) adds only the split-store AT. Its fixture lifts the 49A lock for the test by constructing settings directly. The failing run's output (`test_split_store_e2e.py` failing on "chunks written to the vector store") is saved to `gate-evidence/slice-49b.json` as `red_run` (commit SHA + failing assertion).
  2. Migrate tests to `_patch_backends`.
  3. Rewire sites 1–10.
  4. Relax the lock to rule (ii).
  5. GREEN, with the characterization records still identical.
- Commit pattern: `feat(storage): route chunk data path through the vector-store port; split-store pairing rule`
- **Doc exit (Must):** `invariants.md` § Vector store rows verified; `architecture.md` gains the split-store data-flow diagram (ingest → vector store; runs/results → run-state store); `configuration.md` documents `VECTOR_STORE_BACKEND` + pairing rule; `/healthz` shape in `cli-reference.md`; CHANGELOG + PROGRESS/TRAIL.

---

## Spec (GWT)

```
Scenario: A split-store sweep writes, finds, reports and deletes through the vector store
  Given run state on the configured run-state store, VECTOR_STORE_BACKEND=memory
    and the known-answer fixture corpus with 5 queries
  When the experiment is submitted with POST /experiments (FastAPI TestClient)
    and the sweep runs through run_sweep (orchestrator.py:84), not adapter calls
  Then chunks are written only to the vector store (the run-state store holds none)
    And every query returns hits
    And for at least 4 of the 5 queries the known relevant passage ranks in the top 3
    And GET /healthz shows storage_mode = the vector store and run_state_mode = the run-state store
    And db-stats counts the vector-store chunks under the vector store's label
    And DELETE /experiments/{id} reports the written chunk count and leaves both stores empty for that experiment
    And a second DELETE reports 0 chunks, leaves both stores empty and does not error

Scenario: The same test fails on the 49A wiring (detects the defect)
  Given the 49A code with the lock lifted in the test
  When the split-store scenario runs
  Then it fails on "chunks written to the vector store"

Scenario: Vector store misconfigured
  Given VECTOR_STORE_BACKEND=elasticsearch and ELASTICSEARCH_URL unset
  When the server boots
  Then startup aborts with an error naming ELASTICSEARCH_URL

Scenario: Vector store unreachable
  Given the vector store is configured but unreachable
  When /healthz is called
  Then it returns 503 with stores.vector.ok = false and today's keys still present
    And submitting a sweep fails preflight with the vector-store error, and run-state checks are not attempted

Scenario Outline: A partial delete is completed by a retry
  Given a first DELETE that ended with <failure>
  When DELETE is retried
  Then it succeeds, both stores are empty for the experiment, and the reported counts are correct
  Examples:
    | failure                                              |
    | the vector-store delete failing (run state untouched) |
    | the run-state delete failing after vectors were gone  |
    | a process crash between the two steps                 |

Scenario: Deleting an experiment with no chunks
  Given an experiment whose runs wrote no chunks
  When DELETE /experiments/{id} runs
  Then it succeeds and reports 0 chunks

Scenario: A store that can hold run state must hold it
  Given STORAGE_BACKEND=mongodb and VECTOR_STORE_BACKEND=postgres
  When settings validate
  Then a clear error explains that a store able to hold run state must also hold it

Scenario Outline: A vector-only store pairs with either run-state store
  Given STORAGE_BACKEND=<run_state> and VECTOR_STORE_BACKEND=memory
  When settings validate
  Then they are accepted
  Examples:
    | run_state |
    | mongodb   |
    | postgres  |

Scenario Outline: A vector-store write failure fails the run and honours on_error
  Given the memory vector store raises on upsert_chunks for one run
  When the sweep runs with on_error=<mode>
  Then that run ends FAILED with the vector store named in its error
    And <others>
  Examples:
    | mode     | others                                 |
    | continue | the remaining runs complete            |
    | stop     | no further run starts after the failure |

Scenario: A paused and resumed split-store sweep does not re-embed completed runs
  Given a split-store sweep paused after some runs completed, using the test embedding provider that records every request it receives
  When it is resumed and completes
  Then the provider received no request for texts of runs that completed before the pause
    And the vector-store chunk count for those runs is the same before and after the resume
    And the experiment ends COMPLETE with results for every planned run

Scenario Outline: Runs persisted without database_provider keep their run-state label
  Given run rows without database_provider on run-state store <run_state>, and VECTOR_STORE_BACKEND=memory
  When the experiment is resumed and its results are analysed
  Then no completed run is executed again
    And explore, best-config and db-stats label those runs <run_state>
  Examples:
    | run_state |
    | mongodb   |
    | postgres  |

Scenario: A run on a vector-only store carries that store's label everywhere
  Given VECTOR_STORE_BACKEND=memory and a YAML with database_provider matching it
  When the sweep completes
  Then the run row, explore, best-config, db-stats and vector-db-stats all show the memory store

Scenario: A vector store without an index plan fails preflight closed
  Given a registered vector store that publishes no index plan for the submitted config
  When a sweep is submitted
  Then HTTP 422 names the store and the missing plan, and no experiment is persisted

Scenario: Single-store behaviour unchanged
  Given the 49A characterization records for Mongo and Postgres
    (sweep, results, db-stats, vector-db-stats, delete counts, preflight, and every /healthz key and value present today)
  When the same flow runs after the rewire
  Then every recorded output matches exactly (the new /healthz keys are additions only)

Scenario: No test asserts chunk calls on the run-state mock
  Given the test suite
  When the anti test-theater guard runs
  Then no test sets insert_chunks / delete_chunks_for_experiment expectations on a StorageBackend mock
```

*(Parametrize handoff for `nw-distill`: the split-store scenario and the resume scenario are parametrised over `{memory}` here; Slice 50 adds `elasticsearch` and Slice 53 adds `redis`, each against a live store. The first scenario stays one journey on purpose: it is the defect detector for #240, and the scenarios after it pin each concern separately. Assertions that only a live store can prove — refresh-before-return, delete-by-query counts, BM25 ranking, score scale on real vectors — belong to those live legs, not the double.)*

---

## Before-Checks [GATE]

- [ ] 49A ✅ COMPLETE; characterization records present.
- [ ] Baseline list of tests that patch the storage/retriever factories captured (`grep -rl "get_storage_backend\|get_retriever_backend" tests`).
- [ ] 49A characterization records include both stats endpoints and the full `/healthz` body.
- [ ] harness-scout `detect_confirm` at slice start (touches orchestrator, API, guards, boot).

## After-Checks [GATE]

- [ ] Split-store AT green on `memory`; its RED run on 49A recorded in `gate-evidence/slice-49b.json` (`red_run`: commit SHA + failing assertion).
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
