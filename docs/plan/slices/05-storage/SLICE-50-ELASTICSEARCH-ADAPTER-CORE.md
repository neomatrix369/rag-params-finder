# SLICE 50 — Elasticsearch Adapter Core

**MoSCoW:** MUST
**Target time:** ~6–8 h
**Status:** 📋 PLANNED
**Depends on:** 49 (`VectorStoreAdapter` protocol + registry + `VECTOR_STORE_BACKEND`)
**Branch:** `slice/50-elasticsearch-adapter-core`
**Feature:** Elasticsearch vector-store adapter (ADR-006)

> Pasted spec's "Slice 49". Renumbered per DECISIONS #213.

---

## Context

The greenfield Elasticsearch adapter: a `server/db/elasticsearch/` package + a retrieval module that satisfy `VectorStoreAdapter` (Slice 49) with **full parity** to Mongo/Postgres on dense, sparse, and hybrid retrieval — registered as one manifest entry. ES is a **vector-only** store (D1); run state stays on Mongo/Postgres. Optional extra `[elasticsearch]` with lazy import.

- **Depends-on outputs:** the registry + capabilities seam from Slice 49; the `(1+cos)/2` score scale and RRF `k=60` fusion already implemented for Mongo/Postgres (shared, not duplicated).
- **Invariants pointer:** `docs/plan/invariants.md` — `embedding_model` filter mandatory on every query (+ `experiment_id`, `run_id`); Basic-licence only; unquantized HNSW; `git clone && pip install -e .` must still work with ES absent.

## Non-goals

- Docker profile, `start-services.sh` flags, `GET /api/stores`, CLI/frontend surfaces, example configs (all → Slice 51).
- CI job, `elasticsearch-setup.md`, ADR-006 authoring (→ Slice 51).
- Server-side `rrf`/`linear` retrievers (Platinum — never; hybrid is client-side RRF, D3).
- Any new dependency beyond `elasticsearch>=9,<10`.

## Output contract

- `server/db/elasticsearch/` package: config model, local-vs-cloud URI classification, single-index mapping creation (explicit `index_options.type: "hnsw"`, `cosine`, keyword filter fields, `english` analyzer), idempotent `ensure_indexes`, and a preflight that **fails if the live mapping is quantized** (`bbq_hnsw`/`int8_hnsw`).
- Single index `rpf-chunks` (prefix configurable) with per-dimension fields `embedding_384` / `embedding_1024` (D4), mirroring pgvector's `VECTOR_COLUMNS`. Add `elasticsearch` to the `DatabaseProvider` Literal in `server/models/config.py` (it is a valid vector-store sweep dimension; the D2 guard from Slice 49 matches it to the active `VECTOR_STORE_BACKEND`).
- **Explicit mapping** (data-eng review): `dense_vector` fields set `index_options.type: "hnsw"`, `similarity: "cosine"`, and the ES 9.5 defaults **stated explicitly** (`m: 16`, `ef_construction: 100`) so a future default change can't silently drift; `text` field uses the `english` analyzer; `experiment_id`/`embedding_model`/`run_id` are `keyword`. Ship an `index_mapping.json` template (or an in-code builder) beside the adapter as the SSOT for the shape.
- **Preflight detection method** (data-eng review): `GET /{index}/_mapping` → read each `dense_vector` field's `index_options.type`; **reject** if any is `bbq_hnsw` or `int8_hnsw` with a clear "unquantized HNSW required" remediation.
- **Sizing note** (data-eng review, for `elasticsearch-setup.md` in Slice 51): raw float32 vectors on disk (≈1.5 KB/384-d, ≈4 KB/1024-d) + HNSW graph in memory (≈`8 × m × 4` bytes/chunk ≈ 512 B/chunk at `m=16`); `-Xms1g -Xmx1g` for local testing.
- **`capabilities()` (data-eng review — Suggestion-2):** returns `VectorCapabilities(retrieval_methods=[dense, sparse, hybrid], similarity="cosine", index_types=["hnsw"], supported_dims={384, 1024}, metadata_filtering=True, can_host_run_state=False)`. `supported_dims` mirrors pgvector's `VECTOR_COLUMNS` — a config requesting a dim outside it (e.g. SPLADE 30522) is rejected at preflight via this value, not deep in a query.
- `search()`: dense `knn` (`k=top_k`, `num_candidates=top_k*2`, filters in `knn.filter` for **pre**-filtering), sparse BM25 `match` with the same filters, hybrid = **client-side RRF (k=60)** via a shared fusion helper (extracted, not copied from `retriever_mongo.py`).
- `upsert_chunks` refreshes before returning (`refresh="wait_for"`, **not** `refresh=true` — serialises the immediate follow-up search); `delete_experiment` via delete-by-query.
- **Dual-store error precedence (data-eng review — Suggestion-3):** when both the vector store and run-state store are checked in preflight, the **vector-store (ES) failure gates the sweep and is reported first**; a run-state failure is secondary. Recorded in ADR-006 (Slice 51).
- Missing `elasticsearch` client raises a clear "install the `[elasticsearch]` extra" error **only when ES is selected**.

