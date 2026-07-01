# Getting Started

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)
![SIE](https://img.shields.io/badge/SIE-Superlinked_Inference_Engine-blue)

Everything you need to run your first RAG parameter sweep experiment.

> **Shortest path:** [QUICKSTART.md](../../QUICKSTART.md) — install and first sweep. This guide adds step-by-step detail.

**Documentation map:** [docs/README.md](../README.md)

---

## ✅ Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | Install via [python.org](https://www.python.org/downloads/) or `pyenv install 3.12.2` |
| Node.js | 22+ | Install via [nodejs.org](https://nodejs.org/) or `nvm install 22` |
| MongoDB | Cloud M0 or local Docker | **Required** — see [MongoDB Setup](mongodb-setup.md#choose-your-mongodb-backend) |
| Voyage AI | Optional | Only for Voyage models — see [MongoDB Setup → Voyage AI](mongodb-setup.md#voyage-ai-required-for-voyage-sweep) |
| Docker Desktop + HF_TOKEN | Optional | **Self-hosted SIE only** — remote gateway needs no Docker; see [SIE Provider Setup](sie-setup.md) |

**New to Atlas or Voyage?** Start with **[MongoDB Setup](mongodb-setup.md)** — account creation, connection string, search indexes, API key, and Tier 1 billing (~15 min).

**Using SIE (open-source BGE-M3 embeddings)?** See **[SIE Provider Setup](sie-setup.md)** — set `SIE_ENABLED=true` (on/off), then `SIE_ENDPOINT` (+ `SIE_API_KEY` if needed) for a remote gateway, or optional local Docker.

---

## 📦 Install

```bash
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder

# Python environment
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e .

# Frontend
cd frontend && npm install && cd ..
```

---

## ⚙️ Configure

### 1. Set environment variables

```bash
cp .env.example .env
```

Edit `.env` — minimum for sweeps:

```bash
# Required (both sweeps)
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/rag_params_finder?retryWrites=true&w=majority

# Required for Voyage sweep only — see mongodb-setup.md checklist
VOYAGE_API_KEY=vo-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Uncomment Tier 1 limits in .env.example (comment out free-tier defaults first)
VOYAGE_RPM_LIMIT=2000
VOYAGE_TPM_LIMIT=16000000

SERVER_URL=http://localhost:8001
```

Full variable reference: [Troubleshooting → Environment Variables](troubleshooting.md#-environment-variables-reference). Optional Atlas Admin API keys enable cluster tier + storage quota in the dashboard — see `.env.example`.

### 2. Search indexes (required before sweep)

Both example configs use dense + sparse + hybrid — create **`vector_index_384`** (local) or **`vector_index_1024`** (Voyage or SIE) **and** **`text_search_index`** on the `chunks` collection.

**M0 free tier:** do this manually in Atlas UI before running a sweep — see [MongoDB Setup → step 6](mongodb-setup.md#6-create-search-indexes-m0--required-before-sweep). M0 allows **3 search indexes cluster-wide**; unknown indexes from other projects consume quota.

**M10+ paid tier:** server creates indexes on startup — check uvicorn logs.

**Verify and fix quota issues** (any tier):

```bash
rag-params-finder indexes list              # known vs unknown; count vs M0 limit
rag-params-finder indexes reset             # drop unknown indexes + ensure required
rag-params-finder indexes reset --all       # drop all chunks indexes + recreate
```

The server **preflights search indexes** when you submit a sweep: it derives required index names from your YAML (embedding dimensions + sparse/hybrid retrieval), checks cluster capacity, and rejects the experiment with **HTTP 422** if indexes are missing or quota is exhausted — before any embedding work starts.

---

## 📄 Add Your Documents

Place source documents in `input_data/` (gitignored):

```bash
mkdir -p input_data/pdfs
cp /path/to/my-document.pdf input_data/pdfs/
```

Supported formats: `.pdf`, `.txt`, `.md`, `.csv`

Reference files or directories in your config YAML:
```yaml
data_paths:
  - ./input_data/pdfs/my-document.pdf   # individual file
  - ./input_data/papers/                # directory — scanned recursively
```

---

## 🚀 Start the Server and Dashboard

### Option A — Manual (two terminals)

```bash
# Terminal 1: FastAPI server
uvicorn server.main:app --reload --port 8001

# Terminal 2: React dashboard (optional)
cd frontend && npm run dev
```

### Option B — Docker (one command)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) and `uv pip install -e .` on the host for the CLI.

```bash
./start-services.sh
```

- Server: `http://localhost:8001` (OpenAPI docs at `/docs`)
- Dashboard: `http://localhost:5374`
- Dev hot reload: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`

See [Troubleshooting → Docker](troubleshooting.md#-docker) if startup fails.

---

## ▶️ Run Your First Experiment

Complete the checklist for your sweep path in **[MongoDB Setup → Before you run a sweep](mongodb-setup.md#before-you-run-a-sweep)** first.

```bash
# Local sweep — checklist items 1–5 (no Voyage)
rag-params-finder run --config configs/example-mongodb-local.yaml

# Voyage sweep — checklist items 1–9
rag-params-finder run --config configs/example-mongodb-voyage.yaml

# SIE sweep — SIE_ENABLED=true + SIE_ENDPOINT (+ SIE_API_KEY if remote); see sie-setup.md
rag-params-finder run --config configs/example-mongodb-sie.yaml

# Submit and detach (check dashboard for status instead)
rag-params-finder run --config configs/example-mongodb-local.yaml --detach
```

The CLI will:
- Submit the config to the server (experiment name gets a timestamp suffix automatically)
- Display the experiment ID and generated run IDs
- Poll run progress live unless `--detach` is used

Open `http://localhost:5374` to watch live progress and explore results.

**Long sweeps**: pause and resume without losing completed runs:

```bash
rag-params-finder pause <experiment-id>    # stop after current phase
rag-params-finder resume <experiment-id>   # continue remaining combos
```

Or use the Pause / Resume buttons on the experiment detail screen in the dashboard.

---

## 🤖 Pre-downloading Local Models (Optional)

When using `provider: local`, sentence-transformers downloads models from HuggingFace on first use (~23 MB each). To avoid startup delay on your first run:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

Models are cached in `~/.cache/huggingface/hub/` after the first download.

---

## 👉 Next Steps

- [MongoDB Setup](mongodb-setup.md) — Atlas cloud or local Docker, Voyage billing, search indexes
- [SIE Provider Setup](sie-setup.md) — remote gateway (preferred) or optional self-hosted Docker
- [Configuration reference](configuration.md) — all YAML fields, sweep expansion, queries format
- [CLI reference](cli-reference.md) — all commands and flags
- [Dashboard guide](dashboard-guide.md) — reading the experiments list, detail screen, and search explorer
- [Troubleshooting](troubleshooting.md) — common errors and fixes
