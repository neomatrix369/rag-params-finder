# CLI Reference

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

All `rag-params-finder` commands and flags. The server must be running at `SERVER_URL` (default: `http://localhost:8001`) for any command to work.

---

## 💻 Commands

### ▶️ `run` — Submit and monitor an experiment

```bash
rag-params-finder run --config <path>
```

Submits the experiment config to the server, prints the experiment ID and generated run IDs, then polls run progress live.

| Flag | Default | Description |
|---|---|---|
| `--config` | required | Path to the YAML experiment config |
| `--detach` | off | Submit and exit immediately; check the dashboard for status |

**Examples**:
```bash
# Submit and watch progress in the terminal
rag-params-finder run --config configs/example-local.yaml

# Submit and detach — open http://localhost:5173 to track status
rag-params-finder run --config configs/example-local.yaml --detach

# Voyage AI experiment (requires VOYAGE_API_KEY in .env)
rag-params-finder run --config configs/example-voyage-ai.yaml

# Kimchi-hosted embedding sweep (requires KIMCHI_BASE_URL and KIMCHI_API_KEY)
rag-params-finder run --config configs/example-kimchi.yaml
```

When not detached, the CLI renders a live Rich table showing each run's current phase:

```
Run ID       | Model             | Method    | Size | Overlap | Phase
abc123-run-0 | all-MiniLM-L6-v2  | recursive | 512  | 50      | EMBEDDING
abc123-run-1 | all-MiniLM-L6-v2  | recursive | 512  | 0       | CHUNKING
```

---

### 📋 `list` — List all experiments

```bash
rag-params-finder list
```

Queries the server for all experiments and prints a summary table. No flags.

```
ID           | Name                      | Status   | Runs
abc123       | my-sweep-20260506-123456   | complete | 8/8
def456       | local-test-20260506-120000 | running  | 3/8
```

---

### 📊 `status` — Get a single experiment's status

```bash
rag-params-finder status <experiment-id>
```

Prints the current phase and status for all runs in the given experiment.

---

### 🔄 `recover` — Recover interrupted runs

```bash
rag-params-finder recover --experiment-id <id> --auto
```

Manually triggers recovery of any runs that were interrupted (e.g., by a server restart). The server can also be configured to do this automatically on boot via `RECOVER_ON_BOOT=true` in `.env`.

| Flag | Description |
|---|---|
| `--experiment-id` | ID of the experiment to recover |
| `--auto` | Automatically retry all interrupted runs without prompting |

---

## 🔌 API Endpoints

The server exposes a REST API at `http://localhost:8001`. Full interactive docs at `http://localhost:8001/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Health check — returns `{"status": "ok"}` |
| POST | `/experiments` | Submit an experiment sweep |
| GET | `/experiments` | List all experiments |
| GET | `/experiments/{id}` | Get experiment details + run statuses |
| GET | `/experiments/{id}/results` | Get query results for an experiment |
| GET | `/experiments/{id}/explore` | Get data for the Search Explorer screen |
| GET | `/runs/{id}/status` | Get a single run's current phase |
| POST | `/recover` | Trigger manual recovery |

---

## 👉 See Also

- [Getting Started](getting-started.md) — install, configure, and run your first experiment
- [Configuration Reference](configuration.md) — all YAML fields and sweep expansion rules
- [Dashboard Guide](dashboard-guide.md) — reading results in the browser UI
- [Troubleshooting](troubleshooting.md) — fixing common errors
