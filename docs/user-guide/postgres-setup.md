# Postgres / pgvector setup

![Postgres](https://img.shields.io/badge/Postgres-4169E1?logo=postgresql&logoColor=white)
![pgvector](https://img.shields.io/badge/pgvector-4169E1?logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?logo=supabase&logoColor=white)

**Essential, minimal steps** to run example sweeps against **one** storage
backend — Postgres with the `pgvector` extension — instead of MongoDB Atlas.

### Supabase vs Postgres (read this first)

| Term | What it is in this project |
|---|---|
| **Postgres + pgvector** | The **only** non-Mongo storage backend (`STORAGE_BACKEND=postgres`). Same SQL adapter for every deployment. |
| **Local Docker** | A `pgvector/pgvector:0.8.5-pg16` container on your laptop (`./start-services.sh --postgres-local`). |
| **Supabase** | A **hosted Postgres product** (managed cloud Postgres + dashboard). We connect with a normal `postgresql://…` URI — not a separate Supabase SDK or API. Start with `./start-services.sh --postgres-cloud`. |
| **`configs/supabase/`** | Example YAML **folder name** for Postgres-path configs (mirrors `configs/mongodb/`). Not a second backend and not `STORAGE_BACKEND`. |
| **`database_provider`** | Engine intent only: `mongodb` \| `postgres`. Deprecated YAML input `supabase` **normalizes to `postgres`** (DeprecationWarning). Location (local vs cloud) comes from the URI → `storage_mode`. |

There is **no** `STORAGE_BACKEND=supabase`. Runtime is always
`STORAGE_BACKEND=postgres` + `DATABASE_URL` (or optional `SUPABASE_URI` alias).
See [configuration.md → Engine × Location](configuration.md#-environment-variables-env).

> **Scope today:** storage (schema, CRUD, cascade delete, db-stats) and
> **dense, sparse, and hybrid** retrieval run end to end. Sparse uses
> `tsvector` / `ts_rank`; hybrid fuses dense + sparse with RRF (`rrf_k=60`).
> SPLADE embedding *storage* (30522-dim) is not available yet — keyword sparse
> does not need it.

---

## Choose your Postgres deployment

Same backend (`STORAGE_BACKEND=postgres`). Only where Postgres runs changes:

| Feature | Path A — Local Docker (`pgvector`) | Path B — Hosted Supabase (managed Postgres) |
|---------|------------------------------------|---------------------------------------------|
| Product | Self-hosted Postgres + pgvector | Supabase-hosted Postgres (+ their dashboard) |
| Dense / sparse / hybrid | identical SQL | identical SQL |
| Schema + indexes | Auto on first pool open | Auto on first pool open |
| Account | None | Supabase project |
| TLS | Off (localhost) | On for `*.supabase.co` (auto) |
| Port / host | `localhost:5433` | `db.<project>.supabase.co:5432` |
| First prove | Short config recommended | Prefer short config (plan limits) |

**Path A** — [Local Docker](#path-a--local-docker) — no cloud account; recommended for development.

**Path B** — [Hosted Supabase](#path-b--hosted-supabase) — same Postgres adapter, cloud URI.

---

## Environment variables

| Variable | Role | Local Docker | Hosted Supabase |
|---|---|---|---|
| `STORAGE_BACKEND` | **Backend selector** — always `postgres` for both paths | `postgres` | `postgres` |
| `DATABASE_URL` | Canonical Postgres connection string | `postgresql://rag:rag@localhost:5433/rag_params_finder` | Session-mode pooler URI (preferred) |
| `SUPABASE_URI` | Optional alias for `DATABASE_URL` (used only when `DATABASE_URL` is unset) | — | Same URI as `DATABASE_URL` |
| `sslmode` (in URI) | TLS override | Usually unset (TLS off) | Usually unset (TLS on for hosted hosts) |

Submitting a `configs/supabase/*.yaml` file while the server still has
`STORAGE_BACKEND=mongodb` (default; legacy alias `mongo`) is rejected with
**HTTP 422** (`Config engine mismatch`) before index preflight or persist.
Use `./start-services.sh --postgres-local` or `--postgres-cloud`, or submit a
`configs/mongodb/` example instead.

### Mongo ↔ Postgres env asymmetry

| Concern | Mongo (today) | Postgres path (local **or** Supabase) |
|---|---|---|
| Connection string | `MONGODB_URI` | `DATABASE_URL` (canonical); optional `SUPABASE_URI` alias — no `POSTGRES_URI` |
| Backend select | Often implicit (`STORAGE_BACKEND` defaults to `mongodb`) | Explicit: `STORAGE_BACKEND=postgres` (or `--postgres-*` flag) |
| Config folder / YAML engine | `configs/mongodb/` · `database_provider: mongodb` | `configs/supabase/` · `database_provider: postgres` (`supabase` input → normalize) |
| Runtime backend token | `mongodb` | `postgres` — Supabase is **not** a separate token |
| Location identity | `storage_mode=mongodb-local\|cloud` | `storage_mode=postgres-local\|cloud` |

---

## Path A — local Docker

![pgvector Docker](https://img.shields.io/badge/pgvector-Docker-4169E1?logo=docker&logoColor=white)

### Quick start (full stack)

```bash
./start-services.sh --postgres-local
```

- **Postgres/pgvector**: `localhost:5433`
- **Server**: `http://localhost:8001` (`STORAGE_BACKEND=postgres`)
- **Dashboard**: `http://localhost:5374`

The container publishes **5433**, not 5432, so an existing local Postgres keeps
working untouched.

### Host CLI / native server

```bash
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
```

### Operational checks (required)

- Liveness: `curl -sS http://127.0.0.1:8001/healthz`
  — expect `"storage_backend": "postgres"`, `"storage_mode": "postgres-local"`, and `"postgres": "ok"`
  (hosted Supabase reports `"storage_mode": "postgres-cloud"`)
- Readiness: `curl -sS http://127.0.0.1:8001/experiments`

`/healthz` can return success while `/experiments` still fails; run both before
judging the stack operational.

### Operational commands

| Action | Command |
|--------|---------|
| Full stack — local Postgres | `./start-services.sh --postgres-local` |
| Full stack — hosted Supabase | `./start-services.sh --postgres-cloud` (requires `DATABASE_URL`; no `MONGODB_URI`) |
| Container only | `docker compose --profile postgres-local up -d postgres-local` |
| Stop Postgres profile | `docker compose --profile postgres-local down` |
| Lifecycle (container only) | `./start-services.sh postgres [start\|stop\|reset\|status]` |
| Wipe local data (volume) | `./start-services.sh postgres reset` |
| Status | `docker ps --filter name=postgres-local` |

Deprecated env alias (still works): `RAG_LOCAL_POSTGRES=1` → `--postgres-local`; compose profile `local-postgres` → `postgres-local`. The old `--postgres` / `-p` flags were removed — use `--postgres-local`.

### Low-friction switching

| From → To | Operator steps |
|-----------|----------------|
| Mongo local → Postgres local | `./start-services.sh --postgres-local` + `configs/supabase/example-local.yaml` |
| Mongo cloud → Postgres cloud | put `DATABASE_URL` in `.env`, `./start-services.sh --postgres-cloud` + `configs/supabase/example-*.yaml` |
| Postgres → Mongo | `--mongodb-local` or `--mongodb-cloud` + matching `configs/mongodb/example-*.yaml` (forces `STORAGE_BACKEND=mongodb` even if `.env` still has a leftover `STORAGE_BACKEND=postgres`) |
| Postgres local → Postgres cloud | `--postgres-cloud` (same `database_provider: postgres` YAML OK after normalize) |

YAML `database_provider: supabase` still loads but normalizes to `postgres`. A wrong engine vs the running server returns **HTTP 422** before index preflight (distinct from catalog missing-index 422).

---

## Path B — hosted Supabase

Supabase here means **managed Postgres in the cloud** (`storage_mode=postgres-cloud`). The app still uses
`STORAGE_BACKEND=postgres` and talks Postgres over `DATABASE_URL` — the same
adapter as Path A.

### 1. Create an account

Register at [supabase.com](https://supabase.com/dashboard)
(email, GitHub, or SSO).

→ [Supabase Dashboard](https://supabase.com/dashboard)

### 2. Create a project

Dashboard → **New project** → pick org, name, region, database password →
**Create**.

→ [Supabase Docs — Creating a project](https://supabase.com/docs/guides/getting-started)

### 3. Copy the connection string

Supabase no longer puts the URI under **Project Settings → Database** (that
sidebar item is gone / moved). Use the project header instead:

1. In the project top bar, click **Connect** (next to the project name).
2. Open the **Direct Connection string** / URI view.
3. Set **Connection Method** to **Session pooler** (port `5432`) — required for our long-lived FastAPI server. Avoid **Transaction pooler** (port `6543`).
4. Copy the URI and replace `[YOUR-PASSWORD]` with the database password you set at project creation.

Deep link (replace the project ref):
`https://supabase.com/dashboard/project/<project-ref>?showConnect=true&method=session`

Your project ref is on **Project Settings → General** (e.g. `wfdtjcbntxssnrullvum`).

→ [Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres)

### 4. Set `.env`

```bash
STORAGE_BACKEND=postgres
# Canonical:
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
# Or product-named alias (used only when DATABASE_URL is unset):
# SUPABASE_URI=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

TLS is applied automatically for hosted Supabase hosts. Override with
`?sslmode=require` (or `disable`) in the URI if needed.

No manual index creation — see [Schema](#schema) below.

### 5. Start the stack

```bash
./start-services.sh --postgres-cloud
```

`ensure_env` requires `DATABASE_URL` or `SUPABASE_URI` and does **not** require `MONGODB_URI`. Bare
`./start-services.sh` with `.env` `STORAGE_BACKEND=postgres` behaves the same.

An unedited placeholder URI (one still containing `<project-ref>`, `<password>`, or `<region>`) is
**rejected before startup** — both the start script and the server's `ensure_storage_ready` fail with a
clear message rather than an opaque connect error. Replace the placeholder with a real Session-mode URI,
or use `--postgres-local` (no cloud URI required).

### Pooler / pause troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| "placeholder DATABASE_URL / SUPABASE_URI" on start | Copied `.env.example` URI unedited (`<project-ref>`) | Paste a real Session-mode URI, or use `--postgres-local` |
| Prepared statement errors | Transaction pooler mode | Use **Session mode** URI from the dashboard |
| Connection timeout on boot | Paused free-tier project | Resume in Supabase UI or upgrade tier; `/healthz` shows `"postgres": "error"` |
| HNSW query failures | Wrong pooler or missing extension | Session mode + `CREATE EXTENSION vector` in SQL editor |

### Hosted limits

Prefer a **short** first prove (16 runs) on free-tier projects. Full 120-run
grids may be slow or hit plan limits. Check current quotas at
[Supabase Pricing](https://supabase.com/pricing) before a large hosted sweep.

Hosted Path B smoke is optional when credentials are unavailable — document the
skip; unit gates for `--postgres-cloud` `ensure_env` (no `MONGODB_URI`) still apply.

---

## Schema

Unlike the Atlas path, **there is no manual index step.** The server applies
[`server/db/schema.sql`](../../server/db/schema.sql) on every boot, idempotently,
so tables, foreign keys, and indexes appear on first start.

| Table | Holds | Notes |
|---|---|---|
| `experiments` | Experiment metadata | Promoted columns + `doc` JSONB |
| `run_status` | Per-run phase tracking | Cascades from `experiments` |
| `chunks` | Text chunks and embeddings | Fully columnar; `embedding_384` and `embedding_1024` |
| `results` | Query results | Cascades from `experiments` |

`chunks` has one nullable vector column per supported embedding width, and every
retrieval query filters by `embedding_model` so vectors from different models are
never compared. Keyword sparse/hybrid uses a generated `text_search` tsvector
column (GIN-indexed). SPLADE embedding storage remains deferred.

### Index preflight

Every experiment submit verifies the catalog before any run starts. If the
`vector` extension or a required index is missing, submit fails with **HTTP 422**
naming the missing objects — no partial sweep.

```bash
rag-params-finder indexes list   # PRESENT / MISSING per object
```

| Object | Needed for |
|---|---|
| `vector` extension | any Postgres sweep |
| `chunks_embedding_384_hnsw` | local 384-dim models |
| `chunks_embedding_1024_hnsw` | Voyage / SIE 1024-dim models |
| `chunks_text_search_gin` | sparse and hybrid retrieval |

Because `schema.sql` creates all of these at pool bootstrap, a 422 here means
bootstrap did not complete — restart the server to re-apply the DDL. There is no
Atlas-style quota to free, so `indexes reset` does not apply to this backend. See
[Troubleshooting → Postgres index preflight failed](troubleshooting.md#-postgres-index-preflight-failed).

---

## Before you run a sweep

**First prove (recommended):** `configs/supabase/example-unified-retrievers.yaml`
(16 runs — dense · sparse · hybrid · cross_encoder). Use
`example-local.yaml` (120 runs) only after a short prove succeeds. Hosted
Supabase: prefer the short config.

### Local embeddings — `example-unified-retrievers.yaml` / `example-local.yaml`

| # | Step | Where |
|---|---|---|
| 1 | Postgres backend ready | [Path A](#path-a--local-docker) or [Path B](#path-b--hosted-supabase) |
| 2 | `STORAGE_BACKEND=postgres` + `DATABASE_URL` | [Environment variables](#environment-variables) |
| 3 | Server healthy (`postgres: ok`) | [Operational checks](#operational-checks-required) |

No Voyage or SIE account needed for local embeddings.

### Voyage sweep — `example-voyage.yaml`

Complete the local checklist, then add Voyage steps from
[MongoDB Setup → Voyage AI](mongodb-setup.md#voyage-ai-required-for-voyage-sweep)
(`VOYAGE_API_KEY`, Tier 1 limits). No Atlas vector indexes required on Postgres.

### SIE sweep — `example-sie.yaml`

Complete the local checklist, then follow
[SIE setup](sie-setup.md#choose-your-path) (`SIE_ENABLED=true`, `SIE_ENDPOINT`,
`SIE_API_KEY` when required). Dense SIE models use `embedding_1024`.

---

## Run the smoke sweep

```bash
./start-services.sh --postgres-local
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder

# Preferred first prove — 16 runs
rag-params-finder run --config configs/supabase/example-unified-retrievers.yaml
```

**Expected:** experiment submitted; runs reach a terminal status; dense, sparse,
hybrid, and cross_encoder each produce results. Watch progress at
`http://localhost:5374`.

Full 120-run twin of the Mongo local grid:

```bash
rag-params-finder run --config configs/supabase/example-local.yaml
```

Shorter Bayesian variants: `*-bayesian.yaml` in the same folder.

No optional `example-local-smoke.yaml` — the unified-retrievers config is the
documented first prove (Slice 43 Won’t).

---

## Dense retrieval (operator note)

Dense search uses pgvector HNSW on `embedding_384` / `embedding_1024`. Scores are
reported on Atlas’s scale (`(1 + cosine) / 2`) so backends stay comparable.

**HNSW warning:** with filters (`experiment_id` / `embedding_model` / `run_id`),
HNSW can return fewer than `LIMIT` rows unless `hnsw.iterative_scan = strict_order`
is on (pgvector ≥ 0.8). Failure mode is **silent** — scores change with no error.
The server sets this on every pooled connection; if logs warn that iterative scan
is unavailable, upgrade pgvector. Design rationale →
[Architecture → Postgres dense retrieval](../contributor-guide/architecture.md#postgres--pgvector-backend).

---

## Troubleshooting

Full symptom → fix list → [Troubleshooting → Postgres / pgvector](troubleshooting.md#postgres--pgvector).

**`curl /healthz` looks wrong or Docker marks the server unhealthy**
On a Postgres stack the probe must report `"storage_backend": "postgres"` and
`"postgres": "ok"`. If you still see only a Mongo health field, rebuild with
`./start-services.sh --postgres-local`. Mongo is not required when
`STORAGE_BACKEND=postgres`. When Postgres is unreachable on a cloud URI,
`/healthz` includes a `remediation` hint (resume paused Supabase / Session-mode pooler).

**`DATABASE_URL not set ... required when STORAGE_BACKEND=postgres`**
Export `DATABASE_URL`, or unset `STORAGE_BACKEND` to fall back to Mongo.

**`could not connect to server` on port 5433**
Container not running or still starting. Check
`docker ps --filter name=postgres-local` and
`docker logs rag-params-finder-postgres-local`.

**`type "vector" does not exist`**
Use `pgvector/pgvector:0.8.5-pg16` (compose default), not stock `postgres`.

**`No Postgres vector column for N-dim embeddings`**
Supported widths are 384 and 1024; see [Schema](#schema).

---

## Diagnostics cheat sheet

```bash
# Is the Postgres container running?
docker ps --filter name=postgres-local

# Container logs
docker logs rag-params-finder-postgres-local

# Does the app see Postgres?
curl -sS http://127.0.0.1:8001/healthz | python3 -m json.tool
# → "storage_backend": "postgres", "postgres": "ok"

# Can the host reach the DB?
docker exec rag-params-finder-postgres-local \
  psql -U rag -d rag_params_finder -c "SELECT 1"

# Did schema bootstrap?
docker exec rag-params-finder-postgres-local \
  psql -U rag -d rag_params_finder -c "\dt"
```

---

## Related docs

- [Getting Started](getting-started.md) — install, first experiment
- [Configuration reference](configuration.md) — YAML + env vars (`STORAGE_BACKEND`)
- [Troubleshooting](troubleshooting.md#postgres--pgvector) — Postgres errors
- [MongoDB Setup](mongodb-setup.md) — Atlas path (comparison)
- [SIE Provider Setup](sie-setup.md) — use SIE with `configs/supabase/example-sie.yaml`
- [Contributor development](../contributor-guide/development.md#testing-strategy) — live Postgres integration tests
