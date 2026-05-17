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
| MongoDB Atlas | Free tier (M0) | [cloud.mongodb.com](https://cloud.mongodb.com/) — free tier fully supports vector search |
| Voyage AI API key | Optional | [dash.voyageai.com](https://dash.voyageai.com) — only needed for Voyage models; local models need no key |

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

Edit `.env`:

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

**MongoDB Atlas setup** (one-time):
1. [cloud.mongodb.com](https://cloud.mongodb.com/) → create a free cluster
2. **Database Access** → add a user with read/write permissions
3. **Network Access** → add your IP (or `0.0.0.0/0` for local dev)
4. **Connect → Compass** → copy the SRV connection string into `MONGODB_URI`

### 2. Create the Atlas vector index

The vector search index must be created manually in the Atlas UI — the server cannot do this automatically.

1. Atlas UI → your cluster → **Browse Collections** → `chunks` collection → **Search Indexes** tab
2. **Create Search Index** → JSON Editor

For **Voyage AI models** (1024-dim), name: `vector_index_1024`:
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

For **local models** (384-dim), name: `vector_index_384`:
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

Both indexes can coexist on the same collection. Wait ~1–2 minutes for the index to build before running queries.

### 3. Create the Atlas Full Text Search index (sparse/hybrid only)

**Required only if you use `sparse` or `hybrid` retrieval.** Skip this step if you only use `dense`.

1. Same collection view → **Search Indexes** tab → **Create Search Index** → JSON Editor
2. Name: `text_search_index`
3. Paste this definition:

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "text": [{ "type": "string" }],
      "experiment_id": [{ "type": "token" }],
      "embedding_model": [{ "type": "token" }]
    }
  }
}
```

Wait ~1–2 minutes. The `text_search_index` and both vector indexes can all coexist on the same `chunks` collection.

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

```bash
# Local models — no API key needed (90 runs: all chunkers × all retrieval methods)
rag-params-finder run --config configs/example-mongodb-local.yaml

# Voyage AI models — requires VOYAGE_API_KEY in .env
rag-params-finder run --config configs/example-mongodb-voyage.yaml

# Submit and detach (check dashboard for status instead)
rag-params-finder run --config configs/example-mongodb-local.yaml --detach
```

The CLI will:
- Submit the config to the server (experiment name gets a timestamp suffix automatically)
- Display the experiment ID and generated run IDs
- Poll run progress live unless `--detach` is used

Open `http://localhost:5173` to watch live progress and explore results.

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

- [Configuration reference](configuration.md) — all YAML fields, sweep expansion, queries format
- [CLI reference](cli-reference.md) — all commands and flags
- [Dashboard guide](dashboard-guide.md) — reading the experiments list, detail screen, and search explorer
- [Troubleshooting](troubleshooting.md) — common errors and fixes
