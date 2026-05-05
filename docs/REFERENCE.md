# Reference Guide

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

Detailed reference for `rag-params-finder`. The [README](../README.md) covers the quick-start path; this file preserves all expanded explanations, annotated examples, and debug steps.

---

## How It Works

`rag-params-finder` is a two-process system (Python CLI + FastAPI server + React dashboard) for ML engineers to run parameter-sweep experiments on RAG pipelines and visualize results.

1. Engineer configures experiment sweeps in YAML (embedding models × chunking methods × chunk sizes × overlaps × retrieval methods)
2. CLI submits the experiment config to the FastAPI server via `POST /experiments`
3. Server expands the config into a Cartesian product of runs, then for each run orchestrates:
   - data loading (PDF/TXT/MD/CSV) → chunking → embedding (local or Voyage) → Atlas vector storage → query execution → reranking (local or Voyage)
4. React dashboard displays live experiment status and results; polls the server every 2 seconds

### Key Features (full list)

- **Multi-format data loading**: PDF, TXT, Markdown, CSV — files and/or directories (recursive scan)
- **5 chunking methods**: Fixed, Recursive, Token, Sentence, Semantic (Voyage-aware)
- **Voyage AI embedding models**: `voyage-3.5-lite`, `voyage-3.5`, `voyage-context-3`
- **Free/local embedding models**: `all-MiniLM-L6-v2` via sentence-transformers (no API key, no rate limits)
- **3 retrieval methods**: Dense (vector search), Sparse (BM25), Hybrid (weighted combination)
- **Voyage reranking**: `rerank-2.5-lite` for top-K refinement
- **Free/local reranking**: `cross-encoder/ms-marco-MiniLM-L-6-v2` via sentence-transformers
- **URL-capable queries file**: local path or URL (auto-downloaded and cached on first use)
- **Centralized settings**: pydantic-settings-based config from `.env` or environment variables
- **Auto-timestamped experiments**: each run gets a unique timestamp suffix appended to `experiment_name`
- **Live phase tracking**: QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE
- **Rich experiment dashboard**: metric cards, status badges, color-coded runs table, search explorer

---

## Prerequisites (Detailed)

