# Cloud Account Setup

![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)

**Essential, minimal steps** to run the example sweep commands. Official vendor docs are linked; details you can skip are marked *optional*.

---

## Before you run a sweep

Both example configs use **dense + sparse + hybrid** retrieval — you need **two** Atlas search indexes (vector + text), not just one.

### Local sweep — `example-mongodb-local.yaml`

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml
```

| # | Step | Where |
|---|---|---|
| 1 | Atlas account + M0 cluster | [MongoDB → steps 1–2](#mongodb-atlas-required-for-all-sweeps) |
| 2 | Database user + network access | [MongoDB → steps 3–4](#mongodb-atlas-required-for-all-sweeps) |
| 3 | `MONGODB_URI` in `.env` | [MongoDB → step 5](#mongodb-atlas-required-for-all-sweeps) |
| 4 | `vector_index_384` + `text_search_index` on `chunks` | [MongoDB → step 6](#6-create-search-indexes-m0--required-before-sweep) |
| 5 | Server running | `uvicorn server.main:app --reload --port 8001` |

No Voyage account needed.

### Voyage sweep — `example-mongodb-voyage.yaml`

```bash
rag-params-finder run --config configs/example-mongodb-voyage.yaml
```

Complete the **local sweep checklist** above, then add:

| # | Step | Where |
|---|---|---|
| 6 | Voyage account + API key → `VOYAGE_API_KEY` | [Voyage → steps 1–2](#voyage-ai-required-for-voyage-sweep) |
| 7 | Payment method + **≥ $5** usage credits (Tier 1) | [Voyage → step 3](#voyage-ai-required-for-voyage-sweep) |
| 8 | `VOYAGE_RPM_LIMIT=2000` and `VOYAGE_TPM_LIMIT=16000000` in `.env` | [Voyage → step 3](#voyage-ai-required-for-voyage-sweep) |
| 9 | `vector_index_1024` instead of `vector_index_384` | [MongoDB → step 6](#6-create-search-indexes-m0--required-before-sweep) |

Steps 1–5 use `vector_index_384`; step 9 swaps in `vector_index_1024` for Voyage embeddings. You need **both** vector indexes if you run local and Voyage sweeps on the same cluster.

---

## MongoDB Atlas (required for all sweeps)

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

### 3. Unlock Tier 1 rate limits (required for 90-run sweep)

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

# Local — 120 runs, no API key (needs vector_index_384 + text_search_index)
rag-params-finder run --config configs/example-mongodb-local.yaml

# Voyage — 40 runs, requires steps above
rag-params-finder run --config configs/example-mongodb-voyage.yaml
```

Dashboard (optional): `cd frontend && npm run dev` → `http://localhost:5374`

---

## 👉 If something fails

- [Troubleshooting](troubleshooting.md) — index not found, rate limits, dimension mismatch
- [Getting Started](getting-started.md) — install, documents, pause/resume
