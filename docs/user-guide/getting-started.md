# Getting Started

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Postgres](https://img.shields.io/badge/Postgres_pgvector-4169E1?logo=postgresql&logoColor=white)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-005571?logo=elasticsearch&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
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
| MongoDB | Cloud M0 or local Docker | **Default path** — see [MongoDB Setup](mongodb-setup.md#choose-your-mongodb-backend) |
| Postgres / pgvector | Local Docker or Supabase-hosted Postgres | **Alternative** — one backend (`STORAGE_BACKEND=postgres`); Supabase is hosted Postgres, not a separate adapter — [Postgres Setup](postgres-setup.md) |
| Elasticsearch | Local Docker or BYO cloud cluster | **Alternative vector store** (vector-only, `VECTOR_STORE_BACKEND=elasticsearch`) — [Elasticsearch Setup](elasticsearch-setup.md) |
| Redis | Local Docker or BYO cloud instance | **Alternative vector store** (vector-only, `VECTOR_STORE_BACKEND=redis`) — [Redis Setup](redis-setup.md) |
| Voyage AI | Optional | Only for Voyage models — see [MongoDB Setup → Voyage AI](mongodb-setup.md#voyage-ai-required-for-voyage-sweep) |
| Docker Desktop + HF_TOKEN | Optional | **Self-hosted SIE only** — remote gateway needs no Docker; see [SIE Provider Setup](sie-setup.md) |

**New to Atlas or Voyage?** Start with **[MongoDB Setup](mongodb-setup.md)** — account creation, connection string, search indexes, API key, and Tier 1 billing (~15 min).

**Prefer Postgres?** See **[Postgres Setup](postgres-setup.md)** — local `./start-services.sh --postgres-local` or **Supabase-hosted Postgres** (`./start-services.sh --postgres-cloud`, same `STORAGE_BACKEND=postgres`); first prove with `configs/supabase/example-unified-retrievers.yaml`.

**Prefer Elasticsearch for vectors?** See **[Elasticsearch Setup](elasticsearch-setup.md)** — `./start-services.sh --elasticsearch-local` pairs a local cluster with MongoDB run state unless `STORAGE_BACKEND=postgres`. First prove with `configs/elasticsearch/example-local.yaml`.

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

Pick **one** run-state backend. The default is **SQLite** (`STORAGE_BACKEND=sqlite`, [ADR-008](../adr/ADR-008-sqlite-central-run-state-store.md),
automatic — no setup needed). MongoDB (`STORAGE_BACKEND=mongodb`) and Postgres
(`STORAGE_BACKEND=postgres` or `./start-services.sh --postgres-*` — local Docker or
Supabase-hosted, same adapter) remain fully supported alternatives. This is independent of which
**vector store** you pick below (MongoDB/Postgres/Elasticsearch/Redis).

### 1. Set environment variables

```bash
cp .env.example .env
```

Pick your **vector store** — each guide takes you from this point to a first smoke sweep:

| Backend | Key environment variables | Setup guide | Notes |
|---|---|---|---|
| **MongoDB** (default) | `MONGODB_ATLAS_CLOUD_URI` or `MONGODB_ATLAS_LOCAL_URI` | [MongoDB Setup](mongodb-setup.md) | For Voyage sweeps: add `VOYAGE_API_KEY` + Tier 1 limits |
| **Postgres** | `STORAGE_BACKEND=postgres`; then **`POSTGRES_CLOUD_URL`** (Supabase) **or `POSTGRES_LOCAL_URL`** (Docker) | [Postgres Setup](postgres-setup.md#environment-variables) | ⚠️ **Cloud wins if both are set** — use one or the other |
| **Elasticsearch** | `VECTOR_STORE_BACKEND=elasticsearch`; `ELASTICSEARCH_LOCAL_URL` or `ELASTICSEARCH_CLOUD_URL` (optional `ELASTICSEARCH_API_KEY`) | [Elasticsearch Setup](elasticsearch-setup.md#environment-variables) | Vector store only; run state defaults to MongoDB |
| **Redis** (vector store) | `VECTOR_STORE_BACKEND=redis`, `REDIS_URL` | [Redis Setup](redis-setup.md#environment-variables) | Vector store only; pairs with MongoDB/Postgres/SQLite run state |
| **Redis** (embedding cache) | `EMBEDDING_CACHE_BACKEND=redis`, `REDIS_URL`, `EMBEDDING_CACHE_REDIS_TTL_S` | [Redis Setup](redis-setup.md#embedding-cache) | Optional shared cache for DoubleWord embeddings — separate from Redis's vector-store role; use one, both, or neither |

Full variable reference: [Troubleshooting → Environment Variables](troubleshooting.md#-environment-variables-reference). Optional Atlas Admin API keys enable cluster tier + storage quota in the dashboard — see `.env.example`.

### 2. Search indexes (Mongo only — Postgres/Elasticsearch/Redis auto-create theirs)

On **Mongo/Atlas**, both example configs use dense + sparse + hybrid — create
**`vector_index_384`** (local) or **`vector_index_1024`** (Voyage or SIE) **and**
**`text_search_index`** on the `chunks` collection.

**M0 free tier:** do this manually in Atlas UI before running a sweep — see [MongoDB Setup → step 6](mongodb-setup.md#6-create-search-indexes-m0--required-before-sweep). M0 allows **3 search indexes cluster-wide**; unknown indexes from other projects consume quota.

**M10+ paid tier:** server creates indexes on startup — check uvicorn logs.

**Verify and fix quota issues** (any Atlas tier):

```bash
rag-params-finder indexes list              # known vs unknown; count vs M0 limit
rag-params-finder indexes reset             # drop unknown indexes + ensure required
rag-params-finder indexes reset --all       # drop all chunks indexes + recreate
```

The server **preflights search indexes** on Mongo when you submit a sweep: it derives required index names from your YAML (embedding dimensions + sparse/hybrid retrieval), checks cluster capacity, and rejects the experiment with **HTTP 422** if indexes are missing or quota is exhausted — before any embedding work starts.

On **Postgres**, schema and HNSW/GIN indexes are applied automatically from
[`schema.sql`](../../server/db/postgres/schema.sql) — no Atlas UI step and no `indexes` CLI.
See [Postgres Setup → Schema](postgres-setup.md#schema).

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
./start-services.sh              # Atlas cloud URI from .env (Mongo default)
./start-services.sh --mongodb-local   # Atlas Local in Docker
./start-services.sh --postgres-local  # local pgvector (STORAGE_BACKEND=postgres)
./start-services.sh --postgres-cloud  # Supabase-hosted (POSTGRES_CLOUD_URL; no MONGODB_ATLAS_CLOUD_URI)
./start-services.sh --elasticsearch-local  # local Elasticsearch; run state defaults to local MongoDB unless STORAGE_BACKEND=postgres
# Note: the old --local / --postgres flags were removed — use the canonical flags above
```

- Server: `http://localhost:8001` (OpenAPI docs at `/docs`)
- Dashboard: `http://localhost:5374`
- Dev hot reload: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`

See [Troubleshooting → Docker](troubleshooting.md#-docker) if startup fails.

---

## ▶️ Run Your First Experiment

**Mongo path:** complete the checklist in **[MongoDB Setup → Before you run a sweep](mongodb-setup.md#before-you-run-a-sweep)** first.

```bash
# Local sweep — checklist items 1–5 (no Voyage)
rag-params-finder run --config configs/mongodb/example-local.yaml

# Voyage sweep — checklist items 1–9
rag-params-finder run --config configs/mongodb/example-voyage.yaml

# SIE sweep — SIE_ENABLED=true + SIE_ENDPOINT (+ SIE_API_KEY if remote); see sie-setup.md
rag-params-finder run --config configs/mongodb/example-sie.yaml

# Submit and detach (check dashboard for status instead)
rag-params-finder run --config configs/mongodb/example-local.yaml --detach
```

**Postgres path** (local or Supabase-hosted): see **[Postgres Setup → Before you run a sweep](postgres-setup.md#before-you-run-a-sweep)**. Prefer the short first prove:

```bash
export STORAGE_BACKEND=postgres
export POSTGRES_LOCAL_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
rag-params-finder run --config configs/supabase/example-unified-retrievers.yaml
```

Mirrored stems (same grids as `configs/mongodb/`): `configs/supabase/example-local.yaml`, `example-voyage.yaml`, `example-sie.yaml`.

**Elasticsearch path** (vector store; run state on MongoDB by default): see **[Elasticsearch Setup](elasticsearch-setup.md)** for index creation. Pairs with MongoDB run state unless `STORAGE_BACKEND=postgres`.

```bash
rag-params-finder run --config configs/elasticsearch/example-local.yaml
```

**Redis path** (embedding cache backend): see **[Redis Setup](redis-setup.md)** for cache configuration. Redis can also serve as a vector-only store; verify your setup in [Configuration reference → Split-store](configuration.md#split-store-vector_store_backend-slice-49b).

```bash
rag-params-finder run --config configs/redis/example-local.yaml
```

### ⚡ Enable parallel sweeps (throughput boost)

Set `execution.parallelism` in the config YAML to run sweep combinations concurrently.

```yaml
execution:
  parallelism: 4  # 1 = sequential (safe default), >1 = concurrent
```

- Use `configs/mongodb/example-local-parallel.yaml` for local-provider throughput tuning.
- Use `configs/mongodb/example-voyage-parallel.yaml` or `configs/mongodb/example-sie-parallel.yaml` for provider-specific parallel demo baselines.
- Keep `1` for deterministic small runs and reserved resource profiles.
- Postgres path: same stems under `configs/supabase/` (same YAML keys; set `STORAGE_BACKEND=postgres`).

Example configs:
- Sequential (`parallelism: 1`):
  - [configs/mongodb/example-local.yaml](../../configs/mongodb/example-local.yaml) · [supabase](../../configs/supabase/example-local.yaml)
  - [configs/mongodb/example-voyage.yaml](../../configs/mongodb/example-voyage.yaml) · [supabase](../../configs/supabase/example-voyage.yaml)
  - [configs/mongodb/example-sie.yaml](../../configs/mongodb/example-sie.yaml) · [supabase](../../configs/supabase/example-sie.yaml)
- Parallel (`parallelism: 4`):
  - [configs/mongodb/example-local-parallel.yaml](../../configs/mongodb/example-local-parallel.yaml) · [supabase](../../configs/supabase/example-local-parallel.yaml)
  - [configs/mongodb/example-voyage-parallel.yaml](../../configs/mongodb/example-voyage-parallel.yaml) · [supabase](../../configs/supabase/example-voyage-parallel.yaml)
  - [configs/mongodb/example-sie-parallel.yaml](../../configs/mongodb/example-sie-parallel.yaml) · [supabase](../../configs/supabase/example-sie-parallel.yaml)

For provider-specific caveats and limits (`1..16`, Voyage/SIE quota behavior, and `on_error` semantics), see [Configuration reference → Parallelism](configuration.md#parallelism-executionparallelism).

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
- [Postgres Setup](postgres-setup.md) — local pgvector or hosted Supabase
- [Elasticsearch Setup](elasticsearch-setup.md) — local cluster or hosted, index configuration, vector store backend
- [Redis Setup](redis-setup.md) — embedding cache backend configuration and optional vector store
- [SIE Provider Setup](sie-setup.md) — remote gateway (preferred) or optional self-hosted Docker
- [Configuration reference](configuration.md) — all YAML fields, sweep expansion, queries format
- [CLI reference](cli-reference.md) — all commands and flags
- [Dashboard guide](dashboard-guide.md) — reading the experiments list, detail screen, and search explorer
- [Troubleshooting](troubleshooting.md) — common errors and fixes
