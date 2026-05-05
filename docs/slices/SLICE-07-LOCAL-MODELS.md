# SLICE 07 — Free/Local Embedding + Reranking Models

**MoSCoW:** MUST  
**Target time:** ~15 min  
**Actual time:** ~15 min  
**Status:** ✅ COMPLETE (2026-05-02)

---

## Goal

Add local sentence-transformers models as a zero-cost, no-API-key alternative to Voyage AI. An explicit `provider` field in the YAML config drives routing end-to-end. Engineers can run full experiments without any external credentials.

---

## Acceptance Criteria

- [x] `provider: local` in config routes embedding to `all-MiniLM-L6-v2` (384-dim, sentence-transformers)
- [x] `rerank_provider: local` routes reranking to `cross-encoder/ms-marco-MiniLM-L-6-v2`
- [x] `provider: voyage` preserved; Pydantic validator cross-checks model names match declared provider
- [x] Models lazy-load and cache on first use (HuggingFace hub cache)
- [x] `configs/example-local.yaml` runs end-to-end with no `.env` file
- [x] Separate Atlas vector index `vector_index_384` required for 384-dim local embeddings

---

## Files Changed

| File | Change |
|---|---|
| `server/core/model_registry.py` | **NEW** Unified model registry (embedding + reranker, provider, dimensions, HuggingFace ID) |
| `server/core/local_embedder.py` | **NEW** `SentenceTransformer` wrapper (lazy-load, cached) |
| `server/core/local_reranker.py` | **NEW** `CrossEncoder` wrapper (lazy-load, cached) |
| `configs/example-local.yaml` | **NEW** All-local experiment config |
| `configs/example-voyage-ai.yaml` | **NEW** Preserved Voyage AI config |
| `server/models/config.py` | **EDIT** `provider` on `EmbeddingConfig`; `rerank_provider` on `RetrievalConfig`; Pydantic cross-validators |
| `server/core/embedder.py` | **EDIT** Accepts `provider` param; dispatches to local or Voyage |
| `server/core/reranker.py` | **EDIT** Accepts `provider` param; dispatches to local or Voyage |
| `server/core/orchestrator.py` | **EDIT** Passes `embedding_provider` and `rerank_provider` from `RunParams` |
| `server/core/retriever.py` | **EDIT** Dynamic index name via `get_index_name(model)` → `vector_index_1024` or `vector_index_384` |
| `cli/config_loader.py` | **EDIT** Validates models against registry at load time |
| `pyproject.toml` | **EDIT** Added `sentence-transformers>=2.6.0,<4.0.0`; `numpy>=1.26,<2` |
| `README.md` | **EDIT** Updated for provider-based config |

---

## Key Decisions

| Decision | Why |
|---|---|
| Explicit `provider` field | Config is source of truth; no runtime model-name-to-provider inference |
| Provider flows through `RunParams` → orchestrator → embedder/reranker | End-to-end explicit routing; stale server code cannot mis-dispatch |
| Pydantic cross-validators | Fast-fail at config parse with clear error messages |
| `sentence-transformers` for both embed and rerank | Single package: `SentenceTransformer` for embeddings, `CrossEncoder` for reranking |
| `numpy<2` pin | PyTorch compiled against NumPy 1.x ABI; 2.x causes `_ARRAY_API not found` crashes |
| Separate vector indexes per dimension | Atlas requires exact `numDimensions`; 384 ≠ 1024 |

---

## Atlas Index for Local Models

Create in Atlas UI → `chunks` collection → Search Indexes → JSON Editor:

```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine" },
    { "type": "filter", "path": "experiment_id" },
    { "type": "filter", "path": "embedding_model" }
  ]
}
```

Name: `vector_index_384`

---

## Exit Criteria

- `rag-params-finder run --config configs/example-local.yaml` completes without `VOYAGE_API_KEY`
- Results stored with 384-dim embeddings under `vector_index_384`
- `provider: local` + Voyage model name → Pydantic validation error at config load
