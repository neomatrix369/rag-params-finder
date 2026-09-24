# SLICE 49 — Vector-Store Port Split + Registry (no Elasticsearch code)

**MoSCoW:** MUST
**Target time:** ~4–6 h
**Status:** 📋 PLANNED
**Depends on:** 32 (Storage + Retriever ports on `main`), 33–38 (Mongo + Postgres adapters, dual-backend cutover pattern)
**Branch:** `slice/49-vector-store-port-split-registry`
**Feature:** Elasticsearch vector-store adapter (Elasticsearch = ADR-006; ES code lands in Slice 50)

> **Renumber note (2026-09-24):** This is the pasted spec's "Slice 48". Slice 48 (48A–48D) is already the merged DoubleWord embedder work (PR #187/#188) and `ADR-005` is already the DoubleWord ADR. The Elasticsearch feature is therefore **Slices 49–51** (49 port-split → 50 adapter → 51 operability+CI+docs+ADR closeout, after the 51+52 merge #218) and its ADR is **ADR-006** — DECISIONS #213/#214.

---

## Context

Seam-only refactor that turns "two hard-coded stores" into "a registry of vector-store adapters", so a third store (Elasticsearch, Slice 50) is one manifest entry instead of four script/branch edits. Produces the `VectorStoreAdapter` protocol + `VectorCapabilities`, a static provider→class registry with lazy import, and the `VECTOR_STORE_BACKEND` setting that lets a vector store be selected independently of the run-state store (D1). **No Elasticsearch code and zero behaviour change** for Mongo/Postgres.

