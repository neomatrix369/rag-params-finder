# Configuration Reference

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

All YAML fields, sweep expansion rules, and queries file format.

---

## ⚙️ Experiment Config (YAML)

Place config files in `configs/`. Three ready-to-run configs are provided, one per vector-DB × provider combination:

| Config file | Vector DB | Embedding provider | Chunking | Retrievers | Runs | API key? |
|---|---|---|---|---|---|---|
| `example-mongodb-local.yaml` | MongoDB Atlas | local (all-MiniLM-L6-v2) | all 5 methods | dense · sparse · hybrid · cross-encoder | 120 | No |
| `example-mongodb-voyage.yaml` | MongoDB Atlas | Voyage AI (voyage-3.5-lite) | all 5 methods | hybrid · dense · sparse · reranker | 40 | Yes |
| `example-mongodb-sie.yaml` | MongoDB Atlas | SIE (bge-m3, stella-v5) | all 5 methods | dense · sparse · hybrid · cross-encoder | 80 | No (remote SIE gateway or optional Docker) |
| `example-mongodb-unified-retrievers.yaml` | MongoDB Atlas | local (all-MiniLM-L6-v2) | 2 methods | dense · sparse · hybrid · cross-encoder | 16 | No |

Each config is a **full Cartesian sweep**: every combination of embedding model, chunking method, chunk size, overlap, and retriever runs as an independent experiment. Each entry in `retrieval.retrievers` creates a separate run — retrievers are never combined in a single run.

### Full annotated config

```yaml
experiment_name: my-sweep           # timestamp suffix added automatically on each submit

data_paths:                          # one or more files and/or directories
  - ./input_data/pdfs/sample.pdf     # individual file
  # - ./input_data/pdfs/             # directory — scanned recursively for .pdf/.txt/.md/.csv

queries_file: ./configs/questions.example.json  # local path or URL
                                                 # URL downloads to ./configs/ on first use and caches

embedding:
  provider: local                    # "local" | "voyage" | "sie" (supported on main); "kimchi" reserved — see extending guide
  models:
    - all-MiniLM-L6-v2               # must match provider: local; sie models need provider: sie (e.g. bge-m3)

> **Using `provider: sie`?** SIE runs as a separate Docker container. `/healthz` returning `ok`
> does **not** mean BGE-M3 is ready — encode may return 503 for many minutes on first start.
> See **[SIE Provider Setup](sie-setup.md)** before your first sweep.

chunking:
  methods:
    - recursive                      # one or more: recursive | fixed | token | sentence | semantic
    # - fixed
    # - token
  params:
    chunk_sizes: [256, 512, 1024]    # all sizes × all overlaps = cartesian product of runs
    overlaps: [0, 50]

retrieval:
  top_k_initial: 20                  # candidates for reranker runs (dense fetch is internal)
  top_k_final: 5                     # final results returned per query
  retrievers:
    # Each entry is one sweep dimension — one retriever per run (never combined).
    - type: dense                    # Atlas Vector Search
    - type: sparse                   # Atlas BM25 full-text
    - type: hybrid                   # Reciprocal Rank Fusion of dense + sparse
    - type: cross_encoder            # Local cross-encoder (no API key)
      provider: local
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
    # - type: reranker               # Voyage reranker (requires API key)
    #   provider: voyage
    #   model: rerank-2.5-lite

execution:
  parallelism: 1                     # use 1 until Slice 16; see "### Parallelism" below
  on_error: continue                 # "continue" (partial results) or "stop" (halt experiment)
```

### Parallelism (`execution.parallelism`)

- **Current behavior**: The value is stored on each experiment *(and visible in the dashboard)* but **`server/core/orchestrator.py` always runs sweep runs sequentially** — values greater than `1` have **no throughput effect** until implemented.
- **Planned work**: **[Slice 16 — Parallel Sweep Runs](../slices/SLICE-16-PARALLEL-SWEEP-RUNS.md)** specifies bounded concurrent execution of `_run_single`, cancellation + `on_error` semantics across workers, Atlas/Voyage rate-limit considerations, and an optional Celery-style queue path for larger deployments.

---

## 🔁 Sweep Expansion

One config YAML expands into a **Cartesian product** of runs:

```
runs = embedding.models × chunking.methods × chunk_sizes × overlaps × retrievers
```

Each `retriever` entry creates a separate run. Retrievers are **never chained** — a run uses exactly one retriever type.

Reranker runs (`cross_encoder`, `reranker`) fetch dense candidates internally (using `top_k_initial`), then rerank to `top_k_final`. This dense fetch is an implementation detail and does not appear as a second retriever on the run.

