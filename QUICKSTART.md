# Quickstart

> Once setup is done, head to the [README](README.md) for features, documentation paths, and contributing.

---

## 🚀 Quick Start

**Prerequisites:** Python 3.12+, Node.js 22+, [MongoDB Atlas account](docs/user-guide/cloud-setup.md#mongodb-atlas-required) (free tier). [Voyage AI](docs/user-guide/cloud-setup.md#voyage-ai-optional) optional for local-only sweeps.

```bash
# Clone and install
git clone https://github.com/neomatrix369/rag-params-finder.git
cd rag-params-finder
uv venv && source .venv/bin/activate
uv pip install -e .
cd frontend && npm install && cd ..

# Configure — see docs/user-guide/cloud-setup.md for minimal Atlas + Voyage checklist
cp .env.example .env

# Start
uvicorn server.main:app --reload --port 8001   # Terminal 1
cd frontend && npm run dev                      # Terminal 2 (optional)

# Sweeps — complete cloud-setup.md checklist first
rag-params-finder run --config configs/example-mongodb-local.yaml   # 120 runs, no API key
rag-params-finder run --config configs/example-mongodb-voyage.yaml  # 40 runs, Voyage + Tier 1
```

Open `http://localhost:5374` to watch live progress and explore results.

### Docker Quick Start (optional)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/), MongoDB Atlas configured ([cloud-setup](docs/user-guide/cloud-setup.md)). Install the CLI on the host (`uv pip install -e .`).

```bash
cp .env.example .env   # set MONGODB_URI (and VOYAGE_API_KEY if needed)
./start-services.sh    # server :8001 + dashboard :5374

# Submit sweeps from the host (CLI is not containerized)
rag-params-finder run --config configs/example-mongodb-local.yaml
```

Dev hot reload: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`. Details: [Slice 14 spec](docs/slices/SLICE-14-DOCKER-COMPOSE.md) · [Development Guide → Docker](docs/contributor-guide/development.md#-docker-compose).

---

## Next steps

- **First experiment walkthrough:** [Getting Started](docs/user-guide/getting-started.md)
- **Full documentation map:** [docs/README.md](docs/README.md)
- **Choose your path (lookup table):** [README → Choose Your Path](README.md#-choose-your-path)