## Reuse ledger (reuse-first — don't reinvent the wheel)

The ES adapter is net-new code, but its *behaviour* is composed from patterns and constants the repo already proves for Mongo/Postgres — never re-derived.

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Dense score scale `(1+cos)/2` | Normalisation in `server/core/retrieval/retriever_postgres.py` | **Reuse** the exact formula/constant — assert parity, don't re-derive |
| `num_candidates = top_k×2` | `_CANDIDATES_MULTIPLIER = 2` — `retriever_postgres.py` | **Reuse** the constant |
| RRF fusion `k=60` | `_RRF_K = 60` + fusion loop — `server/core/retrieval/retriever_mongo.py` | **Extract** a shared `rrf_fuse()` helper; Mongo + ES both call it (delete the inlined copy) |
| Per-dimension field layout | `VECTOR_COLUMNS = {384, 1024}` — `server/db/postgres/postgres_docs.py` | **Mirror** as ES `embedding_384`/`embedding_1024` fields |
| Mandatory 3-filter isolation | `WHERE embedding_model/experiment_id/run_id` (`retriever_postgres.py`) + `$vectorSearch` filter (`retriever_mongo.py`) | **Reuse** the same filter set in `knn.filter` |
| Return type | `SearchResult` — `server/models/results.py` | **Reuse** — adapter returns the existing model |
| `RetrieverBackend.search` signature | `server/db/ports/retriever_backend.py` | **Reuse** (Slice 49 composition) — no new search shape |
| Config model + provider Literal | `server/models/config.py` | **Extend** `DatabaseProvider` with `elasticsearch` |
| Live contract fixture | `tests/contract/test_storage_backend_contract.py`, `tests/helpers/storage_live.py` | **Reuse** — add ES to the registry-parametrised fixture |
| **Net-new (only)** | `server/db/elasticsearch/` package (config/URI/mapping/ensure/preflight/upsert/delete), `rrf_fuse()` extraction, `[elasticsearch]` extra | Write new — the ES-specific I/O only |

---

## Spec (GWT)

