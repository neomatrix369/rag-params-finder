# SLICE 32 — Storage Backend Protocol + Mongo Adapter

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** none
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)

---

## Slice Workflow Bundle

- Slice name: `slice-32-storage-backend-protocol`
- Branch: `slice/32-storage-backend-protocol`
- Files (expected):
  - `server/db/storage.py` — `StorageBackend` Protocol: experiments, run_status, chunks, results, cascade delete, boot reconciliation
  - `server/db/retriever_backend.py` — `RetrieverBackend` Protocol: dense, sparse, hybrid (separate from CRUD — different query APIs)
  - `server/db/mongo_store.py` — Mongo `StorageBackend` + `RetrieverBackend` (extract from `atlas.py`, indexes, retriever call sites)
  - `server/db/store_factory.py` — `get_storage_backend()` / `get_retriever_backend()` from settings
  - `server/settings.py` — `storage_backend: Literal["mongo","postgres"]` (default `mongo`)
  - Call sites: `orchestrator.py`, `experiments*.py`, `startup_reconciliation.py` — **no direct** `server.db.atlas` imports
  - `tests/test_store_factory.py`, `tests/test_mongo_store_adapter.py`
- Exit criteria: Mongo path behavior unchanged; all store I/O goes through ports; quality gates green
- Commit pattern: `feat(slice-32): extract storage and retriever backend protocols with mongo adapter`

---

## Goal

Introduce dual-backend **StorageBackend** and **RetrieverBackend** ports and extract the existing MongoDB implementation behind them, with **zero user-visible behavior change**. Postgres adapters are stubbed or raise clear NotImplemented until Slice 33+.

### Seam decision (locked)

| Port | Owns |
|---|---|
| `StorageBackend` | Experiment/run/chunk/result CRUD, cascade delete, boot reconciliation queries |
| `RetrieverBackend` | dense / sparse / hybrid search only |

Orchestrator and API layers depend on ports — never on `pymongo` or `psycopg` directly.

---

## Spec (GWT)

```
Scenario: Default backend remains Mongo
  Given STORAGE_BACKEND is unset or "mongo"
  When the server starts and a sweep runs
  Then all reads/writes use the Mongo adapter and existing Atlas/local paths work

Scenario: Factory rejects unknown backend
  Given STORAGE_BACKEND="redis"
  When get_storage_backend() is called
  Then a clear configuration error is raised (no silent fallback)

Scenario: Storage backend abstracts all data I/O
  Given the server is running
  When experiments are submitted and sweeps execute
  Then all persistent data operations (create, read, update, delete)
  flow through StorageBackend with no direct imports of MongoDB or Postgres
  modules in orchestrator, experiments, or startup code

Scenario: Retrieval flows through RetrieverBackend
  Given a sweep reaches the querying phase
  When dense, sparse, or hybrid retrieval runs
  Then the retriever port is used — not ad-hoc calls into server.core.retriever
  from orchestrator without going through the backend factory
```

---

## Before-Checks [GATE]

- [ ] Branch `slice/32-storage-backend-protocol` from latest `main`
- [ ] `./scripts/quality-gates.sh --quick` green on baseline
- [ ] Read PRD seam table + Decision #10 (Protocol justified for dual-backend)

---

## TDD Execution

1. RED — factory + adapter characterization tests (existing Mongo behavior locked)
2. GREEN — extract ports; move Mongo code behind adapters; wire factory
3. REFACTOR — no duplicate connection logic; settings-driven selection
4. VERIFY — full suite + one manual local Mongo sweep

---

## After-Checks [GATE]

- [ ] All GWT scenarios have named tests
- [ ] No API/CLI/dashboard behavior change on Mongo default
- [ ] `postgres` backend raises clear NotImplemented for storage until Slice 33
- [ ] Grep confirms no `from server.db.atlas` in orchestrator/experiments/startup_reconciliation
- [ ] Specification coverage: every GWT clause ≥1 test; essential error paths covered
- [ ] Branch coverage: 100% target on new modules; exclusions documented
- [ ] `./scripts/quality-gates.sh` passes
- [ ] Doc audit: PRD §Documentation matrix rows for slice **32** (architecture, extending, CLAUDE Key Files)
- [ ] `docs/slices/PROGRESS.md` updated (status + decision log if applicable)

## Gate Status

📋 PLANNED
