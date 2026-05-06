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

**RAG parameter sweep experimentation tool** — systematically evaluate embedding models, chunking strategies, and retrieval methods using MongoDB Atlas Vector Search. Supports Voyage AI (hosted) and local sentence-transformers (no API key needed).

---

## 📸 Screenshots

| Screen | Description |
|:---:|:---|
| ![Experiments list](docs/images/01-experiments-list.png) | **Experiments list** — all submitted sweeps with status badges and run counts |
| ![Experiment detail](docs/images/02-experiment-detail.png) | **Experiment detail** — metric cards, live phase indicator dots, runs table |
| ![Search Explorer](docs/images/03-search-explorer.png) | **Search Explorer** — best-parameters card, ranked configs with score bars |

---

## 🚀 Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+, MongoDB Atlas account (free tier)

```bash
# Clone and install
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

# Configure
cp .env.example .env
# Edit .env: add MONGODB_URI (required) and VOYAGE_API_KEY (optional)

# Start
uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2

# Run an experiment (no API key needed)
rag-params-finder run --config configs/example-local.yaml
```

Open `http://localhost:5173` to watch live progress and explore results.

---

## 🗺️ Choose Your Path

| I want to… | Start here |
|---|---|
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
- **3 retrieval methods**: Dense (vector search), Sparse (BM25), Hybrid (70/30 weighted)
- **Voyage AI models**: `voyage-3.5-lite`, `voyage-3.5`, `voyage-context-3` + `rerank-2.5-lite`
- **Local models** (no API key): `all-MiniLM-L6-v2` + `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Multi-format data loading**: PDF, TXT, Markdown, CSV — files or directories
- **Cartesian sweep**: one YAML config → N models × M methods × P sizes × Q overlaps runs
- **Live phase tracking**: QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → RERANKING → COMPLETE

---

## 🧱 Built With

**Backend**: FastAPI · Python 3.12 · Pydantic · PyMongo · LangChain text splitters · pypdf · Typer · Rich · sentence-transformers · NLTK · tiktoken

**Frontend**: React 19 · TypeScript 5.8 · Vite 6 · Tailwind CSS

**AI/ML**: Voyage AI · sentence-transformers · MongoDB Atlas Vector Search

**Dev tools**: uv · ruff · mypy · pytest · GitHub Actions

---

## 🤝 Contributing

Contributions welcome — please open an issue first to discuss the change.

Priority areas: additional chunkers (sentence, token, semantic are stubbed), sparse/hybrid retrieval wiring, test suite with mock MongoDB fixtures, SSE live updates, Docker Compose.

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙏 Credits

Inspired by [pre-rag-explorer-dashboard](https://github.com/neomatrix369/pre-rag-explorer-dashboard).
