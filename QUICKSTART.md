# Quickstart

> Once setup is done, head to the [README](README.md) for features, documentation paths, and contributing.

---

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
./start-services.sh --local
```

Then open `http://localhost:5374`. The Docker stack starts MongoDB Atlas
Local, the API server, and the dashboard.

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

See [Getting Started](docs/user-guide/getting-started.md) for the detailed
experiment setup and [MongoDB Setup](docs/user-guide/mongodb-setup.md) for the
selected database path.

</details>

<details>
<summary>Researcher comparing configurations</summary>

**Prerequisites:**

- Everything required to run experiments
- Example data and question files
- The dashboard is recommended for comparing results
- A local or hosted embedding provider, depending on the experiment

See the [Configuration Reference](docs/user-guide/configuration.md) for sweep
dimensions, parallelism, and Bayesian search.

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

See the [Development Guide](docs/contributor-guide/development.md) for quality
gates, Docker workflows, and the development loop.

</details>

<details>
<summary>Operator or troubleshooter</summary>

Requirements depend on the deployed setup:

- Docker for Docker-managed services
- Atlas credentials and `MONGODB_URI` for MongoDB Atlas Cloud
- Development dependencies are not required unless changing code

See the [Troubleshooting Guide](docs/user-guide/troubleshooting.md) for health
checks, logs, indexes, storage, and recovery procedures.

</details>

---

## Install

```bash
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

cp .env.example .env   # then edit — see mongodb-setup.md
```

> **Naming note:** `example-mongodb-local.yaml` uses **local embedding models** (sentence-transformers), not local MongoDB. Any example config works with either MongoDB backend — only `MONGODB_URI` (or `./start-services.sh --local`) picks the database.

---

## Local stack at a glance

| Service | URL / port | Required? | Started by |
|---------|------------|-----------|------------|
| FastAPI server | `http://localhost:8001` | Yes | `uvicorn` or `./start-services.sh` |
| Dashboard | `http://localhost:5374` | Recommended | `npm run dev` or `./start-services.sh` |
| MongoDB | `localhost:27017` (local) or Atlas cloud | Yes | `./start-services.sh --local`, `./start-services.sh mongodb start`, or Atlas |
| SIE gateway | `http://localhost:8720` | SIE sweeps only | Manual — **not** in `start-services.sh`; see [sie-setup.md](docs/user-guide/sie-setup.md) |

CLI on the host always uses `SERVER_URL=http://localhost:8001` (default in `.env`).

---

## Choose how to start

Pick **one** path. MongoDB must be reachable before the server health check passes (Docker waits for the server; the dashboard waits on the server).

### Path A — Docker + zero cloud (recommended offline)

No Atlas account. MongoDB Atlas Local runs in Docker; indexes are auto-created on boot (~30–60 s first time).

```bash
./start-services.sh --local      # MongoDB + server + dashboard
```

For host CLI sweeps after Path A, use the local URI (also printed by the script):

```bash
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
```

Do **not** run `./start-services.sh` (without `--local`) while `.env` points at `localhost:27017` — the server container cannot reach the host’s `localhost`.

If MongoDB stays unhealthy (`keyfile` / `Unable to acquire security key`), reset stale volumes once after upgrading:

```bash
./start-services.sh mongodb reset && ./start-services.sh --local
```

### Path B — Docker + Atlas cloud (one command)

Requires a real `mongodb+srv://…` URI in `.env` (not the placeholder).

```bash
./start-services.sh              # server :8001 + dashboard :5374
```

### Path C — Manual (two terminals, any MongoDB backend)

Set `MONGODB_URI` in `.env` first ([mongodb-setup.md](docs/user-guide/mongodb-setup.md)).

**Local MongoDB in Docker, server on host:**

```bash
./start-services.sh mongodb start   # blocks until MongoDB is healthy
# .env: MONGODB_URI=mongodb://localhost:27017/rag_params_finder?directConnection=true

uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2 (optional)
```

**Atlas cloud:** create search indexes in the Atlas UI first (M0), then start uvicorn + frontend as above with `mongodb+srv://…` in `.env`.

---

## Verify the stack

```bash
./scripts/health-check.sh        # server /healthz + MongoDB ping + dashboard
curl -s http://localhost:8001/healthz | python3 -m json.tool
```

Expect `"ok": true` and `"mongodb": "ok"`. If the server is unhealthy, see [troubleshooting → Docker](docs/user-guide/troubleshooting.md#docker).

Dev hot reload (Docker): `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` — details in [development.md → Docker Compose](docs/contributor-guide/development.md#docker-compose).

---

## Run a sweep

Complete the checklist for your config in [mongodb-setup → Before you run a sweep](docs/user-guide/mongodb-setup.md#before-you-run-a-sweep).

```bash
rag-params-finder run --config configs/example-mongodb-local.yaml   # 120 runs, no API key
rag-params-finder run --config configs/example-mongodb-voyage.yaml  # 40 runs, Voyage + Tier 1
# rag-params-finder run --config configs/example-mongodb-sie.yaml   # SIE — see sie-setup.md
```

Open `http://localhost:5374` to watch progress and explore results.

---

## Next steps

- **Step-by-step first experiment:** [Getting Started](docs/user-guide/getting-started.md)
- **MongoDB cloud vs local:** [mongodb-setup.md](docs/user-guide/mongodb-setup.md)
- **Full documentation map:** [docs/README.md](docs/README.md)
- **Choose your path (lookup table):** [README → Choose Your Path](README.md#-choose-your-path)
