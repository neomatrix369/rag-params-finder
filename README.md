# rag-params-finder

**RAG parameter sweep experimentation tool** — systematically evaluate embedding models, chunking strategies, and retrieval methods using MongoDB Atlas Vector Search. Supports both Voyage AI (hosted) and local sentence-transformers models.

## Overview

`rag-params-finder` is a two-process system (Python CLI + FastAPI server + React dashboard) for ML engineers to run parameter-sweep experiments on RAG pipelines and visualize results.

### What it does

1. Engineer configures experiment sweeps in YAML (embedding models × chunking methods × retrieval methods)
2. CLI submits experiment to FastAPI server
3. Server orchestrates: data loading (PDF/TXT/MD/CSV) → chunking → embedding (local or Voyage) → Atlas vector storage → query execution → reranking (local or Voyage)
4. React dashboard displays live experiment status and results

### Key Features

- **Multi-format data loading**: PDF, TXT, Markdown, CSV — files and/or directories (recursive scan)
- **5 chunking methods**: Fixed, Recursive, Token, Sentence, Semantic (Voyage-aware)
- **Voyage AI embedding models**: voyage-3.5-lite, voyage-3.5, voyage-context-3
- **Free/local embedding models**: all-MiniLM-L6-v2 via sentence-transformers (no API key, no rate limits)
- **3 retrieval methods**: Dense (vector search), Sparse (BM25), Hybrid (weighted combination)
- **Voyage reranking**: rerank-2.5-lite for top-K refinement
- **Free/local reranking**: cross-encoder/ms-marco-MiniLM-L-6-v2 via sentence-transformers
- **URL-capable queries**: Queries file can be a local path or URL (auto-downloaded and cached)
- **Centralized settings**: pydantic-settings-based config from `.env` or environment
- **Auto-timestamped experiments**: Each run gets a unique timestamp suffix
- **Live progress tracking**: Phase-based status updates with visual progress indicators
- **Rich experiment dashboard**: Metric cards, status badges, color-coded runs table
- **MongoDB Atlas Vector Search**: Production-grade vector storage and retrieval

---

## Screenshots

| Screen | Description |
|---|---|
| ![Experiments list](docs/images/01-experiments-list.png) | **Experiments list** — all submitted sweeps with status badges (complete / running / failed / partial) and per-experiment run counts |
| ![Experiment detail](docs/images/02-experiment-detail.png) | **Experiment detail** — metric cards (total / successful / failed runs), live phase indicator dots (QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE), and the full runs table |
| ![Search Explorer](docs/images/03-search-explorer.png) | **Search Explorer** — best-parameters card with overall relevance score, ranked config cards with score bars, and per-query detailed results |

---

## Quickstart

### Prerequisites

