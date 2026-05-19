# Troubleshooting

![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

Common errors and how to fix them.

---

## 🔍 Vector index not found

**Symptom**: server logs show `Search index 'vector_index' not found` or queries return no results.

**Cause**: The Atlas vector index must be created manually — the server cannot create it automatically.

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

Both indexes can coexist on the same `chunks` collection — the server selects the correct one automatically based on the model. Wait **~1–2 minutes** for the index to build before running queries.

---

## 🔍 Full Text Search index not found (sparse/hybrid)

**Symptom**: server logs show `Search index 'text_search_index' not found` or sparse/hybrid runs fail immediately.

**Cause**: The server attempts to create this index automatically on startup, but programmatic creation is not supported on **free-tier clusters (M0/M2/M5)**.

**Fix**:

If you're on a free-tier cluster and see this error:

1. Atlas UI → your cluster → **Browse Collections** → `chunks` collection → **Search Indexes** tab
2. **Create Search Index** → JSON Editor → name: `text_search_index`
3. Paste:

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "text": [{ "type": "string" }],
      "experiment_id": [{ "type": "token" }],
      "embedding_model": [{ "type": "token" }]
    }
  }
}
```

Wait ~1–2 minutes. The `text_search_index` and your vector indexes coexist on the same `chunks` collection.

**On paid clusters (M10+)**: If this error occurs, check server logs for creation failures and restart the server.

**Note**: If you only use `dense` retrieval, you do not need this index.

---

## ⚠️ Dimension mismatch (local vs Voyage models)

**Symptom**: vector search fails with a dimension error, or results are nonsensical.

**Cause**: local models produce 384-dim embeddings; Voyage models produce 1024-dim. Vectors from different models cannot be compared in the same search index.

**Fix**:
- Each embedding model needs its own Atlas vector index (`vector_index_384` or `vector_index_1024`)
- Never mix providers within the same experiment config (the system validates this at config load time)
- The server automatically routes to the correct index via `get_index_name(model)` in `server/core/retriever.py`

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

# Wrong — will fail validation immediately
embedding:
  provider: local
  models:
    - voyage-3.5-lite   # ERROR: voyage model with local provider
```

---

## ⏱️ Voyage API rate limit hit

**Symptom**: `voyageai.error.RateLimitError: Rate limit exceeded` in server logs; run status shows `failed`.