**Example**:
```yaml
embedding:
  models: [all-MiniLM-L6-v2]           # 1 model
chunking:
  methods: [recursive, fixed]           # 2 methods
  params:
    chunk_sizes: [512, 1024]            # 2 sizes
    overlaps: [0, 50]                   # 2 overlaps
retrieval:
  retrievers:
    - type: dense
    - type: sparse
    - type: hybrid
    - type: cross_encoder
      provider: local
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

→ 1 × 2 × 2 × 2 × 4 = **32 runs** (one run per retriever type per chunking combo)

Each run is tracked independently through the pipeline phases and has its own results.

---

## 🤖 Models

Canonical list: `server/core/model_registry.py` (`EMBEDDING_MODELS`, `RERANKER_MODELS`).

### Embedding models

| Model | Dimensions | Provider | Notes |
|---|---|---|---|
| `all-MiniLM-L6-v2` | 384 | `local` | ~23 MB, no API key |
| **Voyage 4** | | | |
| `voyage-4-large` | 1024 | `voyage` | Flagship; shared 4-series embedding space |
| `voyage-4` | 1024 | `voyage` | General-purpose |
| `voyage-4-lite` | 1024 | `voyage` | Latency/cost optimized |
| **Domain** | | | |
| `voyage-code-3` | 1024 | `voyage` | Code retrieval |
| `voyage-finance-2` | 1024 | `voyage` | Finance domain |
| `voyage-law-2` | 1024 | `voyage` | Legal domain |
| `voyage-context-3` | 1024 | `voyage` | Contextualized chunk API |
| **Voyage 3 (legacy API)** | | | |
| `voyage-3-large` | 1024 | `voyage` | Previous-gen large |
| `voyage-3.5-lite` | 1024 | `voyage` | Previous-gen lite |
| `voyage-3.5` | 1024 | `voyage` | Previous-gen standard |
| `voyage-3` | 1024 | `voyage` | Voyage 3 general |
| `voyage-multilingual-2` | 1024 | `voyage` | Multilingual |

### Reranker models

| Model | Provider | Notes |
|---|---|---|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | `local` | ~23 MB, no API key |
| `rerank-2.5-lite` | `voyage` | Recommended — fastest |
| `rerank-2.5` | `voyage` | Recommended — higher quality |
| `rerank-2-lite` | `voyage` | Legacy |
| `rerank-2` | `voyage` | Legacy |
| `rerank-lite-1` | `voyage` | Legacy |
| `rerank-1` | `voyage` | Legacy |

**Provider/model must match.** The system validates at config load time — a `provider: local` config with a Voyage model name will fail immediately with a clear error.

**Atlas vector index** selection is automatic: local models (384-dim) use `vector_index_384`; Voyage and dense SIE models (1024-dim) use `vector_index_1024`; SPLADE-v3 (30522-dim) uses `vector_index_30522`. Indexes can coexist on the same `chunks` collection — always filter by `embedding_model`.

**Search index preflight:** on submit, the server derives required index names from your config and validates cluster capacity before any run starts:

| `retrieval.methods` | `embedding` provider | Required Atlas Search indexes |
|---|---|---|
| `dense` only | `local` | `vector_index_384` |
| `dense` only | `voyage` | `vector_index_1024` |
| includes `sparse` or `hybrid` | `local` | `vector_index_384` + `text_search_index` |
| includes `sparse` or `hybrid` | `voyage` | `vector_index_1024` + `text_search_index` |

If indexes are missing or M0 quota (3 cluster-wide) is exhausted, submission fails with **HTTP 422**. Use `rag-params-finder indexes list` and `indexes reset` — see [Troubleshooting](troubleshooting.md#-search-index-preflight-failed).

### `voyage-context-3` (contextualized API)

Unlike other Voyage models, `voyage-context-3` uses Voyage's **`contextualized_embed`** API — all chunks from a document segment share embedding context for better retrieval quality.

| Limit | Value | Server behavior |
|---|---|---|
| Per-segment context window | 32,000 tokens | Long documents are split into multiple segments automatically (`server/core/embedder.py`) |
| Per-request total tokens | 120,000 tokens | Multiple segments batched into one API call when under cap |
| Single chunk max | 32,000 tokens | Validated before embed; fails with clear error if `chunk_size` is too large |

**Implications for sweeps**:

- **Other Voyage models are unaffected** — they use standard `client.embed()` with per-chunk batching.
- **Segment boundaries**: chunks in different segments lose cross-segment document context (within-segment context is preserved).
- **Chunk size**: keep `chunk_sizes` well below 32K tokens (the example configs use `[256, 512]` characters/tokens). A single oversized chunk cannot be truncated by Voyage.

See [Troubleshooting — voyage-context-3 token limit](troubleshooting.md#-voyage-context-3-token-limit-exceeded) if embedding fails with a 32K window error.

---

## ✂️ Chunking Methods

| Method | Algorithm | Best For |
|---|---|---|
| `recursive` | LangChain `RecursiveCharacterTextSplitter` — splits on `\n\n` → `\n` → space | General prose (default) |
| `fixed` | Fixed-size character windows with configurable overlap | Baseline comparisons |
| `token` | tiktoken-based splits at token boundaries | Token-budget-sensitive pipelines |
| `sentence` | NLTK sentence tokenizer | Narrative text, Q&A pairs |
| `semantic` | Groups sentences by cosine similarity of `all-MiniLM-L6-v2` embeddings; `overlap` is ignored | Topic-coherent chunks |

---

## 🔍 Retrieval Configuration

**Unified retriever format** (recommended):
```yaml
retrieval:
  top_k_initial: 20  # Candidate pool for reranker runs
  top_k_final: 5     # Final results per query
  retrievers:
    - type: dense
    - type: sparse
    - type: hybrid
    - type: cross_encoder
      provider: local
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