1. **Python 3.12+** — Install via [python.org](https://www.python.org/downloads/) or pyenv
2. **Node.js 22+** — Install via [nodejs.org](https://nodejs.org/) or nvm
3. **MongoDB Atlas account** (free tier sufficient)
   - Create cluster at [cloud.mongodb.com](https://cloud.mongodb.com/)
   - Note: M0 (free tier) supports vector search
4. **Voyage AI API key** *(only if using Voyage models — local models need no key)*
   - Get free key at [dash.voyageai.com](https://dash.voyageai.com/)

### 1. Clone and Install

```bash
git clone <repository-url>
cd rag-params-finder

# Install Python dependencies (using uv for speed)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials:
#   VOYAGE_API_KEY=<your-key>
#   MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/<db>
#   SERVER_URL=http://localhost:8001
```

### 3. Start the Server

```bash
# Terminal 1: FastAPI server
uvicorn server.main:app --reload --port 8001
```

Server starts at `http://localhost:8001`. Visit `/docs` for OpenAPI documentation.

### 4. Start the Dashboard (Optional)

```bash
# Terminal 2: React dashboard
cd frontend
npm run dev
```

Dashboard runs at `http://localhost:5173`.

### 5. Add Input Data

Place your source documents in the `input_data/` directory (gitignored):

```bash
cp /path/to/my-document.pdf input_data/pdfs/
```

Then reference them in your config YAML:

```yaml
data_paths:
  - ./input_data/pdfs/my-document.pdf   # individual file
  # - ./input_data/pdfs/                # or a directory — scans recursively
```

Supported formats: `.pdf`, `.txt`, `.md`, `.csv`

### 6. Run an Experiment

```bash
# Terminal 3: CLI — local models (no API key needed)
rag-params-finder run --config configs/example-local.yaml

# Or with Voyage AI models (requires VOYAGE_API_KEY in .env)
rag-params-finder run --config configs/example-voyage-ai.yaml
```

The CLI will:
- Submit experiment to server (experiment name gets a timestamp suffix automatically)
- Display experiment ID and run IDs
- Poll run progress live (use `--detach` to skip polling)

### 7. View Results in the Dashboard

Open `http://localhost:5173` in your browser:

1. The **Experiments list** shows your submitted experiment with a status badge
2. Click a row to open the **detail screen** — phase indicator dots show each run's progress (PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE)
3. Once runs finish, drill into per-query results to compare dense vs rerank scores

---

## Architecture

```
┌──────────────┐    HTTP POST       ┌─────────────────────────────────┐
│  Python CLI  │ ──/experiments──▶  │  FastAPI Server (engine)        │
│  (thin)      │                    │  • Sweep expansion              │
│              │ ◀──polling reads── │  • Data loading (PDF/TXT/MD/CSV)│
│  --detach:   │                    │  • Chunking (LangChain+custom)  │
│   skip       │                    │  • Embedding (local/Voyage)     │
│   polling    │                    │  • Atlas Vector Search          │
│              │                    │  • Reranking (local/Voyage)     │
└──────────────┘                    │  • Run status tracking          │
                                    └─────────────┬───────────────────┘
                                                  │
                                                  ▼
                                     ┌─────────────────────────────────┐
                                     │   MongoDB Atlas                 │
                                     │   • chunks (vector index)       │
                                     │   • experiments                 │
                                     │   • run_status                  │
                                     │   • collections, queries        │
                                     │   • results                     │
                                     └─────────────────────────────────┘
```

---

## Configuration

See `configs/example-local.yaml` (local models) or `configs/example-voyage-ai.yaml` (Voyage AI) for complete examples.

**Minimal config** (local, no API key):

```yaml
experiment_name: my-first-experiment  # timestamp suffix added automatically on each run

data_paths:                            # list of files and/or directories
  - ./input_data/pdfs/sample.pdf       # individual file
  # - ./input_data/pdfs/               # or a directory — scans recursively for .pdf/.txt/.md/.csv

queries_file: ./configs/questions.example.json  # local path or URL (downloaded to ./configs/ on first use)

embedding:
  provider: local                      # "local" or "voyage"
  models:
    - all-MiniLM-L6-v2

chunking:
  methods:
    - recursive
  params:
    chunk_sizes: [512]
    overlaps: [50]

retrieval:
  methods:
    - dense
  top_k_initial: 20
  top_k_final: 5
  rerank_provider: local               # "local" or "voyage"
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

**Queries file** (persona-based):

```json
{
  "personas": [
    {
      "id": "current-student",
      "role": "Current Student",
      "description": "Currently enrolled, navigating financial aid.",
      "questions": [
        { "text": "How much can I borrow?", "focus": "General" }
      ]
    }
  ]
}
```

### Free/Local Models (No API Key)

You can run experiments entirely offline using local embedding and reranking models from the `sentence-transformers` package. No Voyage API key or rate limits apply.

| Model | Type | Dimensions | Size | Provider |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | Embedding | 384 | ~23MB | Local (sentence-transformers) |
| `voyage-3.5-lite` | Embedding | 1024 | API | Voyage AI |
| `voyage-3.5` | Embedding | 1024 | API | Voyage AI |
| `voyage-context-3` | Embedding | 1024 | API | Voyage AI |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker | - | ~23MB | Local (CrossEncoder) |
| `rerank-2.5-lite` | Reranker | - | API | Voyage AI |

**All-local config** (see `configs/example-local.yaml`):

```yaml
embedding:
  provider: local
  models:
    - all-MiniLM-L6-v2

retrieval:
  rerank_provider: local
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

Models are downloaded from HuggingFace on first use and cached locally. The `provider` field explicitly declares which backend handles embedding/reranking — the system validates that model names match the declared provider at config load time.

**Atlas vector index for local models**: Local models produce 384-dim embeddings (vs 1024-dim for Voyage). You need a separate Atlas vector index named `vector_index_384`:

```json
{
  "fields": [
    { "type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine" },
    { "type": "filter", "path": "experiment_id" },
    { "type": "filter", "path": "embedding_model" }
  ]
}
```

The existing Voyage index should be renamed to `vector_index_1024`.

---

## Chunking Methods

| Method | Algorithm | Best For |
|---|---|---|
| `recursive` | LangChain `RecursiveCharacterTextSplitter` — splits on `\n\n` → `\n` → space (default) | General prose; most documents |
| `fixed` | Fixed-size character windows with configurable overlap | Baseline comparisons; predictable token budgets |
| `token` | tiktoken-based splits at token boundaries | Token-budget-sensitive pipelines (OpenAI models) |
| `sentence` | NLTK sentence tokenizer | Narrative text, Q&A pairs |
| `semantic` | Groups sentences by embedding similarity; Voyage-aware | Topic-coherent chunks; highest quality, slowest |

## Retrieval Methods

| Method | Algorithm | Strengths |
|---|---|---|
| `dense` | Cosine similarity on embeddings (Atlas Vector Search) | Captures semantic meaning and paraphrases |
| `sparse` | BM25 full-text search (Atlas Search) | Keyword precision; handles rare or domain-specific terms |
| `hybrid` | Weighted combination — 70% dense + 30% sparse | Balanced recall and precision; default recommendation |

## Reranking

After initial retrieval returns the top-K candidates, a cross-encoder reranker re-scores each chunk against the query and reorders the final result list. Two options:

| Option | Model | Requires |
|---|---|---|
| Local | `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers, ~23 MB) | No API key; runs on CPU |
| Voyage | `rerank-2.5-lite` or `rerank-2.5` | `VOYAGE_API_KEY` in `.env` |

Set `rerank_provider: local` or `rerank_provider: voyage` in your config. Reranking is always applied to the top-`top_k_initial` results; `top_k_final` controls how many survive.

---

## CLI Usage

```bash
# Submit experiment and watch progress (local models)
rag-params-finder run --config configs/example-local.yaml

# Submit and detach (check dashboard for status)
rag-params-finder run --config configs/example-local.yaml --detach

# Manual recovery of interrupted runs
rag-params-finder recover --experiment-id <id> --auto
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Health check |
| POST | `/experiments` | Submit experiment sweep |
| GET | `/experiments` | List all experiments |
| GET | `/experiments/{id}` | Get experiment details |
| GET | `/experiments/{id}/results` | Get query results |
| GET | `/runs/{id}/status` | Get run status (for polling) |
| POST | `/recover` | Manual recovery |

---

## Dashboard

Open `http://localhost:5173` in your browser (requires the frontend dev server from step 4).

**Experiments list** — table of all submitted experiments with status badges and run counts. Click any row to drill in.

**Experiment detail** — shows every run in the sweep with phase indicator dots that update live (polls the server every 2 seconds). Once runs reach COMPLETE, expand per-query results to compare dense scores vs rerank scores.

---

## Development

### Quality Gates

```bash
# Lint
ruff check .

# Type check
mypy server/ cli/

# Tests
pytest

# Coverage
pytest --cov=server --cov=cli --cov-report=html
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
│   ├── main.py          # Typer entry
│   └── api_client.py
├── frontend/            # React dashboard
│   └── src/
├── configs/             # Example YAML and queries
├── input_data/          # User-supplied documents (gitignored)
│   └── pdfs/            # Place PDF files here
└── docs/                # Architecture, slices, ADRs
```

---

## Troubleshooting

### Vector index not found

**Symptom**: server logs show `Search index 'vector_index' not found` or queries return no results.

**Fix**: The Atlas vector index must be created manually after the cluster is provisioned.
1. Atlas UI → your cluster → **Browse Collections** → `chunks` collection → **Search Indexes** tab
2. **Create Search Index** → JSON Editor → paste the index definition from [Configure Environment](#2-configure-environment) in `CLAUDE.local.md`
3. Index name must be exactly `vector_index_1024` (Voyage, 1024-dim) or `vector_index_384` (local, 384-dim)
4. Wait ~1–2 minutes for the index to build before running queries

### Dimension mismatch (local vs Voyage models)

**Symptom**: vector search fails with a dimension error, or results are nonsensical.

**Cause**: local models produce 384-dim embeddings; Voyage models produce 1024-dim. Vectors from different models cannot be compared.

**Fix**:
- Each embedding model requires its own Atlas vector index: `vector_index_384` (local) and `vector_index_1024` (Voyage)
- Never mix providers within the same experiment config
- The system validates provider/model consistency at config load time — fix any validation errors before submitting

### Voyage API rate limit hit

**Symptom**: `voyageai.error.RateLimitError: Rate limit exceeded` in server logs; run status shows `failed`.

**Fix**:
- Check usage at [dash.voyageai.com/usage](https://dash.voyageai.com/usage)
- Free tier: 300 RPM / 1 M TPM. Reduce experiment parallelism or switch to `provider: local` for testing
- Set `VOYAGE_RPM_LIMIT` and `VOYAGE_TPM_LIMIT` in `.env` to match your tier; the server uses these to throttle requests

### Dashboard stuck on "Loading…"

**Symptom**: browser shows a loading spinner indefinitely or a "Failed to fetch" error.

**Possible causes and fixes**:

| Cause | Fix |
|---|---|
| Server not running | Start with `uvicorn server.main:app --reload --port 8001`; verify at `http://localhost:8001/healthz` |
| Wrong server port | Check `SERVER_URL` in `.env` matches the port uvicorn is using |
| CORS error | Hard-refresh the browser (`Cmd+Shift+R`); restart server with `--reload` |
| Frontend pointing at wrong API URL | Check `frontend/src/services/apiClient.ts` base URL matches server port |

### Chunks not appearing in Atlas

**Symptom**: experiment completes (status `complete`) but the `chunks` collection in Atlas is empty or the run count is zero.

**Possible causes**:
- MongoDB connection lost during the STORING phase — check server logs for `pymongo` errors
- Atlas free-tier storage quota exceeded (512 MB limit on M0) — check **Metrics → Storage** in the Atlas UI
- Vector index not yet built — chunks are stored but queries fail silently

**Debug steps**:
```bash
# Tail server logs for MongoDB errors
tail -f server.log | grep -i "mongo\|store\|chunk"
```
Then check Atlas UI → **Metrics → Operations** for write failures.

---

## License

MIT

---

## Credits

Inspired by [pre-rag-explorer-dashboard](https://github.com/neomatrix369/pre-rag-explorer-dashboard) — a browser-based RAG exploration tool.

**Differences**:
- Server-based (not browser-only)
- MongoDB Atlas (not IndexedDB)
- Voyage AI (not Transformers.js)
- Parameter sweeps (not single experiments)
- Real semantic chunking (not paragraph-split mock)
