# Architecture

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![React](https://img.shields.io/badge/React_19-61DAFB?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite_6-646CFF?logo=vite&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-embeddings_%26_reranking-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

## System Overview

`rag-params-finder` is a **two-process system** for RAG parameter sweep experimentation:

1. **Python CLI** (thin client) — submits experiment configs to server
2. **FastAPI Server** (engine) — orchestrates PDF → chunk → embed → search pipeline
3. **React Dashboard** (observer) — read-only visualization of experiments and results

## Data Flow

```
CLI (submit YAML) → FastAPI Server → MongoDB Atlas
                                         ↓
                        PDF → Chunk → Embed → Store → Query → Results
                                         ↓
React Dashboard ← (polling) ← FastAPI Server
```

## Technology Stack

### Backend (Server + CLI)
- **FastAPI** — REST API server
- **Python 3.12** — Language runtime
- **Voyage AI** — Embeddings (voyage-3.5-lite/3.5/context-3) + Reranking (rerank-2.5-lite/2.5)
- **sentence-transformers** — Local embeddings (`all-MiniLM-L6-v2`, 384-dim) + Local reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- **MongoDB Atlas** — Vector storage + search
- **LangChain** — Text splitters (recursive, fixed, token, sentence)
- **Typer** — CLI framework
- **Rich** — CLI output formatting

### Frontend (Dashboard)
- **React 19** — UI framework
- **TypeScript 5.8** — Type safety
- **Vite 6** — Build tool
- **Tailwind CSS** — Styling (installed locally, not CDN)

## Core Modules

### Server (`server/`)

#### API Layer (`api/`)
- `experiments.py` — POST /experiments, GET /experiments

#### Core Services (`core/`)
- `orchestrator.py` — End-to-end pipeline executor
- `pdf_parser.py` — pypdf wrapper
- `model_registry.py` — Unified registry for embedding + reranking models (provider, dimensions, HuggingFace ID)
- `chunkers/` — 5 chunking methods
  - `recursive.py` — LangChain RecursiveCharacterTextSplitter
  - `fixed.py` — Fixed-size character windows
  - `token.py` — Token-based (tiktoken)
  - `sentence.py` — NLTK sentence-based
  - `semantic.py` — Sentence grouping by embedding similarity (Voyage-aware)
- `embedder.py` — Voyage embedding client
- `local_embedder.py` — sentence-transformers embedding client (lazy-load, cached)
- `reranker.py` — Voyage reranking client
- `local_reranker.py` — sentence-transformers CrossEncoder reranker (lazy-load, cached)
- `retriever.py` — Atlas Vector Search (dense/sparse/hybrid); dynamic index selection by model dimension

#### Models (`models/`)
- `enums.py` — ChunkingMethod, RetrievalMethod, Phase
- `config.py` — Pydantic experiment config
- `status.py` — RunStatus model
- `results.py` — QueryResult, SearchResult, Chunk

#### Database (`db/`)
- `atlas.py` — MongoDB connection singleton
- `indexes.py` — Collection + index creation

### CLI (`cli/`)
- `main.py` — Typer app entry point
- `config_loader.py` — YAML parser
- `api_client.py` — HTTP client to server

### Frontend (`frontend/src/`)
- `App.tsx` — Root component
- `components/ExperimentsScreen.tsx` — Polling table view
- `services/apiClient.ts` — Fetch wrapper
- `types/index.ts` — Hand-mirrored TypeScript types

## MongoDB Atlas Collections

| Collection | Purpose | Key Indexes |
|---|---|---|
| `chunks` | Text chunks + Voyage embeddings | **Vector index** on `embedding` (1024-dim, cosine); standard on `experiment_id` |
| `experiments` | Experiment metadata + config | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `collections` | Source PDF metadata | `hash` (dedup) |
| `queries` | Test queries executed | `experiment_id` |
| `results` | Per-query top-K results | `experiment_id`, `query_id` |

## Vector Search Configuration

**Atlas Vector Index** (must be created manually in Atlas UI):

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "experiment_id"
    },
    {
      "type": "filter",
      "path": "embedding_model"
    }
  ]
}
```

**Critical**: Always filter by `embedding_model` on queries — different Voyage models produce incompatible vectors.

## Pipeline Phases

Each run progresses through phases tracked in `run_status`:

1. **QUEUED** — Run created, waiting to start
2. **PARSING** — PDF → plain text
3. **CHUNKING** — Text → chunks
4. **EMBEDDING** — Chunks → Voyage embeddings
5. **STORING** — Write chunks + embeddings to Atlas
6. **QUERYING** — Execute test queries
7. **RERANKING** — Voyage rerank top-20 → top-K (if enabled)
8. **COMPLETE** / **FAILED** / **INTERRUPTED**

## Environment Variables

**Server only** (secrets must NOT be in CLI):
- `VOYAGE_API_KEY` — Voyage AI API key
- `MONGODB_URI` — MongoDB Atlas connection string

**CLI**:
- `SERVER_URL` — FastAPI server URL (default: http://localhost:8001)

**Optional**:
- `RECOVER_ON_BOOT` — Auto-retry interrupted runs on boot (default: false)

## Deployment Model

**Runs locally** — no hosted deployment:

1. Clone repo and install (`uv pip install -e .` + `npm install` in `frontend/`)
2. Create `.env` with `MONGODB_URI` (required) and `VOYAGE_API_KEY` (optional — local models need no key)
3. Start server: `uvicorn server.main:app --reload --port 8001`
4. Start dashboard: `cd frontend && npm run dev`
5. Submit experiment: `rag-params-finder run --config configs/example-local.yaml`

## Design Decisions

See `docs/adr/` for Architecture Decision Records:
- [ADR-001](adr/ADR-001-two-process-architecture.md): Two-process architecture (CLI + Server)
- [ADR-002](adr/ADR-002-voyage-and-local-providers.md): Dual embedding/reranking providers (Voyage AI + local sentence-transformers)
- [ADR-003](adr/ADR-003-mongodb-atlas-vector-store.md): MongoDB Atlas as the vector store

## Future Enhancements

- SSE for live updates (replace polling)
- Celery for background tasks (replace FastAPI BackgroundTasks)
- Parallelism > 1 for sweep execution
- Dashboard-triggered runs (currently CLI-only)
