# Quickstart

> Once setup is done, head to the [README](README.md) for features, documentation paths, and contributing.

---

## Contents

- [Choose your path](#choose-your-path)
  - [Visitor / judge](#visitor--judge)
  - [User running experiments](#user-running-experiments)
  - [Researcher comparing configurations](#researcher-comparing-configurations)
  - [Developer extending or debugging the project](#developer-extending-or-debugging-the-project)
  - [Operator or troubleshooter](#operator-or-troubleshooter)
- [Install](#install)
- [Local stack at a glance](#local-stack-at-a-glance)
- [Choose how to start](#choose-how-to-start)
  - [Path A — Docker + zero cloud](#path-a--docker--zero-cloud-recommended-offline)
  - [Path B — Docker + Atlas cloud](#path-b--docker--atlas-cloud-one-command)
  - [Path C — Manual](#path-c--manual-two-terminals-any-mongodb-backend)
  - [Path D — Docker + Postgres/pgvector](#path-d--docker--postgrespgvector-dense-retrieval)
- [Verify the stack](#verify-the-stack)
- [Run a sweep](#run-a-sweep)
- [Next steps](#next-steps)

## Choose your path

### Visitor / judge

Use this path to see the project working with the least setup.

**Prerequisites:**

- Git
- Docker Desktop installed and running

No Atlas account, Voyage AI key, Node.js installation, or local MongoDB
installation is required for this path.

```bash
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
cp .env.example .env
./start-services.sh --mongodb-local
```

For this path, `.env` only needs to exist; no values need to be edited. Then open `http://localhost:5374`. The Docker stack starts MongoDB Atlas Local, the API server, and the dashboard.

<details>
<summary>User running experiments</summary>

**Prerequisites:**

- Git
- Python 3.12+
- `uv`
- MongoDB Atlas Cloud or MongoDB Atlas Local through Docker
- `MONGODB_URI` when using the host CLI
- Voyage AI credentials only for Voyage configurations
- Node.js 22+ and npm only when running the dashboard on the host

See [Getting Started](docs/user-guide/getting-started.md) for the detailed experiment setup and [MongoDB Setup](docs/user-guide/mongodb-setup.md) for the selected database path.

</details>

<details>
<summary>Researcher comparing configurations</summary>

**Prerequisites:**

- Everything required to run experiments
- Example data and question files
- The dashboard is recommended for comparing results
- A local or hosted embedding provider, depending on the experiment

See the [Configuration Reference](docs/user-guide/configuration.md) for sweep dimensions, parallelism, and Bayesian search.

</details>

<details>
<summary>Developer extending or debugging the project</summary>

**Prerequisites:**

- Git
- Python 3.12+
- `uv`
- Node.js 22+ and npm
- Docker Desktop

Install development dependencies with:

```bash
uv pip install -e ".[dev]"
cd frontend && npm install
```

See the [Development Guide](docs/contributor-guide/development.md) for quality gates, Docker workflows, and the development loop.

</details>

<details>
<summary>Operator or troubleshooter</summary>

Requirements depend on the deployed setup:

- Docker for Docker-managed services
- Atlas credentials and `MONGODB_URI` for MongoDB Atlas Cloud
- Development dependencies are not required unless changing code

See the [Troubleshooting Guide](docs/user-guide/troubleshooting.md) for health checks, logs, indexes, storage, and recovery procedures.

</details>

---

<details>
<summary>Install</summary>

```bash
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

cp .env.example .env
```

The `.env.example` file contains the available settings and safe placeholders. The `.env` file is the local, uncommitted configuration read by the server and startup scripts. Edit only the values required by the path you selected:

- Atlas Cloud: set `MONGODB_URI` to the Atlas connection string.
- Atlas Local: leave the placeholders unchanged; `--mongodb-local` supplies the
  container connection internally.
- Voyage: add `VOYAGE_API_KEY` when using a Voyage configuration.
- SIE: enable it and set `SIE_ENDPOINT` when using an SIE configuration.

Keep credentials in `.env`; never put them in committed YAML configs.

> **Naming note:** `configs/mongodb/example-local.yaml` uses **local embedding models** (sentence-transformers), not local MongoDB. Any MongoDB example works with either Atlas backend — only `MONGODB_URI` (or `./start-services.sh --mongodb-local`) picks the database. Matching Supabase/pgvector examples live under `configs/supabase/`.

---
</details>

## Local stack at a glance

| Service | URL / port | Required? | Started by |
|---------|------------|-----------|------------|
| FastAPI server | `http://localhost:8001` | Yes | `./start-services.sh --mongodb-local` / `--postgres-local` / default / `uvicorn` |
| Dashboard | `http://localhost:5374` | Recommended | same as server row, or `npm run dev` |
| MongoDB | `localhost:27017` (local) or Atlas cloud | Mongo path | `./start-services.sh --mongodb-local`, `mongodb start`, or Atlas |
| Postgres/pgvector | `localhost:5433` | Postgres path | `./start-services.sh --postgres-local`, `postgres start`, or hosted URI |
| SIE gateway | `http://localhost:8720` | SIE sweeps only | Manual — **not** in `start-services.sh`; see [sie-setup.md](docs/user-guide/sie-setup.md) |

CLI on the host always uses `SERVER_URL=http://localhost:8001` (default in `.env`).

---

## Choose how to start

Pick **one** path. MongoDB must be reachable before the server health check passes (Docker waits for the server; the dashboard waits on the server).

### Path A — Docker + zero cloud (recommended offline)

No Atlas account. MongoDB Atlas Local runs in Docker; indexes are auto-created on boot (~3 –60 s first time).

Before starting, make sure `.env` exists:

```bash
cp .env.example .env
```

No `.env` values need to be edited for this path.

```bash
./start-services.sh --mongodb-local      # MongoDB + server + dashboard
```

For host CLI sweeps after Path A, use the local URI (also printed by the script):

```bash
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
```

Do **not** run `./start-services.sh` (without `--mongodb-local`) while `.env` points a `localhost:27017` — the server container cannot reach the host’s `localhost`.

If MongoDB stays unhealthy (`keyfile` / `Unable to acquire security key`), reset stale volumes once after upgrading:

```bash
./start-services.sh mongodb reset && ./start-services.sh --mongodb-local
```

<details><summary>Other paths</summary>

### Path B — Docker + Atlas cloud (one command)

Copy `.env.example` to `.env`, then set a real `mongodb+srv://…` value for `MONGODB_URI` (not the placeholder).

```bash
./start-services.sh              # server :8001 + dashboard :5374
```

### Path C — Manual (two terminals, any MongoDB backend)

Copy `.env.example` to `.env` first, then set `MONGODB_URI` for the selected backend ([mongodb-setup.md](docs/user-guide/mongodb-setup.md)).

**Local MongoDB in Docker, server on host:**

```bash
./start-services.sh mongodb start   # blocks until MongoDB is healthy
# .env: MONGODB_URI=mongodb://localhost:27017/rag_params_finder?directConnection=true

uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2 (optional)
```

**Atlas cloud:** create search indexes in the Atlas UI first (M0), then start uvicorn + frontend as above with `mongodb+srv://…` in `.env`.

### Path D — Docker + Postgres/pgvector

No Atlas account. Local `pgvector` on host port **5433** (same Postgres backend as
Supabase-hosted; only the URI differs). Dense, sparse, and hybrid run end to end.
Prefer a short first prove (16 runs).

```bash
cp .env.example .env   # if needed — no cloud URI required for local pgvector
./start-services.sh --postgres-local
```

For host CLI after Path D:

```bash
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
rag-params-finder run --config configs/supabase/example-unified-retrievers.yaml
```

Do **not** run `./start-services.sh` (without `--postgres-local`) while `.env` has
`STORAGE_BACKEND=postgres` and `DATABASE_URL=…@localhost:5433` — the server
container cannot reach the host’s `localhost` (use `--postgres-local`, or run the
server on the host).

If Postgres stays unhealthy or schema bootstrap fails after an image change:

```bash
./start-services.sh postgres reset && ./start-services.sh --postgres-local
```

**Postgres in Docker, server on host** (mirror of Path C):

```bash
./start-services.sh postgres start   # blocks until pgvector is healthy
# STORAGE_BACKEND=postgres
# DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2 (optional)
```

**Hosted Supabase** (same backend, cloud URI): put Session-mode pooler URI in
`.env` as `DATABASE_URL` or optional `SUPABASE_URI`, then
`./start-services.sh --postgres-cloud`. URI comes from the project **Connect**
button (not Project Settings → Database). Details:
[postgres-setup.md → Path B](docs/user-guide/postgres-setup.md#path-b--hosted-supabase).

Full setup: [postgres-setup.md](docs/user-guide/postgres-setup.md).

---
</details>

## Verify the stack

```bash
./scripts/health-check.sh        # /healthz active backend + any local Mongo/Postgres containers + dashboard
curl -s http://localhost:8001/healthz | python3 -m json.tool
```

Expect `"ok": true` plus either `"mongodb": "ok"` (Mongo path) or
`"storage_backend": "postgres"` / `"postgres": "ok"` (Postgres path).
When both local DB containers are running, `health-check.sh` also reports each as healthy.
If the server is unhealthy, see [troubleshooting → Docker](docs/user-guide/troubleshooting.md#docker).

Dev hot reload (Docker): `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` — details in [development.md → Docker Compose](docs/contributor-guide/development.md#docker-compose).

---

## Run a sweep

Complete the checklist for your config in [mongodb-setup → Before you run a sweep](docs/user-guide/mongodb-setup.md#before-you-run-a-sweep)
or [postgres-setup](docs/user-guide/postgres-setup.md) for Postgres/Supabase.

```bash
rag-params-finder run --config configs/mongodb/example-local-bayesian.yaml
# 100 runs using the Bayesian optimizer

rag-params-finder run --config configs/mongodb/example-sie-parallel.yaml
# 120 runs of configs/mongodb/example-local.yaml using the Grid Search run using parallelisation

rag-params-finder run --config configs/mongodb/example-local.yaml   # 120 runs, no API key


rag-params-finder run --config configs/mongodb/example-voyage.yaml  # 40 runs, Voyage + Tier 1
# rag-params-finder run --config configs/mongodb/example-sie.yaml   # SIE — see sie-setup.md

# Postgres/Supabase (Path D — see postgres-setup.md)
rag-params-finder run --config configs/supabase/example-unified-retrievers.yaml
rag-params-finder run --config configs/supabase/example-local.yaml
```

Open `http://localhost:5374` to watch progress and explore results. See [docs/images](https://github.com/neomatrix369/rag-params-finder#-screenshots).

---

## Next steps

- **Step-by-step first experiment:** [Getting Started](docs/user-guide/getting-started.md)
- **MongoDB cloud vs local:** [mongodb-setup.md](docs/user-guide/mongodb-setup.md)
- **Postgres/pgvector:** [postgres-setup.md](docs/user-guide/postgres-setup.md)
- **Full documentation map:** [docs/README.md](docs/README.md)
- **Choose your path (lookup table):** [README → Choose Your Path](README.md#-choose-your-path)
