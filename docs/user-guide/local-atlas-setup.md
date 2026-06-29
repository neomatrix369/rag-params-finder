# Local Atlas Setup

Run the full RAG pipeline — including `$vectorSearch` and `$search` (BM25) — entirely on your laptop using the official `mongodb/mongodb-atlas-local` Docker image. No Atlas cloud account, no 512 MB storage ceiling, no manual UI index creation.

## Prerequisites

- Docker Desktop running
- Project dependencies installed (`uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"`)

## Quick start

### 1. Start the full stack (server + dashboard + local Atlas)

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.local-atlas.yml \
  --profile local-atlas \
  up --build -d
```

- **MongoDB Atlas Local**: `localhost:27017`
- **Server**: `http://localhost:8001`
- **Dashboard**: `http://localhost:5374`

The server connects to `mongodb-local` automatically via the overlay file. All vector and text search indexes are created programmatically on first boot — no Atlas UI step required.

### 2. Run a sweep from the host

```bash
# Set local URI for the host CLI
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"

rag-params-finder run --config configs/example-mongodb-local.yaml
```

### 3. Watch progress

Open `http://localhost:5374` in your browser. The dashboard polls the server every 2 s.

## Local dev (no Docker for server/frontend)

Run MongoDB Atlas Local in Docker and the server + frontend natively — best for fast iteration:

```bash
# Terminal 1 — local Atlas only
docker compose -f docker-compose.yml --profile local-atlas up mongodb-local -d

# Terminal 2 — server
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
uvicorn server.main:app --reload --port 8001

# Terminal 3 — frontend
cd frontend && npm run dev
```

## How it differs from Atlas cloud

| Feature | Atlas Local | Atlas Cloud (M0) |
|---------|-------------|-----------------|
| `$vectorSearch` | ✅ identical syntax | ✅ |
| `$search` (BM25) | ✅ identical syntax | ✅ |
| Index creation | Automatic on boot | Manual via Atlas UI (or auto on M2+) |
| Storage limit | Local disk only | 512 MB (M0 free tier) |
| Atlas Admin API | ❌ not available | ✅ optional |
| Dashboard quota bar | Hidden (no cloud quota) | Shows when Admin API configured |
| Cluster tier/region | Not shown in dashboard | Shown when Admin API configured |

## Switching between cloud and local

The only thing that changes between the two backends is how you start the stack. No code changes, no config changes.

| Action | Command |
|--------|---------|
| Start with local Atlas | `./start-services.sh --local` |
| Start with Atlas cloud | `./start-services.sh` |
| Local Atlas only (no server/frontend) | `./scripts/local-atlas.sh start` |
| Stop local Atlas container | `./scripts/local-atlas.sh stop` |
| Reset local data (wipe volume) | `./scripts/local-atlas.sh reset` |
| Container status + connection string | `./scripts/local-atlas.sh status` |

`RAG_LOCAL_ATLAS=1` is the env-var equivalent of `--local` (useful in CI or scripts):

```bash
RAG_LOCAL_ATLAS=1 ./start-services.sh
```

### CLI URI when running server natively (not Docker)

When you start the server outside Docker but want it to use local Atlas:

```bash
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
uvicorn server.main:app --reload --port 8001
```

To switch back to cloud, restore `MONGODB_URI` in `.env` to the `mongodb+srv://...` string and restart.

The server detects the URI type at startup automatically:
- `*.mongodb.net` URI → Atlas cloud mode (M0-aware search index quota)
- anything else → local mode (all indexes created on boot)

## Indexes

On first boot with a local URI, the server creates all search indexes automatically:

- `vector_index_1024` — Voyage AI + dense SIE models (1024-dim cosine)
- `vector_index_384` — local sentence-transformers (384-dim cosine)
- `vector_index_30522` — SIE SPLADE-v3 learned sparse (30522-dim)
- `text_search_index` — BM25 for sparse and hybrid retrieval

These take about 30–60 seconds to reach `READY` status on first creation. The server logs report progress.

## Resetting data

To wipe all local data and start fresh:

```bash
docker compose -f docker-compose.yml --profile local-atlas down -v
# -v removes the mongodb_local_data named volume
```