- **Depends-on outputs:** `StorageBackend` + `RetrieverBackend` ports (`server/db/ports/*.py`) and both live adapters exist on `main`; the four-value `storage_mode` + config↔engine 422 guard from Slices 36–38 are the branching this slice relocates.
- **Invariants pointer:** `docs/plan/invariants.md` — default store stays `mongodb` permanently (DECISIONS #130); public factory names `get_storage_backend()` / `get_retriever_backend()` are patched by tests and must not change signature.

## Non-goals

- Any Elasticsearch module, config model, mapping, retrieval, Docker profile, or docs (all → Slice 50+).
- Changing the default store or the run-state store selection semantics (DECISIONS #130 — default `mongodb`).
- Splitting `StorageBackend`'s ~28 methods into smaller ports (Interface-Segregation deferral is out of scope; keep the compatibility intersection).
- Frontend store-selection UI (dashboard stays a read-only observer).
- Touching `cli/indexes_cmd.py`'s thin-client leak (fixed via `GET /api/stores` in Slice 51).

## Output contract

- A `VectorStoreAdapter` Protocol and a `VectorCapabilities` value object (retrieval methods, similarity, index types, supported dims, metadata-filter support, `can_host_run_state`), importable from a single owner module.
- A static registry: `provider (str) → "module:Class"` resolved by lazy import, consumed by `get_storage_backend()` / `get_retriever_backend()` (names + signatures unchanged).
- A `VECTOR_STORE_BACKEND` setting that defaults to `STORAGE_BACKEND`; `elasticsearch` is a *valid value only for `VECTOR_STORE_BACKEND`* (rejected for `STORAGE_BACKEND` since ES cannot host run state).
- `grep -rE '== *"(mongodb|postgres)"' server/` returns **only** hits inside the adapters, the registry, and `settings.py`/`config.py` normalisers — no store-string branching in `health_check.py`, `search_index_guard.py`, `config_backend_guard.py`, or `main.py`.

### Protocol scope — required vs delegated (resolves nw-solution-architect C1/C4)

The `VectorStoreAdapter` **required** surface is the vector-store operations only: `health`, `storage_mode`, `plan_indexes`, `ensure_indexes`, `upsert_chunks`, `search`, `delete_experiment`, `stats`, `labels`, `capabilities`. **Reuse, not redefine (per "reuse what we have"):** `search` is the *existing* `RetrieverBackend.search` signature — the adapter **composes** `RetrieverBackend` rather than declaring a second search contract; the chunk/stat methods reuse the shapes already documented on `StorageBackend` (`insert_chunks`/`delete_chunks_for_experiment`/`get_*_db_stats`). `VectorStoreAdapter` is therefore a thin *lifecycle + capabilities* protocol over the two ports we already ship, not a parallel API. Run-state CRUD (experiment/run/result methods on today's `StorageBackend`) is **not** part of this protocol — it is answered by the **run-state store** (`get_storage_backend()` continues to return a full `StorageBackend` for Mongo/Postgres). The compatibility intersection stands: Mongo/Postgres adapters implement both the run-state `StorageBackend` and the `VectorStoreAdapter` surface; a vector-only adapter (ES, Slice 50) implements **only** `VectorStoreAdapter` and declares `capabilities.can_host_run_state = False`. Splitting the two into separate protocol files is a **Non-goal** here (documented above) — `can_host_run_state` is the lighter-weight seam that removes the ambiguity without an ADR.

- **`storage_mode()` for a vector-only adapter** describes the *vector store's* location, e.g. `("elasticsearch", "local"|"cloud")` — it never reports the run-state store. `health_check.py` probes the active vector store via `adapter.storage_mode()` + `adapter.health()`; the run-state store's health is checked separately through its own adapter, and `/healthz` reports both when they differ (D1 two-store setup).
- **Capabilities-driven preflight (replaces engine `if`):** `search_index_plan.py` reads `capabilities()` — `can_host_run_state`, `supported_dims`, `retrieval_methods` — to decide required objects, instead of branching on the backend string. Example: `capabilities.supported_dims = {384, 1024}` makes a config requesting SPLADE 30522-dim fail preflight with a dims-mismatch error, with no engine `if` (Slice 50 wires the ES capability values).
- **D2 clarified (correcting a review misread):** `elasticsearch` **is** a valid YAML `database_provider` *when it is the active vector store* — it is the "Vector Database" sweep dimension. The `config_backend_guard` raises 422 only on a **mismatch** between the YAML `database_provider` and the active `VECTOR_STORE_BACKEND` (keeping today's semantics + the `supabase→postgres` alias). Slice 50 adds `elasticsearch` to the `DatabaseProvider` Literal.
- **D1/D5 independence (resolves C3):** `STORAGE_BACKEND` (run state) and `VECTOR_STORE_BACKEND` (vectors) are **independently selectable via env**; nothing at settings-validation time forces a pairing. The `--elasticsearch-local` flag (Slice 51) *conveniences* the pairing by also starting `postgres-local`, overridable via `STORAGE_BACKEND` — a UX default, **not** a validation constraint.

## Reuse ledger (reuse-first — don't reinvent the wheel)

Reuse-first order: **reuse → extend → extract → write new (last)**. This slice is ~80% reuse/extend of existing seams; net-new is only the registry + capabilities value object.

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Search contract | `RetrieverBackend.search` — `server/db/ports/retriever_backend.py` | **Reuse** — adapter composes it; no second search API |
| Chunk/stat/CRUD shapes | `StorageBackend` — `server/db/ports/storage.py` (28 methods, documented shapes) | **Reuse** as the compatibility intersection; unchanged |
| Backend normalisation + known-set | `normalize_storage_backend`, `_KNOWN_STORAGE_BACKENDS` — `server/settings.py:24,27` | **Extend** → `_KNOWN_VECTOR_STORE_BACKENDS = _KNOWN_STORAGE_BACKENDS \| {"elasticsearch"}` |
| Provider alias (supabase→postgres) | `normalize_database_provider` — `server/models/config.py:16` | **Reuse** unchanged inside the D2 guard |
| Lazy per-backend import | The existing `if/elif` in `store_factory.py:28–38,49–59` already imports adapters at call time | **Extract** the same pattern into a table-driven `registry.py` (behaviour identical) |
| Four-value storage_mode | `resolve_storage_mode` / `mongodb_storage_mode` / `postgres_storage_mode` (guards + `*_uri.py`) | **Move** the engine branch into `adapter.storage_mode()` |
| Backend-agnostic stats assembly | `server/db/ports/stats_common.py` | **Reuse** — already backend-neutral |
| Live contract fixture | `tests/contract/test_storage_backend_contract.py`, `tests/helpers/storage_live.py` | **Reuse** — registry-parametrised (ES joins in Slice 50) |
| **Net-new (only)** | `server/db/ports/vector_store.py` (thin protocol), `registry.py`, `VectorCapabilities` dataclass, `VECTOR_STORE_BACKEND` setting | Write new — smallest surface that removes the four-place branching |

---

## Slice Workflow Bundle

- Slice name: `slice-49-vector-store-port-split-registry`
- Branch: `slice/49-vector-store-port-split-registry`
- Files (expected):
  - `server/db/ports/vector_store.py` — **new**: `VectorStoreAdapter` Protocol + `VectorCapabilities` dataclass. Lifecycle surface: `health`, `storage_mode`, `plan_indexes`, `ensure_indexes`, `upsert_chunks`, `search`, `delete_experiment`, `stats`, `labels`, `capabilities`.
  - `server/db/ports/registry.py` — **new**: static `_VECTOR_STORE_REGISTRY: dict[str, str]` (`"mongodb": "server.db.mongo.mongo_store:MongoStorageBackend"`, `"postgres": "server.db.postgres.postgres_store:PostgresStorageBackend"`) + `resolve_adapter(provider)` lazy importer + `known_vector_stores()`.
  - `server/db/ports/store_factory.py` — **edit**: `get_storage_backend()` / `get_retriever_backend()` delegate to the registry; **public names + signatures unchanged** (tests patch these).
  - `server/settings.py` — **edit**: add `vector_store_backend: str` (default falls back to `storage_backend`); `_KNOWN_VECTOR_STORE_BACKENDS = _KNOWN_STORAGE_BACKENDS | {"elasticsearch"}`; validator rejects `elasticsearch` for `storage_backend` (run-state) but accepts it for `vector_store_backend`.
  - `server/models/config.py` — **edit** (D2): `database_provider` guard asserts against the **vector** store; keep `supabase`→`postgres` alias + today's 422 semantics.
  - `server/core/guards/health_check.py`, `server/core/guards/search_index_guard.py`, `server/core/guards/config_backend_guard.py`, `server/main.py` — **edit**: replace `== "mongodb"` / `== "postgres"` branches with calls to adapter methods (`storage_mode()`, `plan_indexes()`, `capabilities()`).
  - `server/core/guards/search_index_plan.py` — **edit**: required-object planning becomes a `capabilities()`-driven lookup rather than an engine `if`.
  - Tests (RED first): `tests/server/db/ports/test_registry.py`, `tests/server/db/ports/test_vector_capabilities.py`, `tests/server/test_vector_store_backend_setting.py`, plus a `grep`-guard test asserting no store-string branching outside adapters/registry/settings.
- Exit criteria: existing Mongo + Postgres contract, unit, and nightly suites green with **zero behaviour change**; the grep-guard test passes; `VECTOR_STORE_BACKEND` selectable and defaulting correctly; `elasticsearch` accepted only for the vector store.
- Commit pattern: `refactor(storage): vector-store adapter protocol + registry; VECTOR_STORE_BACKEND (no ES code)`
- **Doc exit (Must):** `docs/contributor-guide/extending.md` gains the "add a vector store = one registry entry" flow (full 15-stage journey requirement deferred to Slice 51); CHANGELOG + PROGRESS/TRAIL.

---

## Goal

Introduce the adapter seam that makes a new vector store a registry entry, not a scatter of `if backend == …` edits — while proving, by contract + grep, that Mongo and Postgres behave exactly as before. This is the "skateboard" of the Elasticsearch feature: a complete, shippable refactor that delivers value (removes the four-place branching debt the pasted spec's Repo Facts call out) even if no ES code ever follows.

**Capabilities model (why `VectorCapabilities`):** the current preflight (`search_index_plan.py` / `search_index_guard.py`) branches on engine to decide which indexes/objects are required. Elasticsearch will reject unsupported dims (e.g. SPLADE 30522) at preflight (D4) — that decision belongs to the adapter's declared capabilities, not to a growing engine `if`. Moving the branch now (against two known-good backends) is the safe, testable moment.

---

## Spec (GWT)

```
Scenario: Registry resolves the configured vector store by lazy import
  Given VECTOR_STORE_BACKEND is unset and STORAGE_BACKEND=mongodb
  When get_storage_backend() is called
  Then the registry lazily imports the Mongo adapter class
    And neither psycopg nor any Elasticsearch client module is imported
    And the returned object satisfies the StorageBackend Protocol

Scenario: Vector store selectable independently of run state (D1)
  Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND=elasticsearch
  When settings load
  Then VECTOR_STORE_BACKEND resolves to "elasticsearch"
    And the run-state store resolves to "postgres"
    And no error is raised (ES is a valid vector store)

Scenario: elasticsearch is rejected as a run-state store
  Given STORAGE_BACKEND=elasticsearch
  When settings validate
  Then a clear error names elasticsearch as vector-store-only
    And instructs setting STORAGE_BACKEND to mongodb or postgres

Scenario: VECTOR_STORE_BACKEND defaults to STORAGE_BACKEND
  Given STORAGE_BACKEND=postgres and VECTOR_STORE_BACKEND unset
  When settings load
  Then the active vector store is "postgres"
    (no behaviour change for existing single-store deployments)

Scenario: Config guard asserts against the vector store (D2)
  Given VECTOR_STORE_BACKEND=postgres and a YAML with database_provider: mongodb
  When the config-backend guard runs
  Then it raises HTTP 422 (config↔vector-store engine mismatch)
    And the supabase→postgres alias still normalises before the check

Scenario: No store-string branching leaks outside the adapters/registry/settings
  Given the server package
  When grep -rE '== *"(mongodb|postgres)"' server/ runs
  Then every hit is inside an adapter module, registry.py, settings.py, or config.py
    And health_check.py, search_index_guard.py, config_backend_guard.py, main.py have none

Scenario: Mongo and Postgres contract suites unchanged
  Given the registry-driven factory
  When tests/contract/test_storage_backend_contract.py runs against both stores
  Then every case passes exactly as on main (zero behaviour change)

Scenario: Unknown vector store is rejected with guidance
  Given VECTOR_STORE_BACKEND=unknown
  When the registry resolves the adapter
  Then a clear error names the value and lists the known vector stores
    (registry entry that points at a non-existent class fails the same way)
```

*(Full GWT → step-definition scaffold authored in the AT-design pass — `nw-distill`; each scenario above maps to ≥1 executable test named in the Files list. **PBT/parametrize handoff for `nw-distill`:** parametrize the independent-selection scenario over `(STORAGE_BACKEND, VECTOR_STORE_BACKEND)` pairs, and the grep/behaviour guard over the four guard modules — see the acceptance-designer parametrize table. Business-language reframing of the intentionally-precise scenarios (lazy-import, grep-guard, `(1+cos)/2`, RRF) is deferred to the step-definition pass — these name the observable contract and are kept exact at planning time.)*

---

## Before-Checks [GATE]

- [ ] Slices 32–38 ✅ COMPLETE on `main` with both adapters live (ports + Mongo + Postgres).
- [ ] Contract suite `tests/contract/test_storage_backend_contract.py` green on `main` for both stores (baseline snapshot recorded).
- [ ] `grep -rncE '== *"(mongodb|postgres)"' server/` baseline captured (the exact call sites this slice must relocate).
- [ ] harness-scout `detect_confirm` run at slice start (seam refactor across guards + factory — blast-radius review).

## After-Checks [GATE]

- [ ] Specification coverage: every GWT clause has ≥1 test (BDD/GWT-first); grep-guard test present and green.
- [ ] Complexity evidence: policy `enforcing` (xenon E/C/C on `server/`/`cli/` via `./scripts/ci/quality-gates.sh`); local `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`; new modules do not raise average rank.
- [ ] Branch coverage: meets backend floors (DECISIONS #142 — `fail_under=70` combined + per-metric checker); new port/registry modules covered.
- [ ] Zero behaviour change: Mongo + Postgres contract + unit + nightly suites green; diff shows no functional edit to adapter query logic.
- [ ] Guard **behavioural** contract suite (not just the grep-guard syntax check): `health_check.py`, `search_index_guard.py`, `config_backend_guard.py` exercised against both Mongo and Postgres adapters, asserting identical output dict shapes / accept-reject decisions before vs after the refactor (resolves nw-solution-architect high finding).
- [ ] Mutation: waive with DECISIONS row unless non-trivial new branching logic added (registry resolution is a candidate — run feature-scoped Stryker/mutmut on `registry.py`).
- [ ] `docs/plan/gate-evidence/slice-49.json` written by executor with `coverage_pct`, `branch_pct`, `coverage_target`, `complexity_tool`, `complexity_ceiling`, `complexity_passed`.

---

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9, parallel): adapter-protocol boundary contracts + registry as SSOT for store selection; no new SPOF in lazy import
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED — spec drafted; awaiting nw-reviewer sign-off then AT authoring (`nw-distill`) before 🔨 IN PROGRESS.
