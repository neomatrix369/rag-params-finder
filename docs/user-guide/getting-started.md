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
| Kimchi API key | Optional | Only needed for Kimchi-hosted embedding sweeps |

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

# Optional — only needed for Kimchi-hosted embedding models
KIMCHI_BASE_URL=https://llm.cast.ai/openai
KIMCHI_API_KEY=kimchi-xxxxxxxxxxxxxxxxxxxxxxxx

# Optional — defaults shown
SERVER_URL=http://localhost:8001
VOYAGE_RPM_LIMIT=300
VOYAGE_TPM_LIMIT=1000000
KIMCHI_RPM_LIMIT=60
KIMCHI_TPM_LIMIT=0
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

```bash
# Local models — no API key needed
rag-params-finder run --config configs/example-local.yaml

# Voyage AI models — requires VOYAGE_API_KEY in .env
rag-params-finder run --config configs/example-voyage-ai.yaml

# Kimchi-hosted embeddings — requires KIMCHI_BASE_URL and KIMCHI_API_KEY in .env
rag-params-finder run --config configs/example-kimchi.yaml

# Submit and detach (check dashboard for status instead)
rag-params-finder run --config configs/example-local.yaml --detach
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
