# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**rag-params-finder** is a RAG parameter sweep experimentation tool with three components:
1. **Python CLI** — submits experiment configs
2. **FastAPI Server** — orchestrates PDF → chunk → embed → search pipeline
3. **React Dashboard** — visualizes experiments and results

**Key insight**: Two-process architecture separates config submission (CLI) from execution (Server). Dashboard is read-only observer.

## Development Commands

### Backend (Python 3.12+)

```bash
# Setup
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run server
uvicorn server.main:app --reload --port 8001

# Lint & type check
ruff check .
ruff format .
mypy server/ cli/

# Tests
pytest
pytest -v tests/test_orchestrator.py  # single test file
pytest -k "test_chunking"             # single test by name
```

### Frontend (Node.js 22+)

```bash
cd frontend

# Setup
npm install

# Run dev server
npm run dev              # → http://localhost:5173

# Lint & type check
npm run lint
npm run typecheck

# Build
npm run build
npm run preview          # preview production build
```

### CLI Usage

```bash
# Submit experiment (after server is running)
rag-params-finder run --config configs/example-local.yaml

# Detach from live polling
rag-params-finder run --config configs/example-local.yaml --detach

# List experiments (queries server)
rag-params-finder list

# Get experiment status
rag-params-finder status <experiment-id>
```

## Architecture Essentials

### Data Flow

```
CLI → POST /experiments → Server → MongoDB Atlas
                             ↓
          PDF → Chunk → Embed → Store (Atlas Vector) → Query → Results
                             ↓
         Dashboard ← GET /experiments ← Server
```

### Provider System

**Two independent provider settings**:

1. **`embedding.provider`**: "local" or "voyage"
   - Local: `all-MiniLM-L6-v2` (384-dim, sentence-transformers, ~23MB)
   - Voyage: `voyage-3.5-lite|voyage-3.5|voyage-context-3` (1024-dim, requires API key)

2. **`retrieval.rerank_provider`**: "local" or "voyage"
   - Local: `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers, ~23MB)
   - Voyage: `rerank-2.5-lite|rerank-2.5` (requires API key)

**Critical**: Provider and model must match. Registry in `server/core/model_registry.py` validates this.

### Chunking Methods

Five methods in `server/core/chunkers/`:
- **recursive**: LangChain RecursiveCharacterTextSplitter (default, splits on \n\n → \n → space)
- **fixed**: Simple fixed-size chunks with overlap
- **token**: tiktoken-based chunking (respects token boundaries)
- **sentence**: NLTK sentence-based (uses punkt tokenizer)
- **semantic**: Sentence-grouping with embedding similarity (Voyage-aware)

### Retrieval Methods

Three methods in `server/core/retriever.py`:
- **dense**: Pure vector search (cosine similarity on embeddings)
- **sparse**: BM25 text search (Atlas FTS)
- **hybrid**: Weighted combination (dense 70% + sparse 30%)

### Pipeline Phases

Each run progresses through phases (tracked in `run_status` collection):
1. QUEUED → 2. PARSING → 3. CHUNKING → 4. EMBEDDING → 5. STORING → 6. QUERYING → 7. RERANKING → 8. COMPLETE/FAILED

Dashboard `PhaseIndicator` component shows this visually with colored dots.

## MongoDB Atlas Collections

| Collection | Purpose | Key Index |
|---|---|---|
| `chunks` | Text chunks + embeddings | **Vector index** on `embedding` (1024-dim cosine) + filter on `experiment_id`, `embedding_model` |
| `experiments` | Experiment metadata | `created_at`, `status` |
| `run_status` | Per-run phase tracking | `experiment_id`, `phase` |
| `results` | Query results (top-K chunks) | `experiment_id`, `query_id` |

**Critical**: Always filter vector search by `embedding_model` — different models produce incompatible vectors.

## Frontend Architecture

### Component Structure

```
App.tsx
├── ExperimentsScreen.tsx         # List view (polling every 2s)
├── ExperimentDetailScreen.tsx    # Detail view (runs table, metrics, phase indicators)
└── SearchExplorerScreen.tsx      # Results analysis (ranked configs, detailed results)
```

### UI Design Principles

- **Terminology**: "Embedding Models" (not "Models") to distinguish from "Reranking Models"
- **Provider-conditional fields**: Voyage rate limits only shown when `provider === "voyage"`
- **Status visualization**: Color-coded badges (green=complete, blue=running, red=failed, amber=partial)
- **Progress indicators**: Circular rings for completion percentage
- **Metric cards**: Prominent stat cards with gradients (Total Runs, Successful, Failed, Duration)

See component header comments for detailed design rationale.

### Type Safety

TypeScript types in `frontend/src/types/index.ts` are **hand-mirrored** from Python models. When changing backend models, update frontend types manually.

Enums must match:
- `ChunkingMethod`: fixed|recursive|token|sentence|semantic
- `RetrievalMethod`: dense|sparse|hybrid
- `Phase`: queued|parsing|chunking|embedding|storing|querying|reranking|complete|failed|interrupted

## Configuration Files

### Experiment Config (YAML)

Located in `configs/`. Two examples:
- `example-local.yaml` — Local models (no API key needed)
- `example-voyage-ai.yaml` — Voyage AI models (requires API key)

**Structure**:
```yaml
experiment_name: string         # Timestamp suffix auto-added on submit
data_paths: [paths]             # Files or directories (.pdf, .txt, .md, .csv)
queries_file: path              # Local path or URL (auto-downloaded and cached)
embedding:
  provider: local|voyage
  models: [model-ids]
