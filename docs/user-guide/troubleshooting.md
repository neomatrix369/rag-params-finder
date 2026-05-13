# Troubleshooting

![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

Common errors and how to fix them.

---

## 🔍 Vector index not found

**Symptom**: server logs show `Search index 'vector_index' not found` or queries return no results.

**Cause**: The Atlas vector index must exist with the same number of dimensions as the embedding vector.

**Fix**:

1. Atlas UI → your cluster → **Browse Collections** → `chunks` collection → **Search Indexes** tab
2. **Create Search Index** → JSON Editor
3. Paste the correct index definition for your model type

**Voyage models** (1024-dim) — name: `vector_index_1024`:
```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine" },
    { "type": "filter", "path": "experiment_id" },
    { "type": "filter", "path": "embedding_model" },
    { "type": "filter", "path": "chunking_method" },
    { "type": "filter", "path": "chunk_size" },
    { "type": "filter", "path": "overlap" }
  ]
}
```

**Local models** (384-dim) — name: `vector_index_384`:
```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine" },
    { "type": "filter", "path": "experiment_id" },
    { "type": "filter", "path": "embedding_model" },
    { "type": "filter", "path": "chunking_method" },
    { "type": "filter", "path": "chunk_size" },
    { "type": "filter", "path": "overlap" }
  ]
}
```

For Kimchi models, dimensions are detected at runtime and the server routes to `vector_index_<dimension>`. If programmatic index creation is unsupported on your Atlas tier, copy the dimension from the server log and create the matching index manually.

All indexes can coexist on the same `chunks` collection. Wait **~1–2 minutes** for the index to build before running queries.

---

## ⚠️ Dimension mismatch

**Symptom**: vector search fails with a dimension error, or results are nonsensical.

**Cause**: local models produce 384-dim embeddings, Voyage models produce 1024-dim embeddings, and Kimchi-hosted models vary by model. Vectors from different models cannot be compared in the same search index.

**Fix**:
- Each embedding dimension needs its own Atlas vector index (`vector_index_384`, `vector_index_1024`, or `vector_index_<runtime-dim>`)
- Never mix providers within the same experiment config (the system validates this at config load time)
- The server automatically routes to the correct index from the query embedding length in `server/core/retriever.py`

---

## ⚠️ Provider/model mismatch

**Symptom**: `ValidationError` when running the CLI — error message mentions provider and model name mismatch.

**Cause**: Config has `provider: local` but lists a Voyage model name (or vice versa).

**Fix**: Make sure `provider` matches the model:
```yaml
# Correct — local provider with local model
embedding:
  provider: local
  models:
    - all-MiniLM-L6-v2

# Correct — voyage provider with Voyage model
embedding:
  provider: voyage
  models:
    - voyage-3.5-lite

# Correct — kimchi provider with prefixed Kimchi model ID
embedding:
  provider: kimchi
  models:
    - openai/text-embedding-3-large

# Wrong — will fail validation immediately
embedding:
  provider: local
  models:
    - voyage-3.5-lite   # ERROR: voyage model with local provider
```

---

## 🍜 Kimchi credentials missing

**Symptom**: run fails during the EMBEDDING phase with `KIMCHI_BASE_URL not set` or `KIMCHI_API_KEY not set`.

**Fix**:
- Set both values in `.env`; never put them in config YAML.
- Use `KIMCHI_BASE_URL=https://llm.cast.ai/openai`. Do not use the
  `supported-providers` discovery URL as the embeddings base URL.
- Confirm the server was restarted after editing `.env`.
- Use `configs/example-kimchi.yaml` only when `embedding.provider: kimchi` should call the hosted Kimchi service.

---

## ⏱️ Voyage API rate limit hit

**Symptom**: `voyageai.error.RateLimitError: Rate limit exceeded` in server logs; run status shows `failed`.

**Fix**:
- Check usage at [dash.voyageai.com/usage](https://dash.voyageai.com/usage)
- Free tier: 300 RPM / 1M TPM
- Set `VOYAGE_RPM_LIMIT` and `VOYAGE_TPM_LIMIT` in `.env` to throttle requests to match your tier
- Switch to `provider: local` for testing (no API key, no rate limits)

---

## 🌀 Dashboard stuck on "Loading…"

**Symptom**: browser shows a loading spinner indefinitely or a "Failed to fetch" error.

| Cause | Fix |
|---|---|
| Server not running | Start with `uvicorn server.main:app --reload --port 8001`; verify at `http://localhost:8001/healthz` |
| Wrong server port | Check `SERVER_URL` in `.env` matches the port uvicorn is using |
| CORS error | Hard-refresh the browser (`Cmd+Shift+R`); restart server |
| Frontend pointing at wrong URL | Check `frontend/src/services/apiClient.ts` base URL matches server port |

---

## 🗄️ Chunks not appearing in Atlas

**Symptom**: experiment completes but the `chunks` collection in Atlas is empty or the run count is zero.

**Possible causes**:
- MongoDB connection lost during the STORING phase — check server logs for `pymongo` errors
- Atlas free-tier storage quota exceeded (512 MB limit on M0) — check **Metrics → Storage** in the Atlas UI
- Vector index not yet built — chunks are stored but queries fail silently

**Debug steps**:
```bash
# Tail server logs for MongoDB or storage errors
tail -f server.log | grep -i "mongo\|store\|chunk"
```

Then check Atlas UI → **Metrics → Operations** for write failures.

---

## 🧹 MongoDB manual cleanup

There is no cascade delete — if you need to delete an experiment, clean all four collections:

```javascript
const exp_id = "your-experiment-id"
db.experiments.deleteOne({experiment_id: exp_id})
db.run_status.deleteMany({experiment_id: exp_id})
db.chunks.deleteMany({experiment_id: exp_id})
db.results.deleteMany({experiment_id: exp_id})
```

---

## 🔧 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONGODB_URI` | Yes | — | MongoDB Atlas connection string |
| `VOYAGE_API_KEY` | No | — | Voyage AI API key (only if using Voyage models) |
| `KIMCHI_BASE_URL` | No | — | Kimchi OpenAI-compatible embeddings endpoint |
| `KIMCHI_API_KEY` | No | — | Kimchi API key (only if using Kimchi models) |
| `SERVER_URL` | No | `http://localhost:8001` | FastAPI server URL (used by CLI) |
| `VOYAGE_RPM_LIMIT` | No | `300` | Voyage requests-per-minute limit (throttle guard) |
| `VOYAGE_TPM_LIMIT` | No | `1000000` | Voyage tokens-per-minute limit |
| `KIMCHI_RPM_LIMIT` | No | `60` | Kimchi requests-per-minute limit |
| `KIMCHI_TPM_LIMIT` | No | `0` | Kimchi tokens-per-minute limit; `0` disables token throttling |
| `RECOVER_ON_BOOT` | No | `false` | Auto-retry interrupted runs when server starts |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG` for verbose output) |

---

## 🗄️ MongoDB Atlas Collections Reference

| Collection | Purpose | Key Indexes |
|---|---|---|
| `chunks` | Text chunks + embeddings | Vector index on `embedding` (`vector_index_<dimension>`) + filter fields |
| `experiments` | Experiment metadata + sweep config | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `results` | Per-query top-K results | `experiment_id`, `query_id` |

---

## 👉 See Also

- [Getting Started](getting-started.md) — Atlas setup, vector index creation, and first run
- [Configuration Reference](configuration.md) — fix provider/model mismatch errors
- [Dashboard Guide](dashboard-guide.md) — understand what the UI is showing
- [Local Environment](../contributor-guide/local-environment.md) — deeper debugging and MongoDB shell patterns