```
Scenario: Dense score is on the shared (1+cos)/2 scale
  Given a chunk indexed with a known embedding
  When a dense knn query retrieves it
  Then the returned score equals (1 + cosine)/2 within tolerance
    (comparable to Mongo/Postgres — no conversion applied)

Scenario: embedding_model isolation
  Given chunks from two embedding models sharing one rpf-chunks index
  When a query filters embedding_model=A
  Then only model-A chunks are returned (never model-B vectors)

Scenario: run_id and experiment_id filtering
  Given chunks across two runs of one experiment
  When search runs with a specific run_id
  Then results are confined to that run

Scenario: top_k bound and score ordering
  Given more than top_k matching chunks
  When search runs
  Then exactly top_k are returned, descending by score

Scenario: Hybrid RRF parity with Mongo on a fixed fixture
  Given the shared RRF fusion helper (k=60) and a fixed dual-list fixture
  When ES hybrid fuses dense + sparse
  Then the fused ranking matches Mongo's on the same fixture

Scenario: Extracted RRF helper is the single fusion path (extraction regression)
  Given rrf_fuse() extracted to a shared module (Mongo's inlined copy deleted)
  When Mongo hybrid retrieval runs on the fixed dual-list fixture
  Then its output is unchanged from before the extraction
    (Mongo now routes through the shared helper — no duplicate fusion logic remains)

Scenario: Insert-then-immediately-search returns hits (refresh regression)
  Given upsert_chunks has just returned
  When search runs immediately (no manual refresh)
  Then the freshly indexed chunks are found (Recall > 0)

Scenario: ensure_indexes is idempotent
  Given the rpf-chunks index already exists with the correct mapping
  When ensure_indexes runs again
  Then no error is raised and the mapping is unchanged

Scenario: Quantized mapping is rejected at preflight
  Given a rpf-chunks index whose dense_vector uses bbq_hnsw or int8_hnsw
    (the test fixture pre-creates the index with a quantized mapping via the ES API before preflight runs)
  When preflight runs
  Then it fails with a clear "unquantized HNSW required" remediation
    (scores would otherwise degrade for reasons unrelated to the sweep)

Scenario: Sparse BM25 retrieval with the mandatory filters
  Given chunks indexed with text and the three filter fields
  When a sparse (BM25 match) query runs with embedding_model + experiment_id + run_id
  Then only matching in-scope chunks are returned, ranked by BM25 score

Scenario: delete_experiment removes only that experiment's chunks
  Given chunks from two experiments in rpf-chunks
  When delete_experiment runs for one (delete-by-query)
  Then only that experiment's chunks are gone; the other's remain

Scenario: Dimension mismatch is rejected
  Given rpf-chunks with an embedding_384 field
  When a query supplies a 1024-dim vector (or a config requests an unsupported dim, e.g. SPLADE 30522)
  Then it is rejected with a clear dims-mismatch remediation (capabilities.supported_dims)

Scenario: Invalid top_k is rejected
  Given a search request with top_k <= 0
  When search runs
  Then it fails fast with a clear validation error (no ES round-trip)

Scenario: Elasticsearch unreachable surfaces a clear error
  Given VECTOR_STORE_BACKEND=elasticsearch and ES is down/timing out
  When search or ensure_indexes runs
  Then a clear connection error is raised (not a silent empty result)

Scenario: Dual-store preflight validates both stores (resolves nw-solution-architect high)
  Given STORAGE_BACKEND=postgres (run state) and VECTOR_STORE_BACKEND=elasticsearch (vectors)
  When preflight runs before a sweep
  Then it ensures the Postgres run-state objects exist
    And the ES rpf-chunks mapping is present and unquantized
    And both adapters report health=ok (error precedence documented)

Scenario: ES client missing raises install guidance
  Given the elasticsearch extra is not installed and VECTOR_STORE_BACKEND=elasticsearch
  When the adapter is resolved
  Then a clear "pip install -e .[elasticsearch]" error is raised
    And importing the server with a non-ES backend never imports the client
```

*(Contract cases added to the registry-parametrised fixture: skip locally when ES unreachable; `RAG_REQUIRE_ELASTICSEARCH=1` fails in CI — mirrors `tests/helpers/storage_live.py`. Coverage gate for ES retrieval = 95%, matching Postgres retrieval. **PBT/parametrize handoff for `nw-distill`:** top_k ∈ {1,10,100,1000}; `(embedding_model_A, embedding_model_B)` isolation pairs; quantization types {bbq_hnsw, int8_hnsw}; `@hypothesis`-generated embeddings for the score-scale + RRF-parity scenarios. Business-language reframing of the precise scenarios — the `(1+cos)/2` scale is the observable cross-backend contract from Slice 38 — is deferred to the step-definition pass.)*

---

## Before-Checks [GATE]
- [ ] Slice 49 ✅ COMPLETE (registry + capabilities + `VECTOR_STORE_BACKEND` on `main` or the working branch).
- [ ] Local ES 9.5.x reachable for live contract cases (or documented skip); `elasticsearch>=9,<10` added to `[elasticsearch]` extra only.
- [ ] harness-scout `detect_confirm` at slice start (external service integration + near-real-time refresh seam).

## After-Checks [GATE]
- [ ] Every GWT clause has ≥1 test; refresh regression + quantized-preflight rejection explicitly present.
- [ ] ES retrieval coverage ≥95% (matches Postgres retrieval floor); combined backend floors hold.
- [ ] Complexity `enforcing`; new ES modules do not raise average xenon rank.
- [ ] `pip install -e .` (no extra) still imports server + runs the non-ES suites — ES import stays lazy.
- [ ] Mutation on the ES retrieval + fusion helper: survival budget met or waiver logged.
- [ ] `docs/plan/gate-evidence/slice-50.json` with coverage/complexity fields.

### Closing Gates
- [ ] `nw-at-completeness-check` — AT completeness audit (gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline (gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9, parallel): dense/sparse/hybrid transforms, refresh-before-return correctness, shared-fusion SSOT
- [ ] `nw-data-engineer-reviewer` — mapping/index design, HNSW params, dims layout, filter pre-filtering
- [ ] `nw-gate-evidence-validator` — 9 conditions pass
- [ ] `/verify-slice` — verdict COMPLETE

## Gate Status
📋 PLANNED — depends on Slice 49 sign-off; AT authoring (`nw-distill`) before 🔨 IN PROGRESS.
