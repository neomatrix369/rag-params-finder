# SLICE 17 — Test Suite Expansion (Integration, E2E, Kimchi Hardening)

**MoSCoW:** SHOULD *(confidence for merges and refactors; not blocking Kimchi MVP or hackathon demo)*
**Target time:** ~4–8 h *(phased; can ship unit/integration layers before live smoke automation)*
**Status:** 📋 PLANNED

> **Context:** Kimchi provider delivery (see [`SLICE-16-KIMCHI-PROVIDER.md`](./SLICE-16-KIMCHI-PROVIDER.md)) added a **provider regression suite** (39 pytest cases, 2026-05-20). This slice tracks everything still **untested in CI** and the **manual / operational** gates called out during the Kimchi ↔ `main` merge review.

---

## Goal

Expand automated coverage beyond provider dispatch and stats so merges to `main` do not rely on manual smoke alone. Close gaps for orchestration, retrieval modes, Kimchi live API behavior, and performance-related code paths (`ensure_vector_index`, embedding batching).

---

## Already delivered (baseline — do not re-scope)

Provider regression tests landed with Kimchi hardening:

| Module | Covers |
|--------|--------|
| `tests/test_embedder_provider_dispatch.py` | Explicit `local` / `voyage` / `kimchi` routing; unknown provider → `ValueError`; Voyage contextualized vs standard path |
| `tests/test_retriever_vector_index.py` | Dense search uses `vector_index_{len(query)}` + `ensure_vector_index` for 384 / 1024 / 1536 |
| `tests/test_model_registry_dimensions.py` | Fixed dims (local/Voyage); runtime Kimchi (`dimensions: None`); `get_dimensions()` raises for runtime models |
| `tests/test_experiment_config_providers.py` | Pydantic + CLI load for local/voyage/kimchi; Kimchi rerank rejected |
| `tests/test_experiments_db_stats.py` | Vector DB stats: registry dims (local/Voyage); sampled chunk dims (Kimchi) |
| `tests/test_kimchi_provider.py` | Kimchi payload parsing, URL normalization, CAST model ID routing, example config |

**Verification today:** `rag-params-finder test` or `uv run pytest -m "not integration" --tb=short -q` (no MongoDB, no live API keys required; same command as CI on PRs to `main`).

---

## Parked work — priority matrix

### High — merge / production confidence

| Item | Type | Notes |
|------|------|--------|
| **Manual smoke checklist** | Manual / doc | Document and optionally script-check: `example-mongodb-local.yaml`, `example-mongodb-voyage.yaml`, `example-kimchi.yaml` end-to-end with server + Atlas. **Not automatable in CI without secrets/cluster.** |
| **Atlas indexes for Kimchi dims** | Ops / doc | Startup ensures `vector_index_384` + `vector_index_1024` only. Kimchi example sweep needs **`vector_index_1536`** and **`vector_index_3072`** (OpenAI-family models). Test slice should document required indexes; optional test asserts index names in stats when fixtures present. |
| **Kimchi embedding batching** | Code + test | `kimchi_embedder._embed` posts **one HTTP request per chunk** → slow sweeps, 429 risk. Implement batching (or bounded concurrency) when CAST API supports it; add unit tests for batch split/retry. |
| **Live CAST/Kimchi integration test** | Integration (env-gated) | `@pytest.mark.integration` skipped unless `KIMCHI_API_KEY` + `KIMCHI_BASE_URL` set. One probe embed + dimension assertion. Catches auth, routing, and real vector lengths. |

### Medium — correctness and ops debt

| Item | Type | Notes |
|------|------|--------|
| **`ensure_vector_index` cache** | Code + test | `retriever.dense_search` calls Atlas `list_search_indexes` (and maybe create) **per query**. Cache per-dimension “exists” in-process; test that second call does not re-list. |
| **Orchestrator phase tests** | Unit/integration | Mock Mongo + embedder/retriever boundaries: PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING transitions, `on_error: continue` vs `stop`. |
| **Pause / resume** | Integration | Cooperative pause stops scheduling; resume continues; characterization tests with mocked orchestrator state. |
| **Reranking** | Unit | Local CrossEncoder + Voyage reranker dispatch (mirror embedder provider tests). |
| **Sparse / hybrid retrieval** | Unit | `sparse_search` pipeline shape; `hybrid_search` RRF merge with mocked `aggregate` results. |
| **Mock MongoDB integration** | Integration | Fixtures for `chunks`, `experiments`, `run_status`, `results`; full pipeline slice without network (pre-computed embedding fixtures). Blocker called out in `docs/contributor-guide/development.md`. |
| **Parked Kimchi registry models** | Manual / doc | Registry lists 40+ IDs; example config enables four. Tests cannot verify CAST account availability — document `supported-providers` curl check before enabling parked models. |