Each list entry is one sweep dimension. To compare dense vs sparse vs hybrid, list all three — the sweep runs each independently.

**Retriever types**:

| Type | Algorithm | Strengths | Requires provider/model? |
|---|---|---|---|
| `dense` | Cosine similarity on embeddings (Atlas Vector Search) | Semantic meaning, handles paraphrasing | No |
| `sparse` | BM25 full-text search (Atlas Search) | Keyword precision, rare/domain-specific terms | No |
| `hybrid` | Reciprocal Rank Fusion (RRF) of dense + sparse results | Balanced recall and precision | No |
| `reranker` | Voyage reranking API | High-quality reranking, API-based | Yes |
| `cross_encoder` | Local cross-encoder model | Fast reranking, no API key | Yes |

**One retriever per run.** Do not list multiple retrievers expecting them to chain — each entry becomes its own run in the Cartesian sweep.

**Time vs storage:** Adding `sparse` or `hybrid` increases run count and wall-clock time (extra query passes over the same stored chunks). They use the shared `text_search_index` and do not add embedding dimensions. Disk growth on M0 comes mainly from the chunking grid (methods × sizes × overlaps), not from listing more traditional retriever types.

**Old format** (deprecated, auto-migrated):
```yaml
retrieval:
  methods: [dense, sparse]
  retrieval_provider: local        # DEPRECATED: use retrievers instead
  retrieval_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```
Old configs still work—they're automatically converted to the new `retrievers` format. The deprecated `methods`, `retrieval_provider`, and `retrieval_model` fields are synthesized from `retrievers` for backward compatibility.

---

## 📋 Queries File Format

The `queries_file` field accepts a local path or a URL (downloaded and cached on first use).

**Persona-based format**:
```json
[
  {
    "persona_id": "current-student",
    "queries": [
      {
        "text": "How much can I borrow in student loans?",
        "focus": "loan_limits"
      },
      {
        "text": "What are the Pell Grant eligibility requirements?",
        "focus": "grants"
      }
    ]
  },
  {
    "persona_id": "prospective-student",
    "queries": [
      {
        "text": "What financial aid is available for first-year students?",
        "focus": "overview"
      }
    ]
  }
]
```

Each query is executed independently per run. Results are stored with `persona_id` and `focus` for filtering in the Search Explorer.

---

## 🏠 Quick Start (No API Key)

Use `configs/example-mongodb-local.yaml` — it covers all 5 chunking methods and all traditional retrieval methods (dense, sparse, hybrid) plus local cross-encoder reranking. No Voyage API key needed. **120 runs** — mostly wall-clock time; sparse/hybrid query existing chunk text (BM25/RRF) and do not add embedding storage beyond each run’s chunks. For a shorter sweep, use `example-mongodb-unified-retrievers.yaml` (16 runs).

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml
```

For a targeted subset, copy the file and trim the `methods` or `chunk_sizes` lists before running.

## SIE Quick Start (Open-Source Embeddings)

Use `configs/example-mongodb-sie.yaml` — same chunking/retriever coverage as the local example, with **2 SIE models** (bge-m3, stella-v5). **80 runs** — SIE encode is slower than Voyage API; use `--detach` and monitor the dashboard.

### SIE environment variables

| Variable | Purpose |
|---|---|
| `SIE_ENABLED` | **On/off** — `true` enables the SIE provider; same flag for remote and local Docker |
| `SIE_ENDPOINT` | **Where** — remote gateway URL or `http://localhost:8720` for self-hosted Docker |
| `SIE_API_KEY` | **Auth** — Bearer token when the gateway requires it; usually omitted for local Docker |

