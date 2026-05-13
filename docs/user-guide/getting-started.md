# Getting Started

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-FF9D00?logo=huggingface&logoColor=white)

Everything you need to run your first RAG parameter sweep experiment.

---

## ✅ Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | Install via [python.org](https://www.python.org/downloads/) or `pyenv install 3.12.2` |
| Node.js | 22+ | Install via [nodejs.org](https://nodejs.org/) or `nvm install 22` |
| MongoDB Atlas | Free tier (M0) | **Required** — see [Cloud Account Setup](cloud-setup.md#mongodb-atlas-required) |
| Voyage AI | Optional | Only for Voyage models — see [Cloud Account Setup](cloud-setup.md#voyage-ai-optional) |
| Kimchi API key | Optional | Only for Kimchi-hosted embedding sweeps |

**New to Atlas or Voyage?** Start with **[Cloud Account Setup](cloud-setup.md)** — account creation, connection string, search indexes, API key, and Tier 1 billing (~15 min).

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

# Required for Voyage sweep only — see cloud-setup.md checklist
VOYAGE_API_KEY=vo-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Uncomment Tier 1 limits in .env.example (comment out free-tier defaults first)
VOYAGE_RPM_LIMIT=2000
VOYAGE_TPM_LIMIT=16000000

# Optional — only needed for Kimchi-hosted embedding models
KIMCHI_BASE_URL=https://api.navy
KIMCHI_API_KEY=kimchi-xxxxxxxxxxxxxxxxxxxxxxxx
KIMCHI_RPM_LIMIT=60
KIMCHI_TPM_LIMIT=0

SERVER_URL=http://localhost:8001
```

Full variable reference: [Troubleshooting → Environment Variables](troubleshooting.md#-environment-variables-reference). Optional Atlas Admin API keys enable cluster tier + storage quota in the dashboard — see `.env.example`.

### 2. Search indexes (required before sweep)

Both example configs use dense + sparse + hybrid — create **`vector_index_384`** (local) or **`vector_index_1024`** (Voyage) **and** **`text_search_index`** on the `chunks` collection.

**M0 free tier:** do this manually in Atlas UI before running a sweep — see [Cloud Account Setup → step 6](cloud-setup.md#6-create-search-indexes-m0--required-before-sweep). M0 allows **3 search indexes cluster-wide**; unknown indexes from other projects consume quota.

**M10+ paid tier:** server creates indexes on startup — check uvicorn logs.

**Verify and fix quota issues** (any tier):

```bash
rag-params-finder indexes list              # known vs unknown; count vs M0 limit
rag-params-finder indexes reset             # drop unknown indexes + ensure required
rag-params-finder indexes reset --all       # drop all chunks indexes + recreate
```

The server **preflights search indexes** when you submit a sweep: it derives required index names from your YAML (embedding dimensions + sparse/hybrid retrieval), checks cluster capacity, and rejects the experiment with **HTTP 422** if indexes are missing or quota is exhausted — before any embedding work starts.

For **Kimchi models**, dimensions are detected at runtime. The server will try to create
`vector_index_<dimension>` automatically when the first query embedding is generated. If
your Atlas tier does not support programmatic search index creation, create the same JSON
shape manually with the dimension from the server log.

All vector indexes can coexist on the same collection. Wait ~1–2 minutes for the index to build before running queries.

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

```bash
# Terminal 1: FastAPI server
uvicorn server.main:app --reload --port 8001

# Terminal 2: React dashboard (optional)
cd frontend && npm run dev
```

- Server: `http://localhost:8001` (OpenAPI docs at `/docs`)
- Dashboard: `http://localhost:5173`

---

## ▶️ Run Your First Experiment

Complete the checklist for your sweep path in **[Cloud Account Setup → Before you run a sweep](cloud-setup.md#before-you-run-a-sweep)** first.

```bash
# Local sweep — checklist items 1–5 (no Voyage)
rag-params-finder run --config configs/example-mongodb-local.yaml

# Voyage sweep — checklist items 1–9
rag-params-finder run --config configs/example-mongodb-voyage.yaml

# Kimchi-hosted embeddings — requires KIMCHI_BASE_URL and KIMCHI_API_KEY in .env
rag-params-finder run --config configs/example-kimchi.yaml

# Submit and detach (check dashboard for status instead)
rag-params-finder run --config configs/example-mongodb-local.yaml --detach
```

The CLI will:
- Submit the config to the server (experiment name gets a timestamp suffix automatically)
- Display the experiment ID and generated run IDs
- Poll run progress live unless `--detach` is used

Open `http://localhost:5173` to watch live progress and explore results.

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

- [Cloud Account Setup](cloud-setup.md) — Atlas account, Voyage billing, search indexes
- [Configuration reference](configuration.md) — all YAML fields, sweep expansion, queries format
- [CLI reference](cli-reference.md) — all commands and flags
- [Dashboard guide](dashboard-guide.md) — reading the experiments list, detail screen, and search explorer
- [Troubleshooting](troubleshooting.md) — common errors and fixes
