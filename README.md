# rag-params-finder

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2.6+-E92063?logo=pydantic&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)

[![CI](https://img.shields.io/github/actions/workflow/status/neomatrix369/rag-params-finder/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white)](https://github.com/neomatrix369/rag-params-finder/actions)
[![License: MIT](https://img.shields.io/github/license/neomatrix369/rag-params-finder)](https://github.com/neomatrix369/rag-params-finder/blob/main/LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/neomatrix369/rag-params-finder)](https://github.com/neomatrix369/rag-params-finder/commits/main)
[![Stars](https://img.shields.io/github/stars/neomatrix369/rag-params-finder?style=social)](https://github.com/neomatrix369/rag-params-finder)

> Find your optimal RAG configuration — **before** you build your RAG application.

**RAG parameter sweep experimentation tool** — systematically evaluate embedding models, chunking strategies, and retrieval methods using MongoDB Atlas Vector Search. Supports Voyage AI, Kimchi-hosted embedding models, and local sentence-transformers (no API key needed).

Most RAG projects start with a guess: pick an embedding model, pick a chunking method, a retrieval method (or a re-ranker), realise it's wrong, refactor. That loop is
slow and expensive.

`rag-params-finder` inverts it.

Give it your data and your questions. It runs every combination — embedding
model × chunking method × retrieval method — stores the retrieval scores and
shows you exactly which configuration performs best.
**Before you write a single line of your RAG application.**

## Why this matters

| What you avoid | What you get instead |
|---|---|
| No LLM calls | Embedding only — 10–100× cheaper |
| No eval framework setup | One YAML config, one CLI command |
| No deployed RAG app needed | Just your data, your questions, your credentials |
| No guessing | Actual retrieval scores across every config, side by side |
| No throwaway experiments | Results persist — compare runs across sessions |

## What it sweeps

- **Embedding models**: local, Voyage AI (12 models — see `server/core/model_registry.py`), and Kimchi-hosted model sweeps
- **Chunking methods**: Fixed · Recursive · Token · Sentence · Semantic
- **Retrieval methods**: Dense · Sparse · Hybrid
- **Questions**: Persona-organised — user provided or generated as part of golden master generation process

One YAML. N experiments. Evidence-based decision. Ship the right config first.

---

## 📸 Screenshots

| Screen | Description |
|:---:|:---|
| ![Experiments list](docs/images/01-experiments-list.png) | **Experiments list** — all submitted sweeps with status badges and run counts |
| ![Experiment detail](docs/images/02-experiment-detail.png) | **Experiment detail** — metric cards, live phase indicator dots, runs table |
| ![Search Explorer](docs/images/03-search-explorer.png) | **Search Explorer** — best-parameters card, ranked configs with score bars |

---

## 🚀 Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+, [MongoDB Atlas account](docs/user-guide/cloud-setup.md#mongodb-atlas-required-for-all-sweeps) (free tier). [Voyage AI](docs/user-guide/cloud-setup.md#voyage-ai-required-for-voyage-sweep) or Kimchi credentials optional for local-only sweeps.

```bash
# Clone and install
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

# Configure — see docs/user-guide/cloud-setup.md for minimal Atlas + Voyage checklist
cp .env.example .env
# Edit .env: add MONGODB_URI (required);
# add VOYAGE_API_KEY or KIMCHI_BASE_URL/KIMCHI_API_KEY for hosted models

# Start
uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2 (optional)

# Sweeps — complete cloud-setup.md checklist first
rag-params-finder run --config configs/example-mongodb-local.yaml   # 90 runs, no API key
rag-params-finder run --config configs/example-mongodb-voyage.yaml  # 90 runs, Voyage + Tier 1
rag-params-finder run --config configs/example-kimchi.yaml          # 24 runs, Kimchi-hosted embeddings
```

Open `http://localhost:5173` to watch live progress and explore results.

---

## 🗺️ Choose Your Path

| I want to… | Start here |
|---|---|
| Set up MongoDB Atlas or Voyage AI accounts | [Cloud Account Setup](docs/user-guide/cloud-setup.md) |
| Run my first experiment | [Getting Started](docs/user-guide/getting-started.md) |
| Understand all config options | [Configuration Reference](docs/user-guide/configuration.md) |
| Learn all CLI commands | [CLI Reference](docs/user-guide/cli-reference.md) |
| Understand the dashboard | [Dashboard Guide](docs/user-guide/dashboard-guide.md) |
| Fix an error | [Troubleshooting](docs/user-guide/troubleshooting.md) |
| Understand the system design | [Architecture](docs/contributor-guide/architecture.md) |
| Add a new model, chunker, or endpoint | [Extending the System](docs/contributor-guide/extending.md) |
| Set up a development environment | [Development Guide](docs/contributor-guide/development.md) |
| Why these design choices? | [ADR-001](docs/adr/ADR-001-two-process-architecture.md) · [ADR-002](docs/adr/ADR-002-voyage-and-local-providers.md) · [ADR-003](docs/adr/ADR-003-mongodb-atlas-vector-store.md) |

---

## ⚡ Key Features

- **5 chunking methods**: Fixed, Recursive, Token, Sentence, Semantic
- **3 retrieval methods**: Dense (vector search), Sparse (BM25), Hybrid (Reciprocal Rank Fusion)
- **Voyage AI models**: all registered embeddings in `model_registry.py` (voyage-4/3/domain/context) + rerankers `rerank-2.5-lite`, `rerank-2.5`, and legacy rerank APIs
- **Kimchi embeddings**: OpenAI-compatible hosted embedding catalog via `configs/example-kimchi.yaml`
- **Local models** (no API key): `all-MiniLM-L6-v2` + `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Multi-format data loading**: PDF, TXT, Markdown, CSV — files or directories
- **Cartesian sweep**: one YAML config → N models × M methods × P sizes × Q overlaps runs
- **Live phase tracking**: QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE
- **Experiment management**: Pause/resume long sweeps, cancel running experiments, delete with cascade cleanup, boot orphan reconciliation
- **Search index preflight**: Validates required Atlas Search indexes and cluster quota before sweeps start; rejects with HTTP 422 when indexes are missing or quota exhausted
- **Atlas index CLI**: `indexes list` and `indexes reset` for M0 quota troubleshooting
- **Vector DB stats**: Cluster and per-experiment chunk/storage estimates; optional Atlas quota bar with tier, provider, and region when Admin API credentials are configured
- **Progress feedback**: Byte-level network loading, circular progress with elapsed time and ETA, background polling with "Syncing..." badges
- **Scoped logging**: Server and dashboard use `[rag-params-finder] [Scope] operation — details` format; set `LOG_LEVEL=DEBUG` for verbose server output
- **Pagination**: All list views paginated (10 items per page for experiments/runs, 5 for configs); collapsible experiment rows

---

## 🧱 Built With

**Backend**: FastAPI · Python 3.12 · Pydantic · PyMongo · LangChain text splitters · pypdf · Typer · Rich · sentence-transformers · NLTK · tiktoken

**Frontend**: React 19 · TypeScript 5.8 · Vite 6 · Tailwind CSS

**AI/ML**: Voyage AI · Kimchi embeddings · sentence-transformers · MongoDB Atlas Vector Search

**Dev tools**: uv · ruff · mypy · pytest · GitHub Actions

---

## 🤝 Contributing

Contributions welcome — please open an issue first to discuss the change.

Priority areas: test suite with mock MongoDB fixtures, Search Explorer dashboard enhancements, SSE live updates, Docker Compose.

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙏 Credits

Inspired by [pre-rag-explorer-dashboard](https://github.com/neomatrix369/pre-rag-explorer-dashboard).
