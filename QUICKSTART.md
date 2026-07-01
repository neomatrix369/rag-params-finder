# Quickstart

> Once setup is done, head to the [README](README.md) for features, documentation paths, and contributing.

---

## 🚀 Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+. MongoDB: [Atlas cloud or local Docker](docs/user-guide/mongodb-setup.md#choose-your-mongodb-backend). [Voyage AI](docs/user-guide/mongodb-setup.md#voyage-ai-required-for-voyage-sweep) optional for local-embedding sweeps.

```bash
# Clone and install
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

# Configure — see docs/user-guide/mongodb-setup.md for minimal Atlas + Voyage checklist
cp .env.example .env

# Start
uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2 (optional)

# Sweeps — complete mongodb-setup.md checklist first
rag-params-finder run --config configs/example-mongodb-local.yaml   # 120 runs, no API key
rag-params-finder run --config configs/example-mongodb-voyage.yaml  # 40 runs, Voyage + Tier 1
# rag-params-finder run --config configs/example-mongodb-sie.yaml   # 80 runs, SIE — remote gateway or optional Docker; see sie-setup.md
```

Open `http://localhost:5374` to watch live progress and explore results.

### Docker Quick Start (optional)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/), MongoDB configured ([mongodb-setup](docs/user-guide/mongodb-setup.md)). Install the CLI on the host (`uv pip install -e .`).

```bash
cp .env.example .env   # set MONGODB_URI (and VOYAGE_API_KEY if needed)
./start-services.sh    # server :8001 + dashboard :5374 (Atlas cloud in .env)

# Zero-cloud dev — no Atlas account; MongoDB Atlas Local in Docker + auto-provisioned indexes:
# ./start-services.sh --local

# Submit sweeps from the host (CLI is not containerized)
rag-params-finder run --config configs/example-mongodb-local.yaml
```

Dev hot reload: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`. Details: [Slice 14 spec](docs/slices/SLICE-14-DOCKER-COMPOSE.md) · [Development Guide → Docker](docs/contributor-guide/development.md#-docker-compose).

---

## Next steps

- **First experiment walkthrough:** [Getting Started](docs/user-guide/getting-started.md)
- **Full documentation map:** [docs/README.md](docs/README.md)
- **Choose your path (lookup table):** [README → Choose Your Path](README.md#-choose-your-path)