### Python 3.12+
Install via [python.org](https://www.python.org/downloads/) or pyenv:
```bash
pyenv install 3.12.2
pyenv local 3.12.2
```

### Node.js 22+
Install via [nodejs.org](https://nodejs.org/) or nvm:
```bash
nvm install 22
nvm use 22
```

### MongoDB Atlas (free tier)
1. Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com/)
2. Under **Database Access**, create a user with read/write permissions
3. Under **Network Access**, add your IP (or `0.0.0.0/0` for dev)
4. Get the connection string: **Connect → Compass → copy the SRV URI**
5. Note: M0 (free tier) fully supports vector search

### Voyage AI API key *(optional — local models need no key)*
1. Sign up at [dash.voyageai.com](https://dash.voyageai.com)
2. Navigate to **API Keys** → create new key
3. Copy the `vo-...` key into your `.env`

**Rate limits (free tier)**: 300 RPM, 1 M TPM
**Costs (approximate)**: `voyage-3.5-lite` $0.06/1M tokens · `voyage-3.5` $0.12/1M tokens · `rerank-2.5-lite` $0.02/1K queries

---

## Step-by-Step Setup

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
```

Edit `.env` and set:
```bash
# Required
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/rag_params_finder?retryWrites=true&w=majority

# Optional — only needed for Voyage models
VOYAGE_API_KEY=vo-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional — defaults shown
SERVER_URL=http://localhost:8001
VOYAGE_RPM_LIMIT=300
VOYAGE_TPM_LIMIT=1000000
RECOVER_ON_BOOT=false
LOG_LEVEL=INFO
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
mkdir -p input_data/pdfs
cp /path/to/my-document.pdf input_data/pdfs/
```

Supported formats: `.pdf`, `.txt`, `.md`, `.csv`

Reference files and/or directories in your config YAML:
```yaml
data_paths:
  - ./input_data/pdfs/my-document.pdf   # individual file
  - ./input_data/papers/                # or a directory — scanned recursively for all supported formats
```

### 6. Run an Experiment

```bash
# Terminal 3: CLI

# Local models — no API key needed
rag-params-finder run --config configs/example-local.yaml

# Voyage AI models — requires VOYAGE_API_KEY in .env
rag-params-finder run --config configs/example-voyage-ai.yaml
```

The CLI will:
- Submit the experiment to the server (experiment name gets a timestamp suffix automatically)
- Display the experiment ID and the generated run IDs
- Poll run progress live (use `--detach` to skip polling and check the dashboard instead)

### 7. View Results in the Dashboard

Open `http://localhost:5173`:

1. The **Experiments list** shows your submitted experiment with a status badge (`complete` / `running` / `failed` / `partial`)
2. Click a row to open the **Experiment detail** screen — phase indicator dots update live showing each run's progress (PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE)
3. Once runs finish, open the **Search Explorer** to drill into per-query results and compare dense vs rerank scores across configs

---

## Configuration Reference

See `configs/example-local.yaml` (local, no key) and `configs/example-voyage-ai.yaml` (Voyage AI).

### Full annotated config

```yaml
experiment_name: my-sweep           # timestamp suffix added automatically on each run

data_paths:                          # list of files and/or directories
  - ./input_data/pdfs/sample.pdf     # individual file
  # - ./input_data/pdfs/             # directory — scanned recursively for .pdf/.txt/.md/.csv

queries_file: ./configs/questions.example.json  # local path or URL
                                                 # URL is downloaded to ./configs/ on first use and cached

embedding:
  provider: local                    # "local" (sentence-transformers) or "voyage"
  models:
    - all-MiniLM-L6-v2               # provider must match: "local" models can't be set with provider: voyage

chunking:
  methods:
    - recursive                      # one or more: recursive | fixed | token | sentence | semantic
    # - fixed
    # - token
  params:
    chunk_sizes: [256, 512, 1024]    # all sizes × all overlaps = cartesian product
    overlaps: [0, 50]

retrieval:
  methods:
    - dense                          # one or more: dense | sparse | hybrid
    # - hybrid
  top_k_initial: 20                  # candidates passed to reranker
  top_k_final: 5                     # results returned after reranking
  rerank_provider: local             # "local" or "voyage"
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2

execution:
  parallelism: 1                     # only 1 supported currently
  on_error: continue                 # "continue" (partial results) or "stop" (halt experiment)
```

### Queries file format (persona-based)

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

Each query is executed independently per run. Results are stored per `persona_id` + `focus` for filtering in the Search Explorer.

### All-local config (no API key)

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

**Atlas index requirement for local models**: local embeddings are 384-dim (vs 1024-dim for Voyage), so you need a separate index named `vector_index_384`:

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

Models are downloaded from HuggingFace on first use and cached in `~/.cache/huggingface/hub/`. Pre-download to avoid startup delay:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

---

## Dashboard Reference

### Experiments List Screen

- Table of all submitted experiments (newest first), polling every 2 seconds
- Each row shows: experiment name, status badge, total runs, successful/failed counts, created time
- Status badges: `complete` (green) · `running` (blue) · `failed` (red) · `partial` (yellow) · `cancelled` (gray)
- Click any row to drill into the Experiment Detail screen

### Experiment Detail Screen

- Polls `GET /experiments/{id}` every 2 seconds while status is non-terminal
- **Metric cards**: Total Runs · Successful · Failed · Avg Duration
- **Phase indicator dots**: one dot per phase per run, color-coded:
  - Green = past (complete) · Blue pulsing = current (active) · Gray = future · Red = failed
- **Runs table**: each row is one config combination (model + method + chunk_size + overlap + retrieval). Expand to see per-query results with dense scores and rerank scores
- Once all runs reach COMPLETE, the experiment status flips to `complete`

### Search Explorer Screen

- Loads once from `GET /experiments/{id}/explore` (no polling)
- **Best parameters card**: top-scoring config combination with overall relevance score
- **Ranked config cards**: all configs ranked by score, with score bars for visual comparison
- **Per-query results**: detailed ranked chunks for each query in each config

---

## Development Reference

### Quality Gates

```bash
# Backend
uv run ruff check .                    # lint — expect 0 errors
uv run mypy server/ cli/               # type check — expect 0 errors
uv run pytest --tb=short -q            # tests — 0 tests collected (suite not yet written)
uv run pytest --cov=server --cov=cli --cov-report=html  # coverage (when tests exist)

# Frontend
cd frontend
npm run typecheck                      # tsc --noEmit — expect 0 errors
npm run build                          # expect ~34 modules, ~238 kB JS
npm audit --audit-level=high           # expect 0 vulnerabilities
```

### Project Structure (expanded)

```
rag-params-finder/
├── server/
│   ├── main.py              # FastAPI app entry + startup boot recovery
│   ├── settings.py          # Centralized pydantic-settings config
│   ├── api/
│   │   ├── experiments.py   # POST /experiments, GET /experiments, GET /experiments/{id}
│   │   └── runs.py          # GET /runs/{id}/status, POST /recover
│   ├── core/
│   │   ├── orchestrator.py  # run_sweep() + run_single() pipeline
│   │   ├── pdf_parser.py    # pypdf text extraction
│   │   ├── query_loader.py  # persona JSON → Query dataclass list
│   │   ├── model_registry.py  # embedding + reranking model catalog
│   │   ├── embedder.py      # Voyage embedding client
│   │   ├── local_embedder.py  # sentence-transformers embedding (lazy-load)
│   │   ├── reranker.py      # Voyage reranking client
│   │   ├── local_reranker.py  # CrossEncoder reranking (lazy-load)
│   │   ├── retriever.py     # Atlas Vector Search (dense/sparse/hybrid)
│   │   ├── results_analyzer.py  # aggregates scores, min-max normalization
│   │   └── chunkers/
│   │       ├── recursive.py # LangChain RecursiveCharacterTextSplitter
│   │       ├── fixed.py     # fixed-size character windows
│   │       ├── token.py     # tiktoken-based
│   │       ├── sentence.py  # NLTK sentence tokenizer
│   │       └── semantic.py  # embedding-similarity sentence grouping
│   ├── models/
│   │   ├── enums.py         # ChunkingMethod, RetrievalMethod, Phase
│   │   ├── config.py        # Pydantic experiment config + provider validators
│   │   ├── status.py        # RunStatus model
│   │   └── results.py       # QueryResult, SearchResult, Chunk
│   └── db/
│       ├── atlas.py         # MongoDB connection singleton
│       └── indexes.py       # collection + index creation helpers
├── cli/
│   ├── main.py              # Typer app (run, list, status, recover commands)
│   ├── config_loader.py     # YAML parser + model registry validation
│   └── api_client.py        # HTTP client to server
├── frontend/src/
│   ├── App.tsx              # root component (screen routing)
│   ├── components/
│   │   ├── ExperimentsScreen.tsx       # list view (polling every 2s)
│   │   ├── ExperimentDetailScreen.tsx  # detail view (runs table, phase dots, metrics)
│   │   └── SearchExplorerScreen.tsx    # results analysis (ranked configs, per-query)
│   ├── services/apiClient.ts  # fetch wrapper (all server API calls)
│   └── types/index.ts         # hand-mirrored TypeScript types from Python models
├── configs/
│   ├── example-local.yaml       # all-local experiment (no API key)
│   ├── example-voyage-ai.yaml   # Voyage AI experiment
│   └── questions.example.json   # sample persona queries file
├── input_data/                  # user-supplied documents (gitignored)
└── docs/
    ├── ARCHITECTURE.md
    ├── REFERENCE.md             # this file
    ├── PROGRESS.md
    ├── DOC-GAPS.md
    ├── adr/
    └── slices/
```

---

## Troubleshooting (Expanded)

### Vector index not found

**Symptom**: server logs show `Search index 'vector_index' not found` or queries return no results.

**Fix**: The Atlas vector index must be created manually after provisioning your cluster.

1. Atlas UI → your cluster → **Browse Collections** → `chunks` collection → **Search Indexes** tab
2. **Create Search Index** → JSON Editor
3. Paste the index definition for your model type:

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

Both indexes can coexist on the same `chunks` collection — the server selects the correct one via `get_index_name(model)` in `server/core/retriever.py`.

Wait ~1–2 minutes for the index to build before running queries.

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

| Cause | Fix |
|-------|-----|
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

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | Yes | — | MongoDB Atlas connection string |
| `VOYAGE_API_KEY` | No | — | Voyage AI API key (only if using Voyage models) |
| `SERVER_URL` | No | `http://localhost:8001` | FastAPI server URL (used by CLI) |
| `VOYAGE_RPM_LIMIT` | No | `300` | Voyage requests-per-minute limit (throttle guard) |
| `VOYAGE_TPM_LIMIT` | No | `1000000` | Voyage tokens-per-minute limit |
| `RECOVER_ON_BOOT` | No | `false` | Auto-retry interrupted runs when server starts |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG` for verbose output) |

---

## MongoDB Atlas Collections

| Collection | Purpose | Key Indexes |
|------------|---------|-------------|
| `chunks` | Text chunks + embeddings | Vector index on `embedding` (1024-dim or 384-dim cosine) + filter fields |
| `experiments` | Experiment metadata + sweep config | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `results` | Per-query top-K results | `experiment_id`, `query_id` |

**Manual cleanup** (Atlas UI shell or `mongosh`):
```javascript
const exp_id = "your-experiment-id"
db.experiments.deleteOne({experiment_id: exp_id})
db.run_status.deleteMany({experiment_id: exp_id})
db.chunks.deleteMany({experiment_id: exp_id})
db.results.deleteMany({experiment_id: exp_id})
```

Note: there is no cascade delete — all four collections must be cleaned manually.
