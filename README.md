# rag-params-finder

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2.6+-E92063?logo=pydantic&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)

**RAG parameter sweep experimentation tool** — systematically evaluate embedding models, chunking strategies, and retrieval methods using MongoDB Atlas Vector Search. Supports both Voyage AI (hosted) and local sentence-transformers models (no API key needed).

---

## Screenshots

| Screen | Description |
|:---:|:---|
| ![Experiments list](docs/images/01-experiments-list.png) | **Experiments list** — all submitted sweeps with status badges and per-experiment run counts |
| ![Experiment detail](docs/images/02-experiment-detail.png) | **Experiment detail** — metric cards, live phase indicator dots, and the full runs table |
| ![Search Explorer](docs/images/03-search-explorer.png) | **Search Explorer** — best-parameters card, ranked config cards with score bars, per-query results |

---

## Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+, MongoDB Atlas account (free tier)

```bash
# 1. Clone and install
git clone <repository-url>
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

# 2. Configure
cp .env.example .env
# Edit .env: add MONGODB_URI (required) and VOYAGE_API_KEY (optional — local models need no key)

# 3. Start server + dashboard
uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2

# 4. Run an experiment
rag-params-finder run --config configs/example-local.yaml   # no API key needed
rag-params-finder run --config configs/example-voyage-ai.yaml  # requires VOYAGE_API_KEY
```

Open `http://localhost:5173` to watch live progress and explore results.

---

## Key Features

- **5 chunking methods**: Fixed, Recursive, Token, Sentence, Semantic
- **3 retrieval methods**: Dense (vector search), Sparse (BM25), Hybrid (70/30 weighted)
- **Voyage AI models**: `voyage-3.5-lite`, `voyage-3.5`, `voyage-context-3` + `rerank-2.5-lite`
- **Local models** (no API key, no rate limits): `all-MiniLM-L6-v2` + `cross-encoder/ms-marco-MiniLM-L-6-v2` via sentence-transformers
- **Multi-format data loading**: PDF, TXT, Markdown, CSV — files or directories (recursive scan)
- **URL-capable queries file**: local path or URL (auto-downloaded and cached)
- **Cartesian sweep expansion**: one YAML config → N models × M methods × P sizes × Q overlaps runs
- **Live phase tracking**: QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE
- **Rich dashboard**: metric cards, color-coded status badges, phase indicator dots, search explorer

---

## Documentation

| Document | Description |
|----------|-------------|
| [Reference Guide](docs/REFERENCE.md) | Detailed setup, annotated configs, dashboard guide, full troubleshooting |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, modules, collections |
| [ADR-001](docs/adr/ADR-001-two-process-architecture.md) | Why CLI + Server (two-process) |
| [ADR-002](docs/adr/ADR-002-voyage-and-local-providers.md) | Why dual providers (Voyage AI + local) |
| [ADR-003](docs/adr/ADR-003-mongodb-atlas-vector-store.md) | Why MongoDB Atlas over Pinecone/Weaviate |
| [Progress](docs/PROGRESS.md) | Slice status, forward roadmap, decision log |

---

## Architecture

```
┌──────────────┐    HTTP POST       ┌─────────────────────────────────┐
│  Python CLI  │ ──/experiments──▶  │  FastAPI Server                 │
│  (thin)      │                    │  • Sweep expansion              │
│              │ ◀──polling reads── │  • Data loading (PDF/TXT/MD/CSV)│
│  --detach:   │                    │  • Chunking (5 methods)         │
│   skip       │                    │  • Embedding (local/Voyage)     │
│   polling    │                    │  • Atlas Vector Search          │
│              │                    │  • Reranking (local/Voyage)     │
└──────────────┘                    └─────────────┬───────────────────┘
                                                  │
                                                  ▼
                                     ┌─────────────────────────────────┐
                                     │   MongoDB Atlas                 │
                                     │   • chunks (vector index)       │
                                     │   • experiments                 │
                                     │   • run_status                  │
                                     │   • results                     │
                                     └─────────────────────────────────┘
```

---

## Configuration

See `configs/example-local.yaml` (local models, no key needed) or `configs/example-voyage-ai.yaml` (Voyage AI).

**Minimal config** — local models, no API key:

