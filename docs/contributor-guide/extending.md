# Extending the System

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

How to add new embedding models, chunking methods, retrieval methods, and API endpoints.

---

## 🤖 Adding a New Embedding Model

### 1. Register the model

In `server/core/model_registry.py`, add to `EMBEDDING_MODELS`:

```python
EMBEDDING_MODELS = {
    "my-new-model": {
        "provider": "local",          # or "voyage"
        "dimensions": 768,
        "huggingface_id": "org/my-new-model",  # for local models; None for Voyage
        "description": "Short label for docs",
        "contextualized": False,      # True only for voyage-context-* (contextualized_embed API)
    },
    ...
}
```

### 2. Add provider support (if new provider)

If the model uses a provider not yet supported, update `server/models/config.py` → `Provider` type and add dispatch logic in the embedder.

**Note on `kimchi`:** The `Provider` literal includes `"kimchi"` for CAST OpenAI-compatible embeddings. Full implementation (embedder module, registry entries, example config) lives on branch `tessl-hackathon-kimchi-integration`; **main** currently supports **`local`** and **`voyage`** only. Merge that branch before documenting Kimchi in the user guide.

### 3. Update the embedder dispatcher

In `server/core/embedder.py` (Voyage) or `server/core/local_embedder.py` (sentence-transformers): verify the model name routes correctly through the existing dispatch logic. For most new models of an existing provider type, no changes are needed.

**Contextualized models** (`contextualized: True`, e.g. `voyage-context-3`):

- Route through `_embed_documents_voyage_context()` → `client.contextualized_embed()`
- Respect Voyage's 32K-token per-segment window — long documents are split in `_split_context_segments()`
- Set `"contextualized": True` in `EMBEDDING_MODELS`; `is_contextualized_embedding()` drives dispatch in `embed_documents()`
- Standard Voyage models (`contextualized: False`) are unaffected — they use `client.embed()` only

### 4. Create an Atlas vector index

A new dimension size requires a new Atlas vector index. See [getting-started.md](../user-guide/getting-started.md#2-create-the-atlas-vector-index) for the index JSON format.

### 5. Update the example configs

Add the new model to `configs/example-mongodb-local.yaml` or `configs/example-mongodb-voyage.yaml` (whichever provider it belongs to), so users can immediately try it.

---

## ✂️ Adding a New Chunking Method

### 1. Create the chunker module

Create `server/core/chunkers/my_method.py`:

```python
from typing import List


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Return a list of text chunks."""
    # implementation here
    ...
```

### 2. Register the enum

In `server/models/enums.py`, add to `ChunkingMethod`:

```python
class ChunkingMethod(str, Enum):
    recursive = "recursive"
    fixed = "fixed"
    my_method = "my_method"   # add here
    ...
```

### 3. Wire the dispatcher

In `server/core/chunkers/__init__.py`, add a branch in `chunk_text()`:

```python
elif method == ChunkingMethod.my_method:
    from server.core.chunkers.my_method import chunk_my_method
    chunks = chunk_my_method(text, chunk_size, overlap)
```

### 4. Mirror the enum in TypeScript

In `frontend/src/types/index.ts`, add to `ChunkingMethod`:

```typescript
export type ChunkingMethod = "recursive" | "fixed" | "my_method" | ...;
```

---

## 🔍 Adding a New Retrieval Method

### 1. Implement the retrieval function

In `server/core/retriever.py`, add a new function alongside the existing `dense_search()`, `sparse_search()`, and `hybrid_search()`.

### 2. Register the enum

In `server/models/enums.py`, add to `RetrievalMethod`:

```python
class RetrievalMethod(str, Enum):
    dense = "dense"
    sparse = "sparse"
    hybrid = "hybrid"
    my_method = "my_method"   # add here
```

### 3. Wire the dispatcher

In `server/core/retriever.py`, add a branch in the `search()` dispatcher:

```python
if method == RetrievalMethod.my_method:
    return my_method_search(query_text, experiment_id, embedding_model, top_k)
```

### 4. Mirror in TypeScript

In `frontend/src/types/index.ts`, add to `RetrievalMethod`.

---

## 🔌 Adding a New API Endpoint

### 1. Create the route handler

Add to an existing router in `server/api/` (e.g., `experiments.py`) or create a new file:

```python
@router.get("/experiments/{experiment_id}/my-endpoint")
async def my_endpoint(experiment_id: str, db=Depends(get_db)):
    ...
```

### 2. Register the router

If creating a new router file, register it in `server/main.py`:

```python
from server.api import my_router
app.include_router(my_router)
```

### 3. Add the client method (if CLI needs it)

In `cli/api_client.py`:
```python
def get_my_data(experiment_id: str) -> dict:
    return self._get(f"/experiments/{experiment_id}/my-endpoint")
```

### 4. Add the fetch function (if dashboard needs it)

In `frontend/src/services/apiClient.ts`:
```typescript
export async function fetchMyData(experimentId: string): Promise<MyType> {
    const res = await fetch(`${BASE_URL}/experiments/${experimentId}/my-endpoint`);
    return res.json();
}
```

---

## ⚠️ Common Gotchas

| Gotcha | What to watch for |
|---|---|
| Vector dimension mismatch | Local models are 384-dim; Voyage models are 1024-dim. Cannot mix in the same experiment. Each dimension needs its own Atlas vector index. |
| Provider/model mismatch | Config validation fails if `provider: local` is paired with a Voyage model name. The `model_registry.py` cross-checks this at load time. |
| Missing embeddings filter | Always filter Atlas vector search by `embedding_model` — different models produce incompatible vectors that must not be compared. |
| Queries file URL caching | URL-sourced query files are downloaded to `configs/` and cached by hash. Delete the cached file to force re-download. |
| Server must be running | The CLI requires the server at `SERVER_URL` (default: `http://localhost:8001`). All commands fail if the server is down. |
| Rate limits on Voyage | Free tier: 3 RPM / 10k TPM (defaults). Tier 1: 2,000 RPM + model TPM — set `VOYAGE_RPM_LIMIT` / `VOYAGE_TPM_LIMIT` in `.env`. |
| `voyage-context-3` token window | Contextualized API: 32K tokens per document segment, no truncation. Server splits long docs automatically; single chunks must stay under 32K. Other Voyage models use standard `embed()`. |
| Score normalization | Rerank scores (cross-encoder logits) can be negative. The system uses min-max normalization to map all scores to 0–100. |
| TypeScript types are hand-mirrored | When changing Python models (`server/models/`), manually update `frontend/src/types/index.ts`. There is no codegen. |

---

## 🏛️ Dependency Direction

Outer layers call inward — never the reverse:

```
CLI / Dashboard → API handlers → orchestrator → core services → models / db
```

Engines (`orchestrator`, `retriever`, `embedder`) must not import from `api/` or depend on FastAPI objects. Keep handlers thin: validate input, call inward, return response.

---

## 👉 See Also

- [Architecture](architecture.md) — understand the module map and pipeline before extending
- [Development Guide](development.md) — git hooks (`install-git-hooks.sh`), quality gates, CI parity
- [Configuration Reference](../user-guide/configuration.md) — user-facing impact of new models and methods
- [Local Environment](local-environment.md) — Atlas index setup for new embedding dimensions