chunking:
  methods: [recursive|fixed|token|sentence|semantic]
  params:
    chunk_sizes: [ints]
    overlaps: [ints]
retrieval:
  methods: [dense|sparse|hybrid]
  top_k_initial: int
  top_k_final: int
  rerank_provider: local|voyage
  rerank_model: model-id
execution:
  parallelism: 1                # Currently only 1 supported
  on_error: continue|stop
```

### Queries File (JSON)

Persona-based queries structure:
```json
[
  {
    "persona_id": "student",
    "queries": [
      {"text": "What are Pell Grant eligibility requirements?", "focus": "financial_aid"}
    ]
  }
]
```

## Key Files Reference

### Backend Core

- `server/main.py` — FastAPI app entry + startup
- `server/core/orchestrator.py` — End-to-end pipeline executor (PDF → results)
- `server/core/model_registry.py` — Unified model registry (embedding + reranking)
- `server/core/embedder.py` — Provider dispatcher (local via sentence-transformers, Voyage via API)
- `server/core/reranker.py` — Reranking dispatcher
- `server/core/retriever.py` — Atlas Vector Search (dense/sparse/hybrid)
- `server/core/results_analyzer.py` — Aggregates query results, normalizes scores (0-100 via min-max)
- `server/models/config.py` — Pydantic experiment config with provider validation

### Frontend Core

- `frontend/src/App.tsx` — Root component (screen routing)
- `frontend/src/components/ExperimentDetailScreen.tsx` — Main detail view with visual enhancements
- `frontend/src/components/SearchExplorerScreen.tsx` — Results analysis view
- `frontend/src/services/apiClient.ts` — Fetch wrapper (all server API calls)

## Common Patterns

### Adding a New Embedding Model

1. Add to `server/core/model_registry.py` → `EMBEDDING_MODELS`
2. If new provider: update `server/models/config.py` → `Provider` type
3. Update `server/core/embedder.py` dispatcher logic (if needed)
4. Add example config in `configs/`

### Adding a New Chunking Method

1. Create `server/core/chunkers/my_method.py` with `chunk_text()` function
2. Add enum to `server/models/enums.py` → `ChunkingMethod`
3. Update `server/core/orchestrator.py` → `get_chunker()` dispatcher
4. Update `frontend/src/types/index.ts` → `ChunkingMethod` enum

### Adding a New API Endpoint

1. Create route in `server/api/` (or add to existing router)
2. Add handler to `server/main.py` → `app.include_router()`
3. Add client method to `cli/api_client.py` (if CLI needs it)
4. Add fetch function to `frontend/src/services/apiClient.ts` (if dashboard needs it)

## Testing Strategy

- **Unit tests**: Individual chunkers, embedders, rerankers
- **Integration tests**: Full pipeline with mock MongoDB
- **Frontend**: TypeScript compilation serves as basic test (no vitest/jest setup yet)

Run backend tests: `pytest` (from project root with venv activated)

## Common Gotchas

1. **Vector dimension mismatch**: Local models are 384-dim, Voyage models are 1024-dim. Cannot mix in same experiment.
2. **Model/provider mismatch**: Config validation will fail if `provider: local` but `models: [voyage-3.5]`
3. **Missing embeddings filter**: Always filter Atlas vector search by `embedding_model` to avoid incompatible vector comparisons
4. **Queries file URL caching**: URL queries are downloaded to `configs/` and cached. Delete cached file to re-download.
5. **Server must be running**: CLI requires server at `SERVER_URL` (default: http://localhost:8001)
6. **Rate limits**: Voyage API has rate limits (RPM/TPM). Local models have no limits but are slower.
7. **Score normalization**: Rerank scores can be negative (cross-encoder logits). System uses min-max normalization to map all scores to 0-100 range. Dense-only scores (cosine 0-1) also work correctly.

## Deployment Notes

- **Local only**: No hosted deployment. Each user runs their own server + dashboard.
- **Secrets**: `VOYAGE_API_KEY` and `MONGODB_URI` must be in server's environment (`.env` file or env vars)
- **MongoDB Atlas**: Free tier (M0) supports vector search. Index must be created manually in Atlas UI.
- **Docker**: No containerization yet. Run directly with uvicorn + vite.

## Further Reading

- `docs/ARCHITECTURE.md` — Detailed system architecture
- `README.md` — Setup guide and quickstart
- `docs/PROGRESS.md` — Development progress tracking
- Component header comments — UI design decisions and rationale
