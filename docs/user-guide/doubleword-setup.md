# DoubleWord Embedding Provider Setup

![DoubleWord](https://img.shields.io/badge/DoubleWord-batch_embeddings-4A90E2)
![Qwen3](https://img.shields.io/badge/Qwen3--Embedding--8B-1024--dim-orange)
![Async](https://img.shields.io/badge/async_batches-restart_safe-green)

**DoubleWord** is an **async batch cloud embedding provider** specializing in large
language models like `Qwen/Qwen3-Embedding-8B` (8B parameters, 1024-dim) at significantly
lower cost than synchronous APIs.

Jobs submit immediately but vectors may take **minutes to 24 hours** to arrive. The
rag-params-finder server includes a **detached watcher** that polls for completion
automatically and resumes runs once vectors are cached — other experiments are **never
blocked**.

> **You do not need DoubleWord unless you want to compare models like Qwen3 alongside
> Voyage or local models.** Qwen3 is the only available model, and it requires a
> DoubleWord account + API key.

---

## When to use DoubleWord

| Scenario | Recommendation |
|----------|---|
| I want fast local embeddings (no API key) | Use `all-MiniLM-L6-v2` with `provider: local` — [docs](mongodb-setup.md#path-b--atlas-local-docker) |
| I want hosted embeddings (commercial) | Use Voyage AI models — [docs](../CLAUDE.md#provider-system) + `VOYAGE_API_KEY` in .env |
| I want to compare multiple embedding models, incl. Qwen3 | **Use DoubleWord** + `DOUBLEWORD_API_KEY` + [example-provider-compare.yaml](../../configs/mongodb/example-provider-compare.yaml) |
| I want to compare only Qwen3 in isolation | **Use DoubleWord** + [example-doubleword.yaml](../../configs/mongodb/example-doubleword.yaml) |

---

## Environment variables

Add these to your `.env` file. Only `DOUBLEWORD_API_KEY` is required; the rest have sensible defaults.

| Variable | Default | Description |
|---|---|---|
| `DOUBLEWORD_API_KEY` | — | **Required** — API key from [doubleword.ai](https://doubleword.ai) |
| `DOUBLEWORD_BASE_URL` | `https://api.doubleword.ai/v1` | API endpoint |
| `DOUBLEWORD_POLL_INTERVAL_S` | `10` | Seconds between batch status polls |
| `DOUBLEWORD_POLL_TIMEOUT_S` | `5` | Per-poll HTTP timeout in seconds |
| `DOUBLEWORD_COMPLETION_WINDOW` | `1h` | Batch completion window hint passed to API (controls pricing tier) |
| `EMBEDDING_CACHE_PATH` | `.rpf_cache/embeddings.sqlite` | SQLite vector cache location — **must persist across restarts** |

---

## Quick start

### 1. Get a DoubleWord API key

1. Sign up at [doubleword.ai](https://doubleword.ai)
2. Navigate to **Settings** → **API Keys**
3. Create a new key
4. Add it to `.env`:

```bash
DOUBLEWORD_API_KEY=dw-your_api_key_here
```

### 2. Start the server

```bash
# Backend
uvicorn server.main:app --reload --port 8001

# Frontend (new terminal)
cd frontend && npm run dev

# In another terminal, run CLI
rag-params-finder run --config configs/mongodb/example-doubleword.yaml
```

The server starts a background watcher that polls DoubleWord batches automatically.

### 3. Watch the dashboard

Open [http://localhost:5374](http://localhost:5374). The experiment card shows:
- Experiment status (QUEUED, WAITING, COMPLETE, etc.)
- Current phase (PARSING → CHUNKING → EMBEDDING → QUERYING → RERANKING → COMPLETE)
- Each phase's completion time

---

## How it works (async batch architecture)

### High-level flow

```
CLI submits config
         ↓
Server pre-plans texts & submits DoubleWord batch jobs
         ↓
Returns experiment-id immediately (CLI does NOT wait)
         ↓
Detached asyncio watcher polls batch status every 10 seconds
         ↓
When all batches complete → vectors cached locally
         ↓
Sweep execution continues; other experiments proceed meanwhile
```

### Phases

| Phase | What happens | Duration | Notes |
|-------|---|---|---|
| **QUEUED** | Experiment queued on server | ~0.1 s | Entry point |
| **PARSING** | PDFs extracted to text | varies | Depends on PDF size/format |
| **CHUNKING** | Text split into chunks | ~1 s | Per configured chunking method |
| **EMBEDDING** | DoubleWord batch submitted + watcher polls | **minutes to hours** | Async — other experiments run. Typical: < 1k texts = 1–5 min; 10k+ texts = 1–24 h. Watcher restarts on boot |
| **STORING** | Vectors stored in MongoDB | varies | Depends on vector store backend |
| **QUERYING** | Retrieval queries run (dense/sparse/hybrid) | varies | Depends on query count and index |
| **RERANKING** | Optional re-ranking (if configured) | varies | Only if `type: cross_encoder` or `type: reranker` |
| **COMPLETE** | Experiment finished; results ready | — | Terminal state |

### Where vectors are cached

Vectors are stored in SQLite at `.rpf_cache/embeddings.sqlite` (default). Key features:

- **Content-addressed**: Key is `sha256(text, provider, model, dim, instruction, role)`
- **Shared across sweeps**: If two experiments embed the same text with the same model, it is embedded once and reused
- **SQLite WAL mode**: Allows concurrent reads; Python's `sqlite3` serializes writes internally
- **Persistent**: Must survive server restarts for restart-safety

### Checkpoint store

Batch IDs are stored in `.rpf_state/doubleword_batches.json` for restart safety:

```json
{
  "batch_001": {
    "batch_id": "b_xyz...",
    "model": "Qwen/Qwen3-Embedding-8B",
    "status": "processing",
    "submitted_at": "2026-09-30T12:34:56Z",
    "expires_at": "2026-10-01T12:34:56Z"
  }
}
```

**Restart-safe resume**: If the server reboots mid-batch:
1. Watcher reads `.rpf_state/doubleword_batches.json` on boot
2. Resumes polling the same `batch_id`
3. No re-submission; no wasted API credits

---

## Batch latency

DoubleWord pricing varies by completion window. Typical durations:

| Text count | Completion window | Typical time |
|---|---|---|
| < 1,000 texts | 1 h | **1–5 min** |
| 1,000–10,000 texts | 1 h | **5–30 min** |
| 10,000–100,000 texts | 1 h | **1–3 hours** |
| 100,000+ texts | 24 h | **2–24 hours** |

Your `.env` sets `DOUBLEWORD_COMPLETION_WINDOW=1h` by default. Longer windows (e.g., `DOUBLEWORD_COMPLETION_WINDOW=24h`) may reduce cost but increase completion time.

---

## Docker and volumes (restart safety)

If running the server in Docker, mount `.rpf_cache/` and `.rpf_state/` as named volumes:

```bash
docker run \
  -v rag_cache:/app/.rpf_cache \
  -v rag_state:/app/.rpf_state \
  rag-params-finder-server
```

Or in `docker-compose.yml`:

```yaml
services:
  server:
    volumes:
      - rag_cache:/app/.rpf_cache
      - rag_state:/app/.rpf_state

volumes:
  rag_cache:
  rag_state:
```

**Without persistence**: If `.rpf_cache/` is deleted, vectors cannot be recovered from DoubleWord servers — experiments must be re-run (and re-charged).

---

## Troubleshooting

### "422 DOUBLEWORD_API_KEY not configured"

The server did not find `DOUBLEWORD_API_KEY` in `.env`.

**Fix**: Add the key to `.env`:

```bash
DOUBLEWORD_API_KEY=dw-your_api_key_here
```

Then restart the server.

### "Experiment stuck at EMBEDDING / WAITING"

The watcher is polling but batches have not completed yet. This is **normal** for large datasets.

**Checks**:
1. Look at server logs for `[DoubleWord Watcher]` lines — confirms polling is running
2. Visit [https://app.doubleword.ai/batches](https://app.doubleword.ai/batches) and sign in to see batch status
3. Check the experiment's **Details** tab in the dashboard for the batch ID

**If stuck for > 24 hours**:
- Check your DoubleWord account plan (free tier max ~2 concurrent jobs)
- See if the batch shows errors in the DoubleWord dashboard
- Contact [DoubleWord support](https://doubleword.ai/support)

### "Cache directory not writable" or SQLite lock errors

The server cannot write to `.rpf_cache/` or `.rpf_state/`.

**Fixes**:
- Ensure the directory exists: `mkdir -p .rpf_cache .rpf_state`
- Check permissions: `chmod 755 .rpf_cache .rpf_state`
- If running in Docker, ensure volumes are mounted (see [Docker and volumes](#docker-and-volumes-restart-safety))

### "Unavailable model: Qwen/Qwen3-Embedding-8B"

The model is no longer available from DoubleWord, or a temporary API error occurred.

**Fix**: The server caches the unavailable status in `.rpf_state/doubleword_unavailable.json`. Delete or edit the file to retry:

```bash
rm .rpf_state/doubleword_unavailable.json
```

Then resubmit the experiment.

---

## Mixed-provider experiments

Use [example-provider-compare.yaml](../../configs/mongodb/example-provider-compare.yaml) to compare local, Voyage, and DoubleWord models in one sweep:

```yaml
embedding:
  # provider omitted — derived per model
  models:
    - all-MiniLM-L6-v2           # local (384-dim)
    - Qwen/Qwen3-Embedding-8B   # doubleword (1024-dim)
```

The sweep creates 2 runs (local completes immediately; DoubleWord waits for batch). Vectors are compared fairly despite their different dimensions — the retriever uses the `embedding_model` filter to prevent cross-contamination.

---

## Cost estimation

**Qwen/Qwen3-Embedding-8B pricing** (as of 2026-09):
- ~$0.003 per 1 million tokens
- No per-request API charges (unlike Voyage or hosted APIs)

**Example sweep**:
- 1 PDF, ~200 pages, ~10,000 chunks
- 10,000 chunks × ~100 tokens/chunk = 1 million tokens
- Cost: ~$0.003 per sweep

Compare: Voyage `voyage-3.5` costs ~$0.06/1M tokens — **20× more expensive** for the same documents.

---

## Further reading

- [example-doubleword.yaml](../../configs/mongodb/example-doubleword.yaml) — minimal working config
- [example-provider-compare.yaml](../../configs/mongodb/example-provider-compare.yaml) — mixed-provider sweep
- [ADR-005](../adr/ADR-005-doubleword-embedding-provider.md) — design rationale + async architecture
- [BRIEF-doubleword-embedder.md](../plan/BRIEF-doubleword-embedder.md) — full design brief
