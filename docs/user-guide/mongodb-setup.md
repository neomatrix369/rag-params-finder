# MongoDB Setup

![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![SIE](https://img.shields.io/badge/SIE-Superlinked_Inference_Engine-blue)

**Essential, minimal steps** to run the example sweep commands on **Atlas Cloud** or **Atlas Local (Docker)**. Official vendor docs are linked; details you can skip are marked *optional*.

> **Naming note:** `example-mongodb-local.yaml` means **local embedding models** (sentence-transformers, 384-dim) — not local MongoDB. Any example config works on either backend; only `MONGODB_URI` (or `./start-services.sh --local`) selects the database.

---

## Choose your MongoDB backend

| Feature | Atlas Local (Docker) | Atlas Cloud (M0) |
|---------|---------------------|-----------------|
| `$vectorSearch` | identical syntax | identical syntax |
| `$search` (BM25) | identical syntax | identical syntax |
| Index creation | Automatic on boot | Manual via Atlas UI (M0/M2/M5) |
| Storage limit | Local disk only | 512 MB (M0 free tier) |
| Atlas Admin API | not available | optional (dashboard quota bar) |
| Cluster tier/region | not shown in dashboard | shown when Admin API configured |

**Path A** — [Atlas Cloud (M0)](#path-a--atlas-cloud-m0) — free cloud cluster, manual indexes on M0.

**Path B** — [Atlas Local (Docker)](#path-b--atlas-local-docker) — no cloud account, indexes created automatically.

---

## Path A — Atlas Cloud (M0)

Atlas stores chunks, embeddings, and experiment results. Free **M0** is enough.

### 1. Create an account

Register at [cloud.mongodb.com](https://cloud.mongodb.com/) (email, Google, or GitHub).

→ [Create an Atlas Account](https://www.mongodb.com/docs/atlas/tutorial/create-atlas-account/)

### 2. Deploy a free cluster

Atlas UI → **Create** → **M0 (Free)** → pick region → **Create**.

→ [Deploy a Free Tier Cluster](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/)

### 3. Create a database user

**Database Access** → **Add New Database User** → password auth → **Read and write to any database**. Save username and password.

→ [Create a Database User](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/)

### 4. Allow network access

**Network Access** → **Add IP Address** → **Add Current IP Address** (or `0.0.0.0/0` for local dev only).

→ [Configure IP Access List](https://www.mongodb.com/docs/atlas/security/ip-access-list/)

### 5. Set `MONGODB_URI`

**Database** → **Connect** → **Drivers** → copy SRV string → replace `<password>` → set database to `rag_params_finder`:

```
mongodb+srv://<user>:<password>@<cluster>.mongodb.net/rag_params_finder?retryWrites=true&w=majority
```

Paste into `.env`:

```bash
MONGODB_URI=mongodb+srv://...
```

→ [Connect to Your Cluster](https://www.mongodb.com/docs/atlas/driver-connection/)

### 6. Create search indexes (M0 — required before sweep)

On **M0/M2/M5**, indexes must be created in the Atlas UI **before** the sweep reaches the QUERYING phase. Both example configs need **vector + text** indexes.

**6a. Create the `chunks` collection** (if it does not exist):

Atlas UI → **Browse Collections** → database `rag_params_finder` → **Create Collection** → name: `chunks`.

**6b. Create indexes** on `chunks` → **Search Indexes** → **Create Search Index** → **JSON Editor**:

| Sweep | Vector index name | `numDimensions` |
|---|---|---|
| `example-mongodb-local.yaml` | `vector_index_384` | `384` |
| `example-mongodb-voyage.yaml` | `vector_index_1024` | `1024` |
| `example-mongodb-sie.yaml` | `vector_index_1024`, `vector_index_30522` | `1024`, `30522` |
| Both (same cluster) | create **both** | `384` and `1024` |

**Vector index JSON** (set `numDimensions` and name as above):

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

**Text index** (required — both sweeps use sparse/hybrid), name: `text_search_index`:

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

Wait until each index shows **ACTIVE** (~1–2 min).

→ [How to Index Fields for Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/)

**M10+ paid clusters:** skip manual creation — the server creates indexes on startup (check uvicorn logs).

**Quota check:** M0 allows **3 search indexes cluster-wide**. Before your first sweep:

```bash
rag-params-finder indexes list    # count vs limit; known vs unknown
rag-params-finder indexes reset   # drop stray indexes + ensure required
```

The server **preflights** required indexes on experiment submit — missing indexes or exhausted quota returns **HTTP 422** before embedding starts (see [Troubleshooting → Search index preflight failed](troubleshooting.md#-search-index-preflight-failed)).

---

## Path B — Atlas Local (Docker)

![MongoDB Atlas Local](https://img.shields.io/badge/MongoDB_Atlas_Local-Docker-47A248?logo=mongodb&logoColor=white)

Run the full RAG pipeline — including `$vectorSearch` and `$search` (BM25) — on your laptop using the official `mongodb/mongodb-atlas-local` Docker image. No Atlas cloud account, no 512 MB storage ceiling, no manual UI index creation.

**Prerequisites:** Docker Desktop running; project dependencies installed (`uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"`).

> **Verify Docker is ready before continuing.** Docker Desktop can appear open in the
> dock while its daemon is still starting (or has crashed). Run:
> ```bash
> docker info 2>&1 | head -3
> ```
> You should see `Server Version: ...`. If you see `Cannot connect to the Docker daemon`,
> quit and relaunch Docker Desktop, wait ~20 s for the menu-bar icon to show "Running",
> then re-run `docker info` to confirm before proceeding.

### Quick start (full stack)

```bash
./start-services.sh --local
```

- **MongoDB Atlas Local**: `localhost:27017`
- **Server**: `http://localhost:8001`
- **Dashboard**: `http://localhost:5374`

The server connects to `mongodb-local` automatically. All vector and text search indexes are created programmatically on first boot (~30–60 s to reach `READY`).

### Run a sweep from the host

```bash
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
rag-params-finder run --config configs/example-mongodb-local.yaml
```

Open `http://localhost:5374` to watch progress.

### Operational checks (required)

Use these separate flags as a runbook for local service validation:

- `HEALTH_LIVENESS_LOCAL` (start-up level):
  `curl -sS http://127.0.0.1:8001/health`
- `READINESS_DATA_PLANE` (pre-sweep readiness):
  `curl -sS http://127.0.0.1:8001/experiments`

`/health` can return success while `/experiments` still fails; run both before judging the local stack operational.

### Native dev (MongoDB in Docker, server/frontend on host)

```bash
# Terminal 1 — MongoDB only
./start-services.sh mongodb start

# Terminal 2 — server
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
uvicorn server.main:app --reload --port 8001

# Terminal 3 — frontend
cd frontend && npm run dev
```

> **Wait for MongoDB to be healthy before starting uvicorn.** The Atlas Local container
> takes 30–60 s on first boot to initialise its replica set and create indexes. Starting
> uvicorn while it is still starting produces `Connection reset by peer` warnings in the
> server log — those are non-fatal, but the cleanest approach is to wait:
> ```bash
> until [ "$(docker inspect --format='{{.State.Health.Status}}' \
>   rag-params-finder-mongodb-local 2>/dev/null)" = "healthy" ]; do
>   echo "waiting for MongoDB…"; sleep 5
> done
> ```
> Then start uvicorn in Terminal 2. The server log will show `boot OK — server ready`
> with no connection errors.

### Auto-created indexes (local URI)

- `vector_index_1024` — Voyage AI + dense SIE models (1024-dim cosine)
- `vector_index_384` — local sentence-transformers (384-dim cosine)
- `vector_index_30522` — SIE SPLADE-v3 learned sparse (30522-dim)
- `text_search_index` — BM25 for sparse and hybrid retrieval

The server detects URI type at startup:

- `*.mongodb.net` → cloud mode (M0-aware search index quota)
- anything else → local mode (all indexes created on boot)

---

## Switching backends

The only thing that changes between backends is how you start the stack. No code changes, no config file changes.

| Action | Command |
|--------|---------|
| Full stack — local Atlas | `./start-services.sh --local` |
| Full stack — Atlas cloud | `./start-services.sh` |
| MongoDB container only | `./start-services.sh mongodb start` |
| Stop local MongoDB | `./start-services.sh mongodb stop` |
| Wipe local data (volume) | `./start-services.sh mongodb reset` |
| Status + connection string | `./start-services.sh mongodb status` |

`RAG_LOCAL_ATLAS=1 ./start-services.sh` is the env-var equivalent of `--local` (CI/script-friendly).

To switch back to cloud: restore `MONGODB_URI` in `.env` to the `mongodb+srv://...` string and run `./start-services.sh` (no `--local`).

Reset all local data: `docker compose --profile local-atlas down -v`

`RECOVERY_INTENT_EXPLICIT` requirement: only run `./start-services.sh mongodb reset` after a deliberate operator-confirmation step that acknowledges local data will be removed.

---

## Before you run a sweep

Both example configs use **dense + sparse + hybrid** retrieval — you need **vector + text** search indexes (auto on Path B; manual on Path A M0).

### Local embeddings sweep — `example-mongodb-local.yaml`

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml
```

| # | Step | Where |
|---|---|---|
| 1 | MongoDB backend ready | [Path A steps 1–5](#path-a--atlas-cloud-m0) or [Path B](#path-b--atlas-local-docker) |
| 2 | `vector_index_384` + `text_search_index` on `chunks` | Path A [step 6](#6-create-search-indexes-m0--required-before-sweep) — skip on Path B |
| 3 | Server running | `uvicorn server.main:app --reload --port 8001` or `./start-services.sh [--local]` |

No Voyage account needed.

### Voyage sweep — `example-mongodb-voyage.yaml`

```bash
rag-params-finder run --config configs/example-mongodb-voyage.yaml
```

Complete the **local embeddings sweep checklist** above, then add:

| # | Step | Where |
|---|---|---|
| 4 | Voyage account + API key → `VOYAGE_API_KEY` | [Voyage → steps 1–2](#voyage-ai-required-for-voyage-sweep) |
| 5 | Payment method + **≥ $5** usage credits (Tier 1) | [Voyage → step 3](#voyage-ai-required-for-voyage-sweep) |
| 6 | `VOYAGE_RPM_LIMIT=2000` and `VOYAGE_TPM_LIMIT=16000000` in `.env` | [Voyage → step 3](#voyage-ai-required-for-voyage-sweep) |
| 7 | `vector_index_1024` instead of `vector_index_384` | Path A [step 6](#6-create-search-indexes-m0--required-before-sweep) |

You need **both** vector indexes if you run local-embedding and Voyage sweeps on the same cloud cluster.

### SIE sweep — `example-mongodb-sie.yaml`

```bash
rag-params-finder run --config configs/example-mongodb-sie.yaml
```

Complete the **local embeddings sweep checklist** above, then add:

Set `SIE_ENABLED=true` for either path below — it is the **same on/off flag**; only `SIE_ENDPOINT` (and usually `SIE_API_KEY` on remote) differ.

| # | Step | Where |
|---|---|---|
| 4 | **Remote gateway:** `SIE_ENABLED=true`, `SIE_ENDPOINT`, `SIE_API_KEY` in `.env` — **no Docker** | [SIE setup → Path A](sie-setup.md#choose-your-path) |
| 4′ | **Or self-hosted Docker:** SIE container warm (encode probe HTTP 200) | [SIE setup → Path B](sie-setup.md#self-hosted-docker-optional) |
| 5 | `vector_index_1024` + `text_search_index` on `chunks` | Path A [step 6](#6-create-search-indexes-m0--required-before-sweep) |

Dense SIE models (bge-m3, stella-v5) use `vector_index_1024`. Sparse/hybrid retrievers need `text_search_index`. The example config uses **2 of 3** M0 search-index slots (`splade-v3` deferred — exceeds Atlas 4096-dim limit).

No Voyage API key needed.

**Quick API demo (no YAML):** `POST /api/v1/sweep` — see [SIE setup §6](sie-setup.md#6-quick-smoke-test).

---

## Voyage AI (required for Voyage sweep)

Skip entirely for `example-mongodb-local.yaml`.

### 1. Create an account

Sign up at [dash.voyageai.com](https://dash.voyageai.com).

→ [API Key and Python Client](https://docs.voyageai.com/docs/api-key-and-installation)

### 2. Create an API key

Dashboard → **API Keys** → **Create new secret key** → add to `.env`:

```bash
VOYAGE_API_KEY=vo-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Unlock Tier 1 rate limits (required for 40-run Voyage sweep)

Without billing, Voyage caps you at **3 RPM / 10,000 TPM** — a full sweep will hit rate limits and fail.

1. Add payment method: [Billing → Payment methods](https://dashboard.voyageai.com/organization/billing/payment-methods)
2. Add **≥ $5 USD** credits: [Billing → Add to credit balance](https://dashboard.voyageai.com/organization/billing)
3. Confirm Tier 1 at [Organization → Rate Limits](https://dashboard.voyageai.com/organization/rate-limits)
4. Set in `.env` and **restart uvicorn** (comment out free-tier defaults, uncomment Tier 1 lines — see `.env.example`):

```bash
# Voyage rate limits - Tier 1
VOYAGE_RPM_LIMIT=2000
VOYAGE_TPM_LIMIT=16000000
```

→ [Voyage Rate Limits](https://docs.voyageai.com/docs/rate-limits) · [Prepaid billing FAQ](https://docs.voyageai.com/docs/faq#how-can-i-set-up-prepaid-billing) · [Pricing](https://docs.voyageai.com/docs/pricing)

*Optional:* monitor usage at [dash.voyageai.com/usage](https://dash.voyageai.com/usage).

---

## Run the sweep

```bash
cp .env.example .env          # once — then fill MONGODB_URI (+ Voyage vars if needed)
uvicorn server.main:app --reload --port 8001

# Local embeddings — 120 runs, no API key (needs vector_index_384 + text_search_index on cloud M0)
rag-params-finder run --config configs/example-mongodb-local.yaml

# Voyage — 40 runs, requires Voyage steps above
rag-params-finder run --config configs/example-mongodb-voyage.yaml
```

Dashboard (optional): `cd frontend && npm run dev` → `http://localhost:5374`

Docker stack (optional): `./start-services.sh` (cloud) or `./start-services.sh --local`

---

## If something fails

- [Troubleshooting](troubleshooting.md) — index not found, rate limits, dimension mismatch
- [Getting Started](getting-started.md) — install, documents, pause/resume
