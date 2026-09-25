# SLICE 49A — Vector-Store Port + Registry Seam (no Elasticsearch code, zero behaviour change)

**MoSCoW:** MUST
**Target time:** ~4–6 h
**Status:** 📋 PLANNED
**Depends on:** 32 (Storage + Retriever ports on `main`), 33–38 (Mongo + Postgres adapters, dual-backend cutover pattern)
**Branch:** `slice/49a-vector-store-port-registry`
**Feature:** Elasticsearch vector-store adapter (Elasticsearch = ADR-006; ES code lands in Slice 50)
**Next:** [49B — split-store data-path rewire](SLICE-49B-VECTOR-STORE-DATA-PATH-REWIRE.md)

> **Renumber note (2026-09-24):** This is the pasted spec's "Slice 48". Slice 48 (48A–48D) is already the merged DoubleWord embedder work (PR #187/#188) and `ADR-005` is already the DoubleWord ADR. The Elasticsearch feature is therefore **Slices 49–51** and its ADR is **ADR-006** — DECISIONS #213/#214.
>
> **Split note (2026-09-25, DECISIONS #240/#242):** an end-to-end desk-check against `main @ 59281f3` found that the original Slice 49 added a vector-store port but never pointed the chunk data path at it. In a split setup (vectors in ES, run state in Postgres/Mongo) every sweep would finish COMPLETE with empty results. Slice 49 is now **49A** (this file: port, registry, factory, both stores locked equal) and **49B** (rewire the data path, split-store E2E test, relax the lock to pairing rule (ii)). The filename is kept so existing links resolve.

---

## Context

Seam-only refactor that turns "two hard-coded stores" into "a registry of vector stores", so a third store (Elasticsearch, Slice 50) is one registry entry. Produces the `VectorStore` port + `VectorCapabilities`, a static provider→class registry with lazy import, a `get_vector_store()` factory, and the `VECTOR_STORE_BACKEND` setting. In this slice the validator **locks `VECTOR_STORE_BACKEND == STORAGE_BACKEND`**, so no split setup can exist yet and Mongo/Postgres behaviour is byte-identical (proven by characterization tests written first).

- **Depends-on outputs:** `StorageBackend` + `RetrieverBackend` ports (`server/db/ports/*.py`) and both live adapters exist on `main`; the four-value `storage_mode` + config↔engine 422 guard from Slices 36–38 are the branching this slice relocates.
- **Invariants pointer:** `docs/plan/invariants.md` § Vector store / split-store — default store stays `mongodb` permanently (DECISIONS #130); public factory names `get_storage_backend()` / `get_retriever_backend()` are patched by tests and must not change signature.

## Non-goals

- Rewiring chunk write / delete / stats / preflight / health call sites onto the vector port (→ **49B**).
- Allowing `VECTOR_STORE_BACKEND != STORAGE_BACKEND` (→ **49B**, pairing rule (ii)).
- Any Elasticsearch module, config model, mapping, retrieval, Docker profile, or docs (→ Slice 50+).
- Changing the default store (DECISIONS #130 — default `mongodb`).
- Splitting `StorageBackend`'s run-state methods into smaller ports.
- Frontend store-selection UI (dashboard stays a read-only observer).
- `cli/indexes_cmd.py`'s thin-client leak (fixed via `GET /api/stores` in Slice 51).

## Output contract

- A `VectorStore` Protocol and a `VectorCapabilities` value object (retrieval methods, similarity, index types, supported dims, metadata-filter support, `can_host_run_state`), importable from one owner module (`server/db/ports/vector_store.py`).
- **One port per operation (DECISIONS #240):** `VectorStore` owns chunk write, chunk delete, chunk stats, search (via `retriever()`), index plan/ensure, health, `storage_mode`, labels and capabilities. `StorageBackend` keeps run state (experiments, runs, results, reconciliation). Its chunk methods stay in 49A (callers move in 49B) and are marked deprecated.
- **Composite adapters, not the run-state classes:** the registry maps `"mongodb"` → `server.db.mongo.mongo_vector_store:MongoVectorStore` and `"postgres"` → `server.db.postgres.postgres_vector_store:PostgresVectorStore`. Each is composed from what already exists — the store's chunk methods, the matching `*RetrieverBackend`, index bootstrap, and the chunk half of the stats modules. (The original draft mapped `"mongodb"` to `MongoStorageBackend`, which has no `search`; the retriever is the separate `MongoRetrieverBackend`, `mongo_store.py:297-300`.)
- **Factories:** new `get_vector_store()` reads `VECTOR_STORE_BACKEND` (default `STORAGE_BACKEND`). `get_retriever_backend()` becomes `get_vector_store().retriever()` — **same name and signature**. `get_storage_backend()` keeps reading `STORAGE_BACKEND`.
- **Settings:** `vector_store_backend` defaults to `storage_backend`; `_KNOWN_VECTOR_STORE_BACKENDS = _KNOWN_STORAGE_BACKENDS | {"elasticsearch"}`; `elasticsearch` is rejected for `STORAGE_BACKEND` (cannot host run state). **49A lock:** any value of `VECTOR_STORE_BACKEND` different from `STORAGE_BACKEND` is rejected with "split stores arrive in Slice 49B". 49B replaces the lock with pairing rule (ii) (DECISIONS #241).
- **One `DatabaseProvider` Literal:** delete the duplicate in `server/models/status.py:10` and import the one from `server/models/config.py:13`.
- **Guards read the port, not the string:** `health_check.py`, `search_index_guard.py`, `search_index_plan.py`, `config_backend_guard.py` and `main.py` call `storage_mode()`, `plan_indexes()`, `capabilities()` on the active `VectorStore` instead of `== "mongodb"` / `== "postgres"`.
- **Hardened store-string guard (AST, not grep):** a test walks `server/` **and `cli/`** and fails on any comparison of a store name — `==`, `!=`, `in {…}` / `in (…)`, `match` cases — outside the adapters, `registry.py`, `settings.py` and `config.py` normalisers. The original `grep '== *"…"'` missed `!=`, set membership and the whole CLI.

### D2 (unchanged, clarified)

`elasticsearch` **is** a valid YAML `database_provider` when it is the active vector store — it is the "Vector Database" sweep dimension. `config_backend_guard` raises 422 only on a **mismatch** between the YAML `database_provider` and the active `VECTOR_STORE_BACKEND` (keeping today's semantics + the `supabase→postgres` alias). Slice 50 adds `elasticsearch` to the single `DatabaseProvider` Literal.

### Pairing (superseded)

The earlier "D1/D5 independence — nothing forces a pairing" clause is **superseded by DECISIONS #241** (pairing rule (ii)): `schema.sql:29,44,84` FKs `results`/`chunks`/`run_status` to `experiments`, so Mongo run state + Postgres vectors would fail. In 49A both stores are locked equal; 49B introduces rule (ii).

## Reuse ledger (reuse-first — don't reinvent the wheel)

Reuse-first order: **reuse → extend → extract → write new (last)**. ~80% reuse/extend; net-new is the port file, the registry, two thin composites and the setting.

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Search contract | `RetrieverBackend.search` — `server/db/ports/retriever_backend.py` | **Reuse** — `VectorStore.retriever()` returns it; no second search API |
| Chunk write/delete shapes | `StorageBackend.insert_chunks` / `delete_chunks_for_experiment` — `server/db/ports/storage.py` | **Reuse** — composites delegate to the existing store methods |
| Mongo search | `MongoRetrieverBackend` — `mongo_store.py:297-300` | **Compose** into `MongoVectorStore` |
| Postgres search | `PostgresRetrieverBackend` — `postgres_store.py` | **Compose** into `PostgresVectorStore` |
| Backend normalisation + known-set | `normalize_storage_backend`, `_KNOWN_STORAGE_BACKENDS` — `server/settings.py:24,27` | **Extend** → `_KNOWN_VECTOR_STORE_BACKENDS` |
| Provider alias (supabase→postgres) | `normalize_database_provider` — `server/models/config.py:16` | **Reuse** unchanged inside the D2 guard |
| Lazy per-backend import | `if/elif` in `store_factory.py:28–38,49–59` | **Extract** the same pattern into a table-driven `registry.py` |
| Four-value storage_mode | `resolve_storage_mode` / `mongodb_storage_mode` / `postgres_storage_mode` | **Move** the engine branch behind `VectorStore.storage_mode()` |
| Stats assembly | `server/db/ports/stats_common.py` | **Reuse** the neutral half; note: it is only **half** backend-neutral (`stats_common.py:105-112` falls back per provider) — the provider-specific part moves behind `VectorStore.stats()` |
| Live contract fixture | `tests/contract/test_storage_backend_contract.py` + `tests/helpers/storage_live.py` | **Reuse** — registry-parametrised (ES joins in Slice 50) |
| **Net-new (only)** | `server/db/ports/vector_store.py`, `server/db/ports/registry.py`, `mongo_vector_store.py`, `postgres_vector_store.py` (thin composites), `VECTOR_STORE_BACKEND` setting, AST guard test | Write new — smallest surface that removes the branching |

---

## Slice Workflow Bundle

- Slice name: `slice-49a-vector-store-port-registry`
- Branch: `slice/49a-vector-store-port-registry`
- Files (expected):
  - **RED first — characterization (golden) tests** for today's single-store behaviour: chunk write → search → delete → db-stats → `/healthz` → preflight on Mongo and Postgres, recorded **before** any refactor. These must stay byte-identical through 49A and 49B.
  - `server/db/ports/vector_store.py` — **new**: `VectorStore` Protocol + `VectorCapabilities` dataclass.
  - `server/db/ports/registry.py` — **new**: static `_VECTOR_STORE_REGISTRY: dict[str, str]` → composites; `resolve_adapter(provider)` lazy importer; `known_vector_stores()`.
  - `server/db/mongo/mongo_vector_store.py`, `server/db/postgres/postgres_vector_store.py` — **new, thin**: compose existing chunk methods + retriever + index bootstrap + chunk stats.
  - `server/db/ports/store_factory.py` — **edit**: add `get_vector_store()`; `get_retriever_backend()` → `get_vector_store().retriever()`; public names + signatures unchanged.
  - `server/settings.py` — **edit**: `vector_store_backend`, known-set, reject `elasticsearch` as run state, **49A equality lock**.
  - `server/models/status.py` — **edit**: drop the duplicate `DatabaseProvider` Literal.
  - `server/models/config.py`, `server/core/guards/{health_check,search_index_guard,search_index_plan,config_backend_guard}.py`, `server/main.py` — **edit**: read the port instead of the backend string.
  - Tests: `tests/server/db/ports/test_registry.py`, `tests/server/db/ports/test_vector_capabilities.py`, `tests/server/test_vector_store_backend_setting.py`, `tests/server/test_no_store_string_branching.py` (AST guard), guard behavioural suite.
- Exit criteria: characterization + contract + unit + nightly suites green with **zero behaviour change**; AST guard green; `VECTOR_STORE_BACKEND` defaults correctly and is locked equal; one `DatabaseProvider` Literal.
- Commit pattern: `refactor(storage): vector-store port + registry + get_vector_store (no ES code, stores locked equal)`
- **Doc exit (Must):** `docs/contributor-guide/extending.md` gains the "add a vector store = one registry entry" flow (the full 15-stage journey table and checklist land in Slice 51); `architecture.md` gains a ports/adapters diagram (C4 component view) showing `StorageBackend` and `VectorStore`; CHANGELOG + PROGRESS/TRAIL.

---

## Goal

Introduce the seam that makes a new vector store a registry entry, not a scatter of `if backend == …` edits — while proving, with characterization tests and the AST guard, that Mongo and Postgres behave exactly as before. This is the "skateboard": a complete, shippable refactor that removes today's branching debt even if no ES code ever follows.

**Capabilities model (why `VectorCapabilities`):** the current preflight branches on engine to decide which indexes/objects are required. Elasticsearch will reject unsupported dims (e.g. SPLADE 30522) at preflight (D4) — that decision belongs to the store's declared capabilities, not to a growing engine `if`.

---

## Spec (GWT)

```
Scenario: Registry resolves the configured vector store by lazy import
  Given VECTOR_STORE_BACKEND is unset and STORAGE_BACKEND=mongodb
  When get_vector_store() is called
  Then the registry lazily imports MongoVectorStore
    And neither psycopg nor any Elasticsearch client module is imported
    And the returned object satisfies the VectorStore Protocol, including retriever().search

Scenario: The retriever factory reads the vector store
  Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND unset
  When get_retriever_backend() is called
  Then it returns get_vector_store().retriever()
    And its name and signature are unchanged (existing test patches still apply)

Scenario: VECTOR_STORE_BACKEND defaults to STORAGE_BACKEND
  Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND unset
  When settings load
  Then the active vector store is "postgres"

Scenario: Split stores are locked out until Slice 49B
  Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND=mongodb (or elasticsearch)
  When settings validate
  Then a clear error says split stores arrive in Slice 49B
    And no sweep can start in a half-wired split setup

Scenario: elasticsearch is rejected as a run-state store
  Given STORAGE_BACKEND=elasticsearch
  When settings validate
  Then a clear error names elasticsearch as vector-store-only
    And instructs setting STORAGE_BACKEND to mongodb or postgres

Scenario: Config guard asserts against the vector store (D2)
  Given VECTOR_STORE_BACKEND=postgres and a YAML with database_provider: mongodb
  When the config-backend guard runs
  Then it raises HTTP 422 (config↔vector-store engine mismatch)
    And the supabase→postgres alias still normalises before the check

Scenario: One DatabaseProvider Literal
  Given the server package
  When RunStatus and ExperimentConfig are validated with each known provider
  Then both accept the same set, sourced from one Literal in server/models/config.py

Scenario: No store-string branching outside the adapters/registry/settings
  Given server/ and cli/
  When the AST guard runs
  Then no ==, !=, in-set or match comparison against a store name exists
    outside adapter modules, registry.py, settings.py and config.py

Scenario: Single-store behaviour is byte-identical (characterization)
  Given the golden records captured on main for Mongo and Postgres
  When the same ingest → query → delete → db-stats → /healthz → preflight flow runs after the refactor
  Then every recorded output matches exactly

Scenario: Unknown vector store is rejected with guidance
  Given VECTOR_STORE_BACKEND=unknown
  When the registry resolves the adapter
  Then a clear error names the value and lists the known vector stores
    (a registry entry that points at a non-existent class fails the same way)
```

*(PBT/parametrize handoff for `nw-distill`: parametrize the lock scenario over `(STORAGE_BACKEND, VECTOR_STORE_BACKEND)` pairs; the AST guard over each comparison form; the characterization flow over {mongodb, postgres}.)*

---

## Before-Checks [GATE]

- [ ] Slices 32–38 ✅ COMPLETE on `main` with both adapters live.
- [ ] Contract suite green on `main` for both stores (baseline snapshot recorded).
- [ ] Characterization golden records captured on `main` **before** the first refactor commit.
- [ ] Baseline of store-string comparisons in `server/` + `cli/` captured (the exact sites this slice must relocate).
- [ ] harness-scout `detect_confirm` run at slice start.

## After-Checks [GATE]

- [ ] Specification coverage: every GWT clause has ≥1 test; AST guard present and green.
- [ ] Characterization records unchanged (zero behaviour change) for Mongo + Postgres.
- [ ] Complexity evidence: policy `enforcing` (xenon E/C/C via `./scripts/ci/quality-gates.sh`); `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`.
- [ ] Branch coverage meets backend floors (DECISIONS #142); new port/registry modules covered.
- [ ] Guard behavioural suite: `health_check.py`, `search_index_guard.py`, `config_backend_guard.py` give identical output shapes / accept-reject decisions before vs after, for both stores.
- [ ] Mutation: feature-scoped run on `registry.py`, or waiver logged in DECISIONS.
- [ ] `docs/plan/gate-evidence/slice-49a.json` with coverage/complexity fields.

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline (gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` (gate #9, parallel): every operation on exactly one port; registry is the SSOT for store selection; reviewers cite file:line for each call site they checked (DECISIONS #240 — no stub-only approvals)
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — verdict COMPLETE

## Gate Status

📋 PLANNED — restructured 2026-09-25 after the round-3 desk-check (DECISIONS #240–#249); confirmation review pending before AT authoring (`nw-distill`).
