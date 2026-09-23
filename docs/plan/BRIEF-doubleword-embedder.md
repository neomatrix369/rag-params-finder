# Brief — DoubleWord Embedder (Qwen3-Embedding-8B) as a Sweepable Embedding Provider

> **Source material, not a slice spec.** Owner-supplied plan (2026-09-24), originally titled "SLICE-32". Kept for traceability and for the reusable design sketches (§6.3, §6.7, Appendix A).
> **Executable specs:** [48A](slices/08-embedding-providers/SLICE-48A-DOUBLEWORD-REALTIME-PROVIDER.md) · [48B](slices/08-embedding-providers/SLICE-48B-DOUBLEWORD-BATCH-CACHE-PREEMBED.md) · [48C](slices/08-embedding-providers/SLICE-48C-DOUBLEWORD-MRL-INSTRUCTION-AXES.md). Where this brief and a slice spec disagree, **the slice spec wins**.
> **Decisions:** [DECISIONS #188–#197](DECISIONS.md).

## Reconciliation against `main` @ `6283caa` (2026-09-24)

| Brief assumes | Repo reality | Resolution |
|---|---|---|
| Slice number **32** / **32B** | 32 / 32B / 32C = Storage Protocol track | Renumbered **48A / 48B / 48C** (#188) |
| 32A = one Must slice (realtime + batch + cache + pre-embed + cost) | Too large for one skateboard increment | Split: 48A realtime skateboard · 48B batch/cache/pre-embed/cost · 48C axes (#189) |
| `EmbedderProtocol`, async `DoublewordEmbedder` class, `server/embedders/…` | Sync plain functions dispatched by `server/core/embedding/embedder_factory.get_embedder(provider)`; DECISIONS #10 prefers factory over Protocol | New module `server/core/embedding/doubleword_embedder.py` + factory branch (#191) |
| `AsyncOpenAI` + `respx` | `httpx` already a dependency; no `openai` or `respx`; kimchi branch used raw `httpx` to `/v1/embeddings` | Sync `httpx.Client`; tests use `httpx.MockTransport`; **no new dependency** (#191) |
| `embedding.models[]` entries with `class:` / `params:` / `requires_env:` | `EmbeddingConfig{provider, models: list[str]}`: one provider per experiment; the registry owns each model's provider | `embedding.provider` becomes optional; provider derived per model from the registry, so mixed-provider sweeps need no new schema block (#190) |
| Generic `requires_env` + WARN-and-skip | Fail-closed preflight guards (`sie_guard`, `config_backend_guard`) return **HTTP 422** at submit | `doubleword_guard` returns 422 when a DoubleWord model is configured without `DOUBLEWORD_API_KEY`; configs without DoubleWord are unaffected (#192) |
| Per-identity vector fields `emb__dw_qwen3_8b__1024` | Indexes keyed by dimension (`vector_index_{dims}`, Postgres `embedding_1024`) plus a mandatory `embedding_model` filter | 1024-dim needs **no** index or schema change (48A). Other dimensions are 48C's problem: Postgres has only 384/1024 columns, and pgvector HNSW caps `vector` at 2000 dims (#196) |
| New `pre_embedding` run **Phase** | `Phase` is per run; pre-embed is per experiment | Experiment-level `pre_embed` progress object; the `Phase` enum is unchanged (#194) |
| Bayesian: no complete run list | 41A Bayesian uses `suggest_categorical` over declared chunk sizes and overlaps, so the space is finite | Pre-embed the declared space for both grid and Bayesian runs (#193) |
| `@pytest.mark.live` | Repo marker is `integration` (excluded by default) | Opt-in DoubleWord tests use `integration` and skip when no key is set |
| `docs/embedders/doubleword.md`, `configs/examples/…` | Pattern: `docs/user-guide/sie-setup.md`; `configs/{mongodb,supabase}/example-*.yaml` | `docs/user-guide/doubleword-setup.md`; example config in both folders |
| ADR-0XX | Next free number: ADR-005 | `docs/adr/ADR-005-doubleword-embedding-provider.md` (Proposed in 48A, Accepted at 48B close) |
| Qwen3 query format `Instruct: …\nQuery: {q}` | The official Qwen3-Embedding example uses `Query:{q}` (no space) | Confirm in the V-spike (V9, 48A T0) |

---

## Original brief (condensed: the sections executors still need; section numbers match the owner's original)

Omitted sections: §2 recon (superseded by the table above), §4 scope, §5.1–5.2 config (superseded by #190/#192), §6.1/6.5/6.6/6.8/6.9 async class sketches (superseded by #191), §7.2–7.5, §9–10 (re-expressed as GWT in the slice specs), §12 (→ 48C), Appendix B.

### 1. Context: what DoubleWord is and why it fits a sweep engine

DoubleWord is primarily a **batch inference cloud** with an OpenAI-compatible API at `https://api.doubleword.ai/v1`. It exposes exactly **one embedding model**: `Qwen/Qwen3-Embedding-8B`.

| Property | Value |
|---|---|
| Model ID (exact) | `Qwen/Qwen3-Embedding-8B` |
| Context length | 32K tokens |
| Output dimension | up to 4096; user-defined 32–4096 (MRL) |
| Instruction-aware | yes (task instructions on queries) |
| Languages | 100+ |
| MTEB multilingual | #1 as of 2025-06-05 (70.58) |
| Price per 1M input tokens | Realtime $0.04 · Async $0.03 · Batch (24h) $0.02 |
| Output tokens | $0.00 |
| Realtime availability | **limited**: DoubleWord states it is primarily a batch API |

Why it matters for rag-params-finder: DoubleWord's embeddings workbook argues that re-embedding after every chunking change is where embedding costs multiply, which is exactly what a chunking × embedding sweep does. Their measured run (1.6M tokens) cost $0.03 on DoubleWord batch, against $0.19 on voyage-3-large and $0.10 on OpenAI batch. Their small 100-query Wikipedia eval had Qwen3-Embedding-8B at recall@10 82.4% against 85.1% for text-embedding-3-large (both at 1024 dims). That is close enough to let the sweep decide on *your* data.

**Key design consequence:** in a grid sweep, every chunk configuration *and* every golden-master question is known before any trial runs. So both documents and queries can be embedded in one batch per embedding config, which makes the 24h batch tier usable even for query embeddings.

### 3. Verification spike (≤ 30 min, before production code)

| # | Question | How to check | If NO |
|---|---|---|---|
| V1 | Does `/v1/embeddings` accept the OpenAI `dimensions` parameter? | `dimensions=512` → `len(vec) == 512` | Always request full vectors; truncate client-side and L2-renormalize (valid for MRL models) |
| V2 | Default output dim with no `dimensions` | `len(vec)` | Record actual default (expected 4096) |
| V3 | Batch accepts `endpoint="/v1/embeddings"` with JSONL `url: "/v1/embeddings"` | Submit a 3-line batch, poll to completion | Stop; fall back to realtime/async only and record in ADR |
| V4 | Batch output line shape | Expected `response.body.data[0].embedding` + `response.body.usage.prompt_tokens` | Adapt parser |
| V5 | Can one batch request carry a list `input`? | JSONL body with `input: ["a","b"]` | Keep one text per line |
| V6 | Is `completion_window="1h"` accepted for embeddings? | Submit with `"1h"` | Use `"24h"` only |
| V7 | `GET /v1/batches/{id}/analytics` returns `total_cost` | httpx GET | Compute cost as `prompt_tokens × price` |
| V8 | Realtime availability right now | 10 sequential realtime calls; note errors/latency | Realtime marked "best effort"; default mode = batch |

### 5.3 Provider metadata (static, used for cost + validation)

```yaml
provider: doubleword
base_url: "https://api.doubleword.ai/v1"
auth_env: DOUBLEWORD_API_KEY
models:
  "Qwen/Qwen3-Embedding-8B":
    context_tokens: 32768
    max_dimensions: 4096
    min_dimensions: 32
    mrl: true
    instruction_aware: true
    context_injection: false        # axis-independent from chunking (unlike voyage-context-3)
    price_per_mtok: { realtime: 0.04, async: 0.03, batch: 0.02 }
limits:
  max_jsonl_line_bytes: 5242880     # 5 MB per JSONL line (learned in docextract)
  poll_interval_s: 10
```

### 6.3 Qwen3 instruction formatting

Qwen3-Embedding is instruction-aware on the **query** side; documents are embedded as plain text. The instruction string is part of the **cache key** and the **run identity**.

```python
def format_query(text: str, instruction: str | None) -> str:
    if not instruction:
        return text
    return f"Instruct: {instruction}\nQuery: {text}"   # V9: confirm spacing against official example
```

### 6.4 MRL truncation

```python
def truncate_and_normalize(vec: list[float], dim: int) -> list[float]:
    if dim > len(vec):
        raise ValueError(f"Requested dim {dim} > vector length {len(vec)}")
    v = np.asarray(vec[:dim], dtype=np.float32)
    n = np.linalg.norm(v)
    return (v / n).tolist() if n > 0 else v.tolist()
```

Optimization for the dimension axis: embed once at max dim and derive lower dims by truncation, so one paid pass serves every `embedding_dim` value.

### 6.7 Batch pipeline sketch (ported from docextract; re-express as sync `httpx` in 48B)

```python
MAX_LINE_BYTES = 5_242_880
TERMINAL = {"completed", "failed", "expired", "cancelled"}

def build_jsonl(items, *, model, dimensions) -> bytes:
    """items: [(custom_id, text)] — custom_id is the cache key hash."""
    # one line per item: {"custom_id", "method": "POST", "url": "/v1/embeddings", "body": {model, input[, dimensions]}}
    # raise ValueError naming custom_id when a line exceeds MAX_LINE_BYTES

class CheckpointStore:  # {job_key: {batch_id, submitted_at, n}}; enables resume across restarts
    ...

def run_batch(client, job_key, items, *, model, dimensions, window, ckpt, interval_s=10, on_progress=None):
    # 1. existing checkpoint → retrieve; if failed/expired/cancelled → drop checkpoint and resubmit
    # 2. else upload JSONL from memory (files, purpose="batch") → create batch(endpoint="/v1/embeddings") → checkpoint
    # 3. poll until terminal (report request_counts.completed/total)
    # 4. status != completed → raise with batch_id
    # 5. download output_file_id → {custom_id: vector}, row errors, prompt_tokens
    # 6. download error_file_id → pre-processing rejections (silent if ignored!)
    # 7. pop checkpoint; return {batch_id, vectors, errors, prompt_tokens}
```

Error policy: any `custom_id` in `errors` means that chunk is **missing**. The run must fail loudly if a missing chunk is required; never silently index a partial corpus, because it corrupts Recall and Hit Rate. Retrying only the failed ids is allowed once.

### 7.1 Pre-embed phase (grid sweeps): the core win

```
expand sweep → runs[]
group runs by embedder identity
for each identity group:
    chunks  = union of chunk texts across all chunk configs used by those runs
    queries = all golden-master questions (already known)
    embed_documents(chunks)   # one batch job (cache-miss only)
    embed_queries(queries)    # one batch job (cache-miss only)
then run trials as today — every embed call is a cache hit
```

### 8. Failure handling

| Situation | Behaviour |
|---|---|
| 401/403/404 from DoubleWord | Mark provider unavailable for this sweep; skip remaining DoubleWord runs with a reason |
| Batch `failed`/`expired` | Resubmit once; second failure → runs `FAILED` with the batch id in the error |
| Process killed mid-batch | Checkpoint holds `batch_id`; on restart, resume polling instead of resubmitting |
| Pre-processing errors (`error_file_id`) | Surface per chunk; the run fails if any required chunk is missing |
| Chunk > `max_input_tokens` | Plan-time validation error naming the chunk config |

### 11. ADR skeleton: DoubleWord as a batch-priced embedding provider

- **Context:** chunking × embedding sweeps re-embed corpora repeatedly; batch-priced embeddings cut this cost about 6× against voyage-3-large; grid sweeps know all texts up front.
- **Decision:** add a DoubleWord (Qwen3-Embedding-8B) provider with realtime/batch modes, a provider-agnostic content-addressed cache and a pre-embed phase; opt in via API key.
- **Verification results:** V1–V9 table.
- **Consequences:** + cheap re-embedding, MRL dim axis possible, cost metrics for Pareto. − a single model from this provider; realtime is limited; batch latency (minutes to hours) makes pre-embed a blocking phase; per-dim vector indexes count against Atlas M0 index limits.
- **Alternatives considered:** OpenAI batch (pricier), local Qwen3-Embedding via HuggingFace (breaks "no heavy install" at 8B; 0.6B is a future local option), Voyage only (status quo).

### 13. Open questions (answered 2026-09-24; see DECISIONS #189–#194)

1. Bayesian handling → **pre-embed the declared space** (#193).
2. Cache backend → local SQLite, no new dependency (#194).
3. Cache scope → **shared across sweeps** (#194).
4. `requires_env` → **not added**; reuse the fail-closed preflight guard pattern (#192).
5. Reranker gap → out of scope; the question to DoubleWord about a Qwen3 reranker stays with the owner.

### Appendix A: lessons carried over from `playgroup_202602_docextract`

| Lesson | Applied in |
|---|---|
| Checkpoint `{batch_id, submitted_at}` before polling; resume on restart | 48B |
| Two error channels: `output_file_id` row errors **and** `error_file_id` pre-processing rejections | 48B |
| 5 MB per JSONL line limit | 48B `build_jsonl` |
| Poll interval 10 s | 48B settings default |
| Upload JSONL from memory (`(name, bytes)`), no temp files | 48B |
| Track unavailable models persistently; don't retry permission errors | 48A (fail fast on 401/403/404) |
| DoubleWord docs vs API model IDs have diverged before; verify the exact ID | 48A T0 spike |
| Analytics endpoint is DoubleWord-specific; call it with httpx and degrade gracefully | 48B cost |