**Fix**:
- Check usage and org limits at [dash.voyageai.com/usage](https://dash.voyageai.com/usage) and [organization rate limits](https://dashboard.voyageai.com/organization/rate-limits)
- **Free tier** (no payment method): 3 RPM / 10,000 TPM — server defaults match this
- **Tier 1** (payment method): 2,000 RPM; TPM per model (e.g. `voyage-4-lite` / `voyage-3.5-lite` → 16M, `voyage-4` / `voyage-3.5` → 8M, `rerank-2.5-lite` → 4M). See [Voyage rate limits](https://docs.voyageai.com/docs/rate-limits) and `.env.example`
- Set `VOYAGE_RPM_LIMIT` and `VOYAGE_TPM_LIMIT` in `.env` to **match or stay slightly below** your tier (restart uvicorn after changing)
- If limits are too **low**, sweeps are slow but safe; if too **high**, you get 429s (retry/backoff applies)
- Switch to `provider: local` for testing (no API key, no rate limits)

---

## 📄 voyage-context-3 token limit exceeded

**Symptom**: server logs or Voyage API error:

```
Request to model 'voyage-context-3' failed. The example at index 0 in your batch has too many tokens
and does not fit into the model's context window of 32000 tokens.
```

**Cause**: `voyage-context-3` embeds document chunks via the **contextualized** API, which shares context across chunks in each segment. Voyage does **not** truncate contextualized inputs. Either:

1. The **combined tokens** of all chunks in one segment exceeded 32K (common on long PDFs), or
2. A **single chunk** exceeded 32K tokens (oversized `chunk_size`).

**Fix**:

- **Server ≥ 2026-05-19**: the embedder automatically splits long documents into ~30K-token segments. Restart uvicorn and re-run. Check logs for `Split N chunks into M contextualized segments`.
- If a **single chunk** is too large, reduce `chunk_sizes` in your YAML (e.g. `[256, 512]` not `[8192, 16384]`).
- For documents that still fail, temporarily disable `voyage-context-3` and use `voyage-3.5-lite` or `voyage-4-lite` (standard per-chunk embedding, no shared context).

**Note**: only `voyage-context-3` uses this API. All other registered Voyage models route through `client.embed()` and are not subject to the 32K per-segment limit.

---

## 🔁 Experiment stuck `running` or shows `partial` after server restart

**Symptom**: Dashboard shows an experiment as `running` for hours/days, or `partial` with many “Not Started” runs after you restarted uvicorn (`--reload`) or the server crashed mid-sweep.

**Cause**: Sweep execution runs in FastAPI `BackgroundTasks` (in-memory only). When the process dies, MongoDB may still show `status: running` and in-flight runs mid-phase — even though nothing is executing.

**Automatic fix (server ≥ 2026-05-19)**: On every server start, `reconcile_orphaned_experiments()` in `server/core/startup_reconciliation.py`:

1. Finds experiments still marked `running`
2. Marks in-flight runs as `interrupted` with error *“Interrupted — server restarted while run was in progress”*
3. Recomputes experiment status → usually `partial` when some runs completed and others never started

**What to do**:

1. Restart the server once — reconciliation runs at startup (check logs for `Reconciled N orphaned experiment(s)`)
2. On the detail screen, verify outcome metrics: **Successful + Failed + Interrupted + Not Started = Total**
3. To finish remaining parameter combos: **`rag-params-finder resume <experiment-id>`** if status is `paused`, or pause a running sweep first then resume later. Alternatively submit a trimmed YAML for missing combos, or wait for Slice 10 `recover` (retry failed/interrupted runs in-place)

**Prevention during long sweeps**:

- Avoid editing server code (triggers `--reload`) while a large sweep is running
- Run uvicorn **without** `--reload` for production-length sweeps: `uvicorn server.main:app --port 8001`

**Note**: `RECOVER_ON_BOOT=true` does **not** yet retry interrupted runs — it only logs a reminder. Status reconciliation always runs regardless of that flag.

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

## 🗑️ Deleting Experiments

**Use the CLI or dashboard** for safe deletion with cascade cleanup:

**CLI**:
```bash
# Delete with confirmation prompt
rag-params-finder delete <experiment-id>

# Delete without confirmation (use with caution)
rag-params-finder delete <experiment-id> --force
```

**Dashboard**:
- **Experiments list**: Click the trash icon in the Actions column
- **Experiment detail**: Click the trash icon in the top-right header

Both methods:
- Show a confirmation modal with experiment details
- Prevent deletion of **running** experiments (pause or cancel first; **paused** experiments can be deleted)
- Cascade delete across all collections (experiments, run_status, chunks, results)
- Display deletion statistics after completion

**Manual cleanup** (if needed):
```javascript
// Only use if CLI/dashboard unavailable — otherwise use the delete command
const exp_id = "your-experiment-id"
db.experiments.deleteOne({experiment_id: exp_id})
db.run_status.deleteMany({experiment_id: exp_id})
db.chunks.deleteMany({experiment_id: exp_id})
db.results.deleteMany({experiment_id: exp_id})
```

⚠️ **Warning:** Manual deletion bypasses validation (can delete running experiments) and provides no statistics.

---

## 🔧 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONGODB_URI` | Yes | — | MongoDB Atlas connection string |
| `VOYAGE_API_KEY` | No | — | Voyage AI API key (only if using Voyage models) |
| `SERVER_URL` | No | `http://localhost:8001` | FastAPI server URL (used by CLI) |
| `VOYAGE_RPM_LIMIT` | No | `3` | Voyage requests-per-minute limit (throttle guard; free-tier default) |
| `VOYAGE_TPM_LIMIT` | No | `10000` | Voyage tokens-per-minute limit (free-tier default) |
| `ATLAS_PUBLIC_KEY` | No | — | Atlas Admin API public key — enables cluster storage quota in dashboard |
| `ATLAS_PRIVATE_KEY` | No | — | Atlas Admin API private key |
| `ATLAS_GROUP_ID` | No | — | 24-char Atlas **project** ID (from cloud.mongodb.com URL) |
| `ATLAS_CLUSTER_NAME` | No | *(from URI)* | Cluster name for quota lookup; parsed from `MONGODB_URI` host if omitted |
| `MONGODB_STORAGE_LIMIT_MB` | No | `0` | Manual cluster quota override (MB). `0` = try Atlas API; omit quota bar if unavailable |
| `RECOVER_ON_BOOT` | No | `false` | Stored in experiment metadata for the dashboard. **Status reconciliation on boot always runs.** Automatic **retry** of interrupted runs is not implemented yet ([Slice 10](../slices/SLICE-10-RUN-RECOVERY.md)). |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG` for verbose output) |

---

## 🗄️ MongoDB Atlas Collections Reference

| Collection | Purpose | Key Indexes |
|---|---|---|
| `chunks` | Text chunks + embeddings | Vector index on `embedding` (cosine, 384 or 1024-dim) + filter fields |
| `experiments` | Experiment metadata + sweep config | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `results` | Per-query top-K results | `experiment_id`, `query_id` |

---

## 👉 See Also

- [Getting Started](getting-started.md) — Atlas setup, vector index creation, and first run
- [Configuration Reference](configuration.md) — fix provider/model mismatch errors
- [Dashboard Guide](dashboard-guide.md) — understand what the UI is showing
- [Local Environment](../contributor-guide/local-environment.md) — deeper debugging and MongoDB shell patterns