**If you have a remote SIE gateway** (recommended): set all three in `.env` (API key as required) — **no Docker**.

**Otherwise:** run optional self-hosted Docker, then set `SIE_ENABLED=true` and `SIE_ENDPOINT=http://localhost:8720` — see **[SIE Provider Setup](sie-setup.md)**.

Also requires `vector_index_1024` + `text_search_index` on Atlas. Full checklist: **[Cloud Account Setup → SIE sweep](cloud-setup.md#sie-sweep--example-mongodb-sieyaml)**.

```bash
rag-params-finder run --config configs/example-mongodb-sie.yaml
```

To **continue an incomplete sweep** without re-submitting YAML, pause and resume the same experiment (CLI or dashboard) — completed parameter combinations are skipped automatically.

To **re-run only failed combinations inside an existing experiment** *(same `experiment_id`, keep successful runs)*, see the planned workflow in [`../slices/SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md) — today this requires manual YAML reshaping, pause/resume for not-yet-started combos, or a new submit.

---

## 💰 Voyage AI Cost Estimates



| Model | Cost | Notes |
|---|---|---|
| `voyage-4-lite` | $0.02 / 1M tokens | Cheapest current-gen embedding |
| `voyage-4` | $0.06 / 1M tokens | Balanced |
| `voyage-4-large` | $0.12 / 1M tokens | Highest quality |
| `voyage-context-3` | $0.18 / 1M tokens | Contextualized chunks |
| `voyage-3.5-lite` | $0.02 / 1M tokens | Legacy lite |
| `rerank-2.5-lite` | $0.02 / 1M tokens | Cheapest reranker |

**Rate limits**: Required for Voyage sweep — add payment method + ≥$5 credits, then set Tier 1 limits in `.env`. See [Cloud Account Setup → Voyage step 3](cloud-setup.md#3-unlock-tier-1-rate-limits-required-for-40-run-voyage-sweep).

**Example cost** for a 36-run sweep (3 models × 2 methods × 3 chunk sizes × 2 overlaps):
- 1 PDF × ~200 pages × 5 chunks/page = 1,000 chunks/run
- 36 runs × 1,000 chunks × ~100 tokens = 3.6M tokens
- Cost: ~$0.22 at `voyage-3.5-lite` pricing

---

## ⚙️ Environment Variables (`.env`)

Create a `.env` file in the project root to configure server behavior:

```bash
# MongoDB Atlas (REQUIRED)
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/rag_params_finder

# Voyage AI (OPTIONAL — only if using Voyage models)
VOYAGE_API_KEY=vo-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Voyage rate limits — free tier defaults (override for Tier 1 Voyage sweep)
VOYAGE_RPM_LIMIT=3        # Requests per minute (free tier)
VOYAGE_TPM_LIMIT=10000    # Tokens per minute (free tier)
# Tier 1 (example-mongodb-voyage.yaml): VOYAGE_RPM_LIMIT=2000 VOYAGE_TPM_LIMIT=16000000

# SIE (OPTIONAL — only if using provider: sie or POST /api/v1/sweep)
# SIE_ENABLED = on/off (same for remote and local Docker)
# SIE_ENDPOINT = where to connect | SIE_API_KEY = auth when required
# Path A — remote gateway (no local Docker):
SIE_ENABLED=false
# SIE_ENDPOINT=https://your-sie-gateway.example.com
# SIE_API_KEY=your_gateway_token
# Path B — self-hosted Docker on :8720 (only when no remote gateway):
# SIE_ENDPOINT=http://localhost:8720
# SIE_ENDPOINT=http://host.docker.internal:8720   # server in Docker, SIE on host
# HF_TOKEN=hf_...   # Docker path only — HuggingFace token for container model downloads

# Aim experiment tracking (OPTIONAL — UI via ./scripts/aim-ui.sh)
# AIM_REPO=.aim      # Docker sets /app/.aim automatically

# MongoDB /healthz ping timeout (ms) — keep below Docker healthcheck (10s)
# HEALTH_CHECK_MONGODB_TIMEOUT_MS=5000

# Search result ranking tiebreaker (NEW in v0.11.0)
# When multiple configs achieve the same max score, this setting determines
# which average metric is used for ranking.
#
# Options:
#   - "query_avg" (default, RECOMMENDED): Weighted per-query average
#     Each query contributes equally, preventing queries with many results
#     from dominating the average. Fairer representation of config performance.
#
#   - "chunk_avg" (legacy): Unweighted chunk-level average
#     Each chunk contributes equally. Queries that return more chunks have
#     more weight. Use only if you need backward compatibility.
#
TIEBREAKER_METRIC=query_avg

# Server URL (used by CLI)
SERVER_URL=http://localhost:8001

# Recovery on boot (auto-retry interrupted runs)
RECOVER_ON_BOOT=false

# Logging
LOG_LEVEL=INFO  # DEBUG for verbose output

# Atlas Admin API (OPTIONAL — for cluster quota display in dashboard)
ATLAS_PUBLIC_KEY=your-atlas-public-key
ATLAS_PRIVATE_KEY=your-atlas-private-key
ATLAS_GROUP_ID=24-char-project-id
ATLAS_CLUSTER_NAME=YourClusterName  # leave blank to auto-detect from MONGODB_URI

# Manual storage limit override (MB)
# When > 0, skips Atlas API auto-detect
MONGODB_STORAGE_LIMIT_MB=0

# CORS Configuration (ADVANCED — for production deployment)
# Comma-separated list of allowed origins. Defaults work for local development.
# CORS_ORIGINS=http://localhost:5374,http://127.0.0.1:5374,http://localhost:3000
# CORS_ALLOW_LOCALHOST_ORIGIN_REGEX=true  # Auto-allow localhost/127.0.0.1/[::1] on any port
```

**DO NOT commit `.env` to git** — it's already in `.gitignore`.

### Query Avg vs Chunk Avg: Which to Use?

**Use `query_avg` (default)** unless you have a specific reason not to. It's fairer because:

| Scenario | Chunk Avg (unweighted) | Query Avg (weighted) |
|---|---|---|
| Query 1 returns 5 chunks (scores: 100, 100, 95, 90, 85) | Avg = 94% | Avg = 94% |
| Query 2 returns 3 chunks (scores: 80, 75, 70) | Avg = 75% | Avg = 75% |
| **Combined config avg** | **(100+100+95+90+85+80+75+70)/8 = 87%** ← Query 1 dominates (5/8 = 62.5% weight) | **(94 + 75)/2 = 84.5%** ← Each query weighted equally (50% each) |

Query avg prevents high-scoring queries with many results from hiding poorly-performing queries with few results.

**When to use `chunk_avg`**: You have existing experiments ranked with the old method and want consistency for comparison. New experiments should use `query_avg`.

### CORS Configuration (Advanced)

**For production deployment only.** Local development defaults work out of the box.

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:5374,http://127.0.0.1:5374,http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of allowed origins for CORS |
| `CORS_ALLOW_LOCALHOST_ORIGIN_REGEX` | `true` | When true, automatically allow localhost/127.0.0.1/[::1] on any port via regex |
| `SIE_ENABLED` | `false` | **Master on/off** for SIE — not local-vs-remote; set `true` when you want the server to use SIE (either path) |
| `SIE_ENDPOINT` | `http://localhost:8720` | **Where** to connect — remote gateway URL or local Docker (`host.docker.internal:8720` when server is in Docker) |
| `SIE_API_KEY` | — | **Auth** — Bearer token when gateway requires it; usually empty for local Docker |
| `HF_TOKEN` | — | HuggingFace token for **self-hosted Docker only** — not used when pointing at a remote gateway |
| `AIM_REPO` | `.aim` | Path to Aim experiment repo (Docker: `/app/.aim`; UI: `./scripts/aim-ui.sh`) |
| `HEALTH_CHECK_MONGODB_TIMEOUT_MS` | `5000` | MongoDB ping timeout for `/healthz` (ms) |

**When to customize**:
- Deploying the dashboard on a custom domain (e.g., `https://rag-finder.example.com`)
- Running the frontend on a non-standard port in production
- Tightening security by disabling the localhost regex in production

**Example for production**:
```bash
CORS_ORIGINS=https://rag-finder.example.com,https://api.example.com
CORS_ALLOW_LOCALHOST_ORIGIN_REGEX=false  # Disable regex, use explicit list only
```

**Security note**: The regex pattern `^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$` only matches localhost addresses — it does **not** open CORS to arbitrary hosts. Safe for local development; disable for production if using `CORS_ORIGINS` explicitly.

---

## 👉 See Also

- [Getting Started](getting-started.md) — environment setup and first experiment
- [Cloud Account Setup](cloud-setup.md) — Atlas and Voyage account setup
- [CLI Reference](cli-reference.md) — how to submit a config and monitor runs
- [Dashboard Guide](dashboard-guide.md) — interpreting results and scores (including tiebreaker logic)
- [Extending the System](../contributor-guide/extending.md) — adding new models or chunking methods