```yaml
experiment_name: my-first-experiment

data_paths:
  - ./input_data/pdfs/sample.pdf    # or a directory — scanned recursively

queries_file: ./configs/questions.example.json  # local path or URL

embedding:
  provider: local
  models:
    - all-MiniLM-L6-v2

chunking:
  methods: [recursive]
  params:
    chunk_sizes: [512]
    overlaps: [50]

retrieval:
  methods: [dense]
  top_k_initial: 20
  top_k_final: 5
  rerank_provider: local
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

Place source documents in `input_data/` (gitignored). Supported formats: `.pdf`, `.txt`, `.md`, `.csv`.

---

## Models

| Model | Type | Dimensions | Provider |
|-------|------|-----------|----------|
| `all-MiniLM-L6-v2` | Embedding | 384 | Local (sentence-transformers, ~23 MB) |
| `voyage-3.5-lite` | Embedding | 1024 | Voyage AI |
| `voyage-3.5` | Embedding | 1024 | Voyage AI |
| `voyage-context-3` | Embedding | 1024 | Voyage AI |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker | — | Local (sentence-transformers, ~23 MB) |
| `rerank-2.5-lite` | Reranker | — | Voyage AI |

Local models are downloaded from HuggingFace on first use and cached in `~/.cache/huggingface/`. The `provider` field in the config is the source of truth — the system validates that model names match the declared provider at load time.

**Atlas vector indexes**: local models need `vector_index_384` (384-dim); Voyage models need `vector_index_1024` (1024-dim). See [Troubleshooting](#troubleshooting) for the index JSON.

---

## Chunking Methods

| Method | Algorithm | Best For |
|--------|-----------|----------|
| `recursive` | LangChain `RecursiveCharacterTextSplitter` — splits on `\n\n` → `\n` → space | General prose (default) |
| `fixed` | Fixed-size character windows with configurable overlap | Baseline comparisons |
| `token` | tiktoken-based splits at token boundaries | Token-budget-sensitive pipelines |
| `sentence` | NLTK sentence tokenizer | Narrative text, Q&A pairs |
| `semantic` | Groups sentences by embedding similarity; Voyage-aware | Topic-coherent chunks |

## Retrieval Methods

| Method | Algorithm | Strengths |
|--------|-----------|-----------|
| `dense` | Cosine similarity on embeddings (Atlas Vector Search) | Semantic meaning, handles paraphrasing |
| `sparse` | BM25 full-text search (Atlas Search) | Keyword precision, rare/domain-specific terms |
| `hybrid` | Weighted combination — 70% dense + 30% sparse | Balanced recall and precision |

## Reranking

After initial retrieval returns `top_k_initial` candidates, a cross-encoder re-scores each chunk and reorders the final `top_k_final` results.

| Option | Model | Requires |
|--------|-------|----------|
| Local | `cross-encoder/ms-marco-MiniLM-L-6-v2` (~23 MB) | No API key |
| Voyage | `rerank-2.5-lite` or `rerank-2.5` | `VOYAGE_API_KEY` in `.env` |

---

## CLI Usage

```bash
# Submit and watch progress
rag-params-finder run --config configs/example-local.yaml

# Submit and detach (check dashboard for status)
rag-params-finder run --config configs/example-local.yaml --detach

# Manual recovery of interrupted runs
rag-params-finder recover --experiment-id <id> --auto
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthz` | Health check |
| POST | `/experiments` | Submit experiment sweep |
| GET | `/experiments` | List all experiments |
| GET | `/experiments/{id}` | Get experiment details |
| GET | `/experiments/{id}/results` | Get query results |
| GET | `/runs/{id}/status` | Get run status (for polling) |
| POST | `/recover` | Manual recovery |

Server OpenAPI docs: `http://localhost:8001/docs`

---

## Development

```bash
# Backend quality gates
uv run ruff check .
uv run mypy server/ cli/
uv run pytest

# Frontend quality gates
cd frontend && npm run typecheck && npm run build
```

### Project Structure

```
rag-params-finder/
├── server/              # FastAPI engine
│   ├── main.py          # App entry + boot recovery
│   ├── settings.py      # Centralized pydantic-settings config
│   ├── api/             # Route handlers
│   ├── core/            # Orchestration, chunking, embedding, data loading
│   ├── models/          # Pydantic schemas
│   └── db/              # Atlas connection
├── cli/                 # Python CLI client
├── frontend/            # React dashboard
│   └── src/
├── configs/             # Example YAML and queries
├── input_data/          # User-supplied documents (gitignored)
└── docs/                # Architecture, slices, ADRs
```

---