### Lower — nice to have in same slice or follow-on

| Item | Type | Notes |
|------|------|--------|
| **Frontend component tests** | Frontend | vitest/jest for `ExperimentsScreen`, polling, delete modal (TypeScript-only gate today). |
| **Remove dead `kimchi_embedder.get_dimensions()`** | Code cleanup | Unused probe helper; embed path caches dims inline. |
| **`KIMCHI_TPM_LIMIT=0` behavior** | Code + test | Document “RPM-only throttling”; optional test that limiter respects TPM when set. |
| **Parallel sweep characterization** | Integration | When [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](./SLICE-16-PARALLEL-SWEEP-RUNS.md) ships: `parallelism: 1` matches today; `parallelism > 1` scheduling tests. |

---

## Acceptance criteria *(implementation exit)*

### Phase A — Documentation and manual gates

- [ ] `docs/user-guide/troubleshooting.md` (or contributor testing doc) includes **pre-merge smoke checklist** (local → Voyage → Kimchi) and **Kimchi Atlas index** requirements (`vector_index_1536`, `vector_index_3072`, etc.).
- [ ] Slice 17 cross-linked from `docs/contributor-guide/development.md` Testing Strategy (replace “no suite yet” where outdated).

### Phase B — Automated expansion (CI-safe)

- [ ] `tests/conftest.py` with shared fixtures (mock collections, sample embeddings, minimal `ExperimentConfig` builders).
- [ ] Orchestrator tests (mocked boundaries) for at least one happy path and one `on_error: stop` path.
- [ ] Reranker provider dispatch tests (local + voyage).
- [ ] Sparse + hybrid retriever tests with mocked Mongo `aggregate`.
- [ ] Test that `ensure_vector_index` is not called repeatedly for the same dimension after cache *(after cache implemented)*.

### Phase C — Optional live / heavy

- [ ] Env-gated Kimchi integration test (`pytest -m integration` documented in development.md).
- [ ] Kimchi embedding batching implemented + batch unit tests.
- [ ] Mock-Mongo full-pipeline integration test (no Voyage/Kimchi/Atlas network).

---

## Out of scope (other slices)

| Work | Slice |
|------|--------|
| Honor `execution.parallelism` | [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](./SLICE-16-PARALLEL-SWEEP-RUNS.md) |
| Failed-run retry CLI/API | [`SLICE-10-RUN-RECOVERY.md`](./SLICE-10-RUN-RECOVERY.md) |
| CI workflow itself | Done — `.github/workflows/ci.yml` (Slice 15 roadmap item) |
| README screenshots | `docs/_internal/DOC-GAPS.md` Gap 1 |

---

## Key files (expected touch)

| Area | Files |
|------|--------|
| Tests | `tests/conftest.py`, `tests/test_orchestrator.py`, `tests/test_reranker_dispatch.py`, `tests/test_retriever_sparse_hybrid.py`, `tests/test_kimchi_integration.py` *(optional)* |
| Code *(if batching/cache in scope)* | `server/core/kimchi_embedder.py`, `server/core/retriever.py`, `server/db/indexes.py` |
| Docs | `docs/contributor-guide/development.md`, `docs/user-guide/troubleshooting.md` |

---

## Verification

```bash
uv run ruff check .
uv run mypy server/ cli/
uv run pytest --tb=short -q                    # default CI — unit + mocked
uv run pytest -m integration --tb=short -q   # optional — requires KIMCHI_* / VOYAGE_* / MONGODB_URI
```

---

## References

- Kimchi merge review (branch `tessl-hackathon-kimchi-integration` vs `main`): provider dispatch, runtime vector indexes, db-stats, no live API coverage.
- `README.md` Contributing — test suite with mock MongoDB called out as priority.
- `VERIFICATION_CHECKLIST.md` — manual dashboard/regression cases (align smoke checklist with Slice 17 Phase A).
