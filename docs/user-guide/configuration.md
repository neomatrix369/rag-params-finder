# Configuration Reference

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

All YAML fields, sweep expansion rules, and queries file format.

---

## ⚙️ Experiment Config (YAML)

Place config files in `configs/`. Two examples are provided:
- `configs/example-local.yaml` — local models, no API key needed
- `configs/example-voyage-ai.yaml` — Voyage AI models, requires `VOYAGE_API_KEY`
- `configs/example-kimchi.yaml` — Kimchi-hosted embeddings, requires `KIMCHI_API_KEY`

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
  parallelism: 1                     # only 1 supported currently
  on_error: continue                 # "continue" (partial results) or "stop" (halt experiment)
```

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

| Model | Type | Dimensions | Provider | Notes |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | Embedding | 384 | `local` | ~23 MB, no API key, HuggingFace cached |
| `voyage-3.5-lite` | Embedding | 1024 | `voyage` | Cheapest Voyage embedding |
| `voyage-3.5` | Embedding | 1024 | `voyage` | Higher accuracy |
| `voyage-context-3` | Embedding | 1024 | `voyage` | Long-context optimized |
| `mistral/codestral-embed` and other prefixed IDs | Embedding | Runtime | `kimchi` | Kimchi-hosted OpenAI-compatible embeddings |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker | — | `local` | ~23 MB, no API key |
| `rerank-2.5-lite` | Reranker | — | `voyage` | Fastest Voyage reranker |
| `rerank-2.5` | Reranker | — | `voyage` | Higher accuracy reranker |

**Provider/model must match.** The system validates at config load time — a `provider: local` config with a Voyage model name will fail immediately with a clear error.

**Atlas vector index** selection is automatic: local models (384-dim) use `vector_index_384`; Voyage models (1024-dim) use `vector_index_1024`; Kimchi models use the runtime embedding length and route to `vector_index_<dimension>`. All can coexist on the same `chunks` collection.

---

## ✂️ Chunking Methods

| Method | Algorithm | Best For |
|---|---|---|
| `recursive` | LangChain `RecursiveCharacterTextSplitter` — splits on `\n\n` → `\n` → space | General prose (default) |
| `fixed` | Fixed-size character windows with configurable overlap | Baseline comparisons |
| `token` | tiktoken-based splits at token boundaries | Token-budget-sensitive pipelines |
| `sentence` | NLTK sentence tokenizer | Narrative text, Q&A pairs |
| `semantic` | Groups sentences by embedding similarity; Voyage-aware | Topic-coherent chunks |

---

## 🔍 Retrieval Methods

| Method | Algorithm | Strengths |
|---|---|---|
| `dense` | Cosine similarity on embeddings (Atlas Vector Search) | Semantic meaning, handles paraphrasing |
| `sparse` | BM25 full-text search (Atlas Search) | Keyword precision, rare/domain-specific terms |
| `hybrid` | Weighted combination — 70% dense + 30% sparse | Balanced recall and precision |

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

## 🏠 All-Local Config (No API Key)

```yaml
experiment_name: local-sweep

data_paths:
  - ./input_data/pdfs/sample.pdf

queries_file: ./configs/questions.example.json

embedding:
  provider: local
  models:
    - all-MiniLM-L6-v2              # 384-dim; requires vector_index_384 in Atlas

chunking:
  methods: [recursive, fixed]
  params:
    chunk_sizes: [512, 1024]
    overlaps: [0, 50]

retrieval:
  methods: [dense]
  top_k_initial: 20
  top_k_final: 5
  rerank_provider: local
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2

execution:
  on_error: continue
```

---

## 🍜 Kimchi Config

`configs/example-kimchi.yaml` sweeps the Kimchi-hosted embedding catalog with prefixed model IDs such as `mistral/codestral-embed`, `openai/text-embedding-3-large`, and `hosted_vllm/bge-m3`.

```yaml
embedding:
  provider: kimchi
  models:
    - mistral/codestral-embed
    - openai/text-embedding-3-large

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
| `voyage-3.5-lite` | $0.06 / 1M tokens | Cheapest embedding |
| `voyage-3.5` | $0.12 / 1M tokens | Higher accuracy |
| `rerank-2.5-lite` | $0.02 / 1K queries | Cheapest reranker |

**Free tier limits**: 300 RPM, 1M TPM. Set `VOYAGE_RPM_LIMIT` and `VOYAGE_TPM_LIMIT` in `.env` to throttle requests to match your tier.

**Example cost** for a 36-run sweep (3 models × 2 methods × 3 chunk sizes × 2 overlaps):
- 1 PDF × ~200 pages × 5 chunks/page = 1,000 chunks/run
- 36 runs × 1,000 chunks × ~100 tokens = 3.6M tokens
- Cost: ~$0.22 at `voyage-3.5-lite` pricing

---

## 👉 See Also

- [Getting Started](getting-started.md) — environment setup and Atlas vector index creation
- [CLI Reference](cli-reference.md) — how to submit a config and monitor runs
- [Dashboard Guide](dashboard-guide.md) — interpreting results and scores
- [Extending the System](../contributor-guide/extending.md) — adding new models or chunking methods