## Troubleshooting

### Vector index not found

**Symptom**: server logs show `Search index 'vector_index' not found` or queries return no results.

**Fix**: The Atlas vector index must be created manually after provisioning your cluster.

1. Atlas UI → your cluster → **Browse Collections** → `chunks` collection → **Search Indexes** tab
2. **Create Search Index** → JSON Editor → paste one of the index definitions below
3. Wait ~1–2 minutes for the index to build before running queries

**For Voyage models** (1024-dim) — name: `vector_index_1024`:
```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine" },
    { "type": "filter", "path": "experiment_id" },
    { "type": "filter", "path": "embedding_model" }
  ]
}
```

**For local models** (384-dim) — name: `vector_index_384`:
```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine" },
    { "type": "filter", "path": "experiment_id" },
    { "type": "filter", "path": "embedding_model" }
  ]
}
```

### Dimension mismatch (local vs Voyage models)

**Symptom**: vector search fails with a dimension error, or results are nonsensical.

**Cause**: local models produce 384-dim embeddings; Voyage models produce 1024-dim. Vectors from different models cannot be compared.

**Fix**: Each embedding model needs its own Atlas vector index (`vector_index_384` or `vector_index_1024`). Never mix providers within the same experiment config.

### Voyage API rate limit hit

**Symptom**: `voyageai.error.RateLimitError` in server logs; run status shows `failed`.

**Fix**: Check usage at [dash.voyageai.com/usage](https://dash.voyageai.com/usage). Free tier: 300 RPM / 1 M TPM. Set `VOYAGE_RPM_LIMIT` and `VOYAGE_TPM_LIMIT` in `.env` to throttle requests, or switch to `provider: local` for testing.

### Dashboard stuck on "Loading…"

**Symptom**: browser shows a loading spinner or "Failed to fetch" error.

| Cause | Fix |
|-------|-----|
| Server not running | Start with `uvicorn server.main:app --reload --port 8001`; check `http://localhost:8001/healthz` |
| Wrong port | Verify `SERVER_URL` in `.env` matches the uvicorn port |
| CORS error | Hard-refresh (`Cmd+Shift+R`); restart server |

### Chunks not appearing in Atlas

**Symptom**: experiment shows `complete` but the `chunks` collection is empty.

**Check**: server logs for `pymongo` errors, Atlas UI → **Metrics → Storage** for quota (M0 limit: 512 MB).

---

## Built With

**Backend**
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI_server-499848?logo=gunicorn&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![PyMongo](https://img.shields.io/badge/PyMongo-4.6+-47A248?logo=mongodb&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain_Text_Splitters-1C3C3C?logoColor=white)
![HTTPX](https://img.shields.io/badge/HTTPX-async_HTTP-2C2D72?logoColor=white)
![pypdf](https://img.shields.io/badge/pypdf-PDF_parsing-00897B?logoColor=white)

**CLI**
![Typer](https://img.shields.io/badge/Typer-CLI_framework-009688?logo=fastapi&logoColor=white)
![Rich](https://img.shields.io/badge/Rich-terminal_UI-FAE04E?logoColor=black)

**Frontend**
![React](https://img.shields.io/badge/React_19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)

**AI/ML**
![Voyage AI](https://img.shields.io/badge/Voyage_AI-embeddings_%26_reranking-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-local_models-FF9D00?logo=huggingface&logoColor=white)
![NLTK](https://img.shields.io/badge/NLTK-sentence_chunking-154F5B?logoColor=white)

**Dev Tools**
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logoColor=white)
![ruff](https://img.shields.io/badge/ruff-linter-D7FF64?logoColor=black)
![mypy](https://img.shields.io/badge/mypy-type_checker-2A6DB2?logoColor=white)
![pytest](https://img.shields.io/badge/pytest-testing-0A9EDC?logo=pytest&logoColor=white)
![ESLint](https://img.shields.io/badge/ESLint-4B32C3?logo=eslint&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)

---

## License

MIT

---

## Credits

Inspired by [pre-rag-explorer-dashboard](https://github.com/neomatrix369/pre-rag-explorer-dashboard) — a browser-based RAG exploration tool.

**Differences from the inspiration**:
- Server-based (not browser-only)
- MongoDB Atlas (not IndexedDB)
- Voyage AI + local sentence-transformers (not Transformers.js)
- Parameter sweeps across many configs (not single experiments)
- Real semantic chunking with embedding similarity
