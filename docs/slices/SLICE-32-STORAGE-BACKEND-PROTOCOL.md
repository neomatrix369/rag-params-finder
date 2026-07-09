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
  - `server/db/storage.py` — Protocol / ABC for store operations
  - `server/db/mongo_store.py` — Mongo adapter (extract from `atlas.py`, indexes, experiments helpers)
  - `server/db/store_factory.py` — `get_store()` from settings
  - `server/settings.py` — `storage_backend: Literal["mongo","postgres"]` (default `mongo`)
  - Call sites: `orchestrator.py`, `experiments*.py`, `startup_reconciliation.py`, `retriever.py` (thin wrap)
  - `tests/test_store_factory.py`, `tests/test_mongo_store_adapter.py`
- Exit criteria: Mongo path behavior unchanged; all store I/O goes through Protocol; quality gates green
- Commit pattern: `feat(slice-32): extract storage backend protocol with mongo adapter`

---

## Goal

Introduce a dual-backend **storage Protocol** and extract the existing MongoDB implementation behind it, with **zero user-visible behavior change**. Postgres adapter is stubbed or NotImplemented until Slice 33.

---

## Spec (GWT)

```
Scenario: Default backend remains Mongo
  Given STORAGE_BACKEND is unset or "mongo"
  When the server starts and a sweep runs
  Then all reads/writes use the Mongo adapter and existing Atlas/local paths work

Scenario: Factory rejects unknown backend
  Given STORAGE_BACKEND="redis"
  When get_store() is called
  Then a clear configuration error is raised (no silent fallback)

Scenario: Protocol surface covers CRUD + retrieval hooks
  Given the StorageBackend Protocol
  When inspected by tests
  Then it declares methods for experiments, run_status, chunks, results,
       cascade delete, boot reconciliation query, and retrieval entrypoints
       (dense/sparse/hybrid may be on RetrieverBackend or same Protocol — one decision, documented)
```

---

## Before-Checks [GATE]

- [ ] Branch `slice/32-storage-backend-protocol` from latest `main`
- [ ] `./scripts/quality-gates.sh --quick` green on baseline
- [ ] Read PRD §4 module inventory + Decision #10 (factory over Protocol unless contract needed — here Protocol **is** required for dual backend)

---

## TDD Execution

1. RED — factory + adapter characterization tests (existing Mongo behavior locked)
2. GREEN — extract Protocol; move Mongo code behind adapter; wire factory
3. REFACTOR — no duplicate connection logic; settings-driven selection
4. VERIFY — full suite + one manual local Mongo sweep

---

## After-Checks [GATE]

- [ ] All GWT scenarios have named tests
- [ ] No API/CLI/dashboard behavior change on Mongo default
- [ ] `postgres` backend either raises clear "not implemented" or is absent until Slice 33
- [ ] Specification coverage: every GWT clause ≥1 test; essential error paths covered
- [ ] Branch coverage: 100% target on new modules; exclusions documented
- [ ] Mutation testing if feature-complete for this slice (§23)
- [ ] `./scripts/quality-gates.sh` passes
- [ ] Doc audit: CLAUDE.md Key Files + architecture note for Protocol

## Gate Status

📋 PLANNED
