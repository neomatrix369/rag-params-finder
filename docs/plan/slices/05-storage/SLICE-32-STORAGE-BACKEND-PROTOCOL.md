# SLICE 32 — Storage Backend Protocol + Mongo Adapter

**MoSCoW:** MUST
**Target time:** ~3–4 h
**Status:** 🔨 IN PROGRESS (implementation on branch; craft remediation → [Slice 32C](SLICE-32C-STORAGE-PROTOCOL-REVIEW-REMEDIATION.md); verification gates → [Slice 32B](SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md))
**Depends on:** none
**Unblocks:** Slice 32C (review remediation) → Slice 32B (gate closure) → Slice 33
**PRD:** [`docs/plan/PRD-supabase-pgvector-migration.md`](../../PRD-supabase-pgvector-migration.md)
**PR:** [#110](https://github.com/neomatrix369/rag-params-finder/pull/110)

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

- [x] Branch `slice/32-storage-backend-protocol` from latest `main` (rebased on 512213f, 2026-07-25)
- [x] `./scripts/quality-gates.sh --quick` green on baseline (2026-07-25)
- [x] Read PRD seam table + Decision #10 — Protocol justified: dual-backend (Mongo ↔ Postgres swappable) is the explicit exception case Decision #10 acknowledges; factory alone cannot enforce a cross-adapter contract

---

## TDD Execution

1. RED — factory + adapter characterization tests (existing Mongo behavior locked)
2. GREEN — extract ports; move Mongo code behind adapters; wire factory
3. REFACTOR — no duplicate connection logic; settings-driven selection
4. VERIFY — full suite + one manual local Mongo sweep

---

## After-Checks [GATE]

- [x] All GWT scenarios have named tests
- [x] No API/CLI/dashboard behavior change on Mongo default
- [x] `postgres` backend raises clear NotImplemented for storage until Slice 33
- [x] Grep confirms no `from server.db.atlas` in orchestrator/experiments/startup_reconciliation (also `runs.py`)
- [x] Specification coverage: every GWT clause ≥1 test; essential error paths covered
- [x] Doc audit: PRD §Documentation matrix rows for slice **32** (architecture, extending, CLAUDE Key Files)
- [x] `docs/plan/slices/PROGRESS.md` decision log row added
- [x] `./scripts/quality-gates.sh --quick` passed (2026-07-25)

**Delegated to [Slice 32B](SLICE-32B-STORAGE-PROTOCOL-GATE-CLOSURE.md)** (do not tick COMPLETE here until 32B passes):

- [ ] Branch coverage: 100% target on new modules; exclusions documented → **32B**
- [ ] Mutation testing (or explicit waiver) → **32B**
- [ ] `./scripts/quality-gates.sh` (full) passes → **32B**
- [ ] `/nw-review` APPROVED → **32B**
- [ ] Gate-evidence + tracker COMPLETE for Slice 32 → **32B**

## Gate Status

🔨 IN PROGRESS — implementation + GWT/acceptance tests + docs + quick gates green (2026-07-25). Remaining verification/governance gates owned by **Slice 32B**.
