# Configuration Reference

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

All YAML fields, sweep expansion rules, and queries file format.

---

## ⚙️ Experiment Config (YAML)

Place config files in `configs/`. Ready-to-run configs:

| Config file | Vector DB | Embedding provider | Chunking | Retrieval | Runs | API key? |
|---|---|---|---|---|---|---|
| `example-mongodb-local.yaml` | MongoDB Atlas | local (all-MiniLM-L6-v2) | all 5 methods | dense · sparse · hybrid | 90 | No |
| `example-mongodb-voyage.yaml` | MongoDB Atlas | Voyage AI (all models) | all 5 methods | dense · sparse · hybrid | 90 | Yes |
| `example-kimchi.yaml` | MongoDB Atlas | Kimchi-hosted embeddings | recursive | dense | 24 | Yes |

Each config is a **full Cartesian sweep**: every combination of embedding model, chunking method, chunk size, overlap, and retrieval method runs as an independent experiment.

### Full annotated config

```yaml
experiment_name: my-sweep           # timestamp suffix added automatically on each submit

data_paths:                          # one or more files and/or directories
  - ./input_data/pdfs/sample.pdf     # individual file
  # - ./input_data/pdfs/             # directory — scanned recursively for .pdf/.txt/.md/.csv

queries_file: ./configs/questions.example.json  # local path or URL
                                                 # URL downloads to ./configs/ on first use and caches

embedding:
  provider: local                    # "local", "voyage", or "kimchi"
  models:
    - all-MiniLM-L6-v2               # models must match the declared provider

chunking:
  methods:
    - recursive                      # one or more: recursive | fixed | token | sentence | semantic
    # - fixed
    # - token
  params:
    chunk_sizes: [256, 512, 1024]    # all sizes × all overlaps = cartesian product of runs
    overlaps: [0, 50]

retrieval:
  methods:
    - dense                          # one or more: dense | sparse | hybrid
    # - hybrid
  top_k_initial: 20                  # candidates passed to the reranker
  top_k_final: 5                     # results returned after reranking
  rerank_provider: local             # "local" or "voyage"
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2

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
runs = embedding.models × chunking.methods × chunking.params.chunk_sizes × chunking.params.overlaps × retrieval.methods
```

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
  methods: [dense]                      # 1 retrieval method
```

→ 1 × 2 × 2 × 2 × 1 = **8 runs**

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
| **Kimchi-hosted** | | | |
| `mistral/codestral-embed` and other prefixed IDs | Runtime | `kimchi` | OpenAI-compatible hosted embeddings — see `model_registry.py` |

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

**Atlas vector index** selection is automatic: local models (384-dim) use `vector_index_384`; Voyage models (1024-dim) use `vector_index_1024`; Kimchi models use the runtime embedding length and route to `vector_index_<dimension>`. All can coexist on the same `chunks` collection.

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

## 🔍 Retrieval Methods

| Method | Algorithm | Strengths |
|---|---|---|
| `dense` | Cosine similarity on embeddings (Atlas Vector Search) | Semantic meaning, handles paraphrasing |
| `sparse` | BM25 full-text search (Atlas Search) | Keyword precision, rare/domain-specific terms |
| `hybrid` | Reciprocal Rank Fusion (RRF) of dense + sparse results | Balanced recall and precision |

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

Use `configs/example-mongodb-local.yaml` — it covers all 5 chunking methods and all 3 retrieval methods with the local model. No Voyage API key needed.

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml
```

For a targeted subset, copy the file and trim the `methods` or `chunk_sizes` lists before running.

To **continue an incomplete sweep** without re-submitting YAML, pause and resume the same experiment (CLI or dashboard) — completed parameter combinations are skipped automatically.

To **re-run only failed combinations inside an existing experiment** *(same `experiment_id`, keep successful runs)*, see the planned workflow in [`../slices/SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md) — today this requires manual YAML reshaping, pause/resume for not-yet-started combos, or a new submit.

---

## 🍜 Kimchi Config

`configs/example-kimchi.yaml` sweeps four OpenAI-family Kimchi models with recursive chunking and dense retrieval. Additional prefixed model IDs are registered in `model_registry.py` (many parked in the YAML until provider availability is confirmed).

```yaml
embedding:
  provider: kimchi
  models:
    - openai/text-embedding-3-large
    - openai/text-embedding-ada-002
    - openai/text-embedding-3-small
    - openai/text-embedding-ada-002-v2

chunking:
  methods: [recursive]
  params:
    chunk_sizes: [256, 512, 1024]
    overlaps: [50, 100]

retrieval:
  methods: [dense]
  top_k_initial: 20
  top_k_final: 5
  rerank_provider: local
  rerank_model: null
```

Kimchi support is embeddings-only. Set `KIMCHI_BASE_URL` and `KIMCHI_API_KEY` server-side in `.env`; do not put secrets in YAML config files.

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

**Rate limits**: Required for Voyage sweep — add payment method + ≥$5 credits, then set Tier 1 limits in `.env`. See [Cloud Account Setup → Voyage step 3](cloud-setup.md#3-unlock-tier-1-rate-limits-required-for-90-run-sweep).

**Example cost** for a 36-run sweep (3 models × 2 methods × 3 chunk sizes × 2 overlaps):
- 1 PDF × ~200 pages × 5 chunks/page = 1,000 chunks/run
- 36 runs × 1,000 chunks × ~100 tokens = 3.6M tokens
- Cost: ~$0.22 at `voyage-3.5-lite` pricing

---

## 👉 See Also

- [Getting Started](getting-started.md) — environment setup and first experiment
- [Cloud Account Setup](cloud-setup.md) — Atlas and Voyage account setup
- [CLI Reference](cli-reference.md) — how to submit a config and monitor runs
- [Dashboard Guide](dashboard-guide.md) — interpreting results and scores
- [Extending the System](../contributor-guide/extending.md) — adding new models or chunking methods
