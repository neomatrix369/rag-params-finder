# rag-params-finder

**RAG parameter sweep experimentation tool** — systematically evaluate embedding models, chunking strategies, and retrieval methods using MongoDB Atlas Vector Search and Voyage AI.

## Overview

`rag-params-finder` is a two-process system (Python CLI + FastAPI server + React dashboard) for ML engineers to run parameter-sweep experiments on RAG pipelines and visualize results.

### What it does

1. Engineer configures experiment sweeps in YAML (embedding models × chunking methods × retrieval methods)
2. CLI submits experiment to FastAPI server
3. Server orchestrates: PDF parsing → chunking → Voyage embedding → Atlas vector storage → query execution → reranking
4. React dashboard displays live experiment status and results

### Key Features

- **5 chunking methods**: Fixed, Recursive, Token, Sentence, Semantic (Voyage-aware)
- **3 Voyage embedding models**: voyage-3.5-lite, voyage-3.5, voyage-context-3
- **3 retrieval methods**: Dense (vector search), Sparse (BM25), Hybrid (weighted combination)
- **Voyage reranking**: rerank-2.5-lite for top-K refinement
- **Live progress tracking**: Phase-based status updates
- **MongoDB Atlas Vector Search**: Production-grade vector storage and retrieval

---

## Quickstart

### Prerequisites

1. **Python 3.12+** — Install via [python.org](https://www.python.org/downloads/) or pyenv
2. **Node.js 22+** — Install via [nodejs.org](https://nodejs.org/) or nvm
3. **MongoDB Atlas account** (free tier sufficient)
   - Create cluster at [cloud.mongodb.com](https://cloud.mongodb.com/)
   - Note: M0 (free tier) supports vector search
4. **Voyage AI API key**
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
#   SERVER_URL=http://localhost:8000
```

### 3. Start the Server

```bash
# Terminal 1: FastAPI server
uvicorn server.main:app --reload
```

Server starts at `http://localhost:8000`. Visit `/docs` for OpenAPI documentation.

### 4. Start the Dashboard (Optional)

```bash
# Terminal 2: React dashboard
cd frontend
npm run dev
```

Dashboard runs at `http://localhost:5173`.

### 5. Run an Experiment

```bash
# Terminal 3: CLI
rag-params-finder run --config configs/example.yaml
```

The CLI will:
- Submit experiment to server
- Display experiment ID and run IDs
- Exit (use `--watch` flag to monitor progress)

Check dashboard or query server endpoints to view results.

---

## Architecture

```
┌──────────────┐    HTTP POST       ┌────────────────────────────────┐
│  Python CLI  │ ──/experiments──▶ │  FastAPI Server (engine)        │
│  (thin)      │                    │  • Sweep expansion             │
│              │ ◀──polling reads── │  • PDF parsing (pypdf)         │
│  --watch:    │                    │  • Chunking (LangChain+custom) │
│   polls      │                    │  • Embedding (Voyage)          │
│   /runs/*/   │                    │  • Atlas Vector Search         │
│   status     │                    │  • Voyage rerank               │
└──────────────┘                    │  • Run status tracking         │
                                     └────────────┬───────────────────┘
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

See `configs/example.yaml` for a complete example.

**Minimal config**:

```yaml
experiment_name: my-first-experiment
pdf_path: ./papers/attention.pdf
queries_file: ./configs/questions.example.json

embedding:
  models:
    - voyage-3.5-lite

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
  rerank_model: rerank-2.5-lite
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

---

## CLI Usage

```bash
# Submit experiment and watch progress
rag-params-finder run --config configs/example.yaml

# Submit and detach (check dashboard for status)
rag-params-finder run --config configs/example.yaml --detach

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

Visit `http://localhost:5173` to:

- View experiment history
- Monitor live runs (phase indicators)
- Drill down into per-query results
- Compare dense vs rerank scores

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
├── server/          # FastAPI engine
│   ├── main.py      # App entry + boot recovery
│   ├── api/         # Route handlers
│   ├── core/        # Orchestration, chunking, embedding
│   ├── models/      # Pydantic schemas
│   └── db/          # Atlas connection
├── cli/             # Python CLI client
│   ├── main.py      # Typer entry
│   └── api_client.py
├── frontend/        # React dashboard
│   └── src/
├── configs/         # Example YAML and queries
└── docs/            # Architecture, slices, ADRs
```

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
