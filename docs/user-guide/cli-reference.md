# CLI Reference

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

All `rag-params-finder` commands and flags. The server must be running at `SERVER_URL` (default: `http://localhost:8001`) for commands that call the API.

---

## 💻 Commands

### ▶️ `run` — Submit and monitor an experiment

```bash
rag-params-finder run --config <path>
```

Submits the experiment config to the server, then optionally polls run progress in the terminal.

| Flag | Default | Description |
|---|---|---|
| `--config` | required | Path to the YAML experiment config |
| `--detach` | off | Submit and exit immediately; check the dashboard for status |
| `--watch` / `--no-watch` | watch on | Poll the server until the experiment reaches a terminal status (omit with `--detach`) |

**Examples**:
```bash
# Submit and watch progress in the terminal
rag-params-finder run --config configs/example-mongodb-local.yaml

# Submit and detach — open http://localhost:5173 to track status
rag-params-finder run --config configs/example-mongodb-local.yaml --detach

# Submit, print the submission summary, then exit without polling the server
rag-params-finder run --config configs/example-mongodb-local.yaml --no-watch

# Voyage AI experiment (requires VOYAGE_API_KEY in .env)
rag-params-finder run --config configs/example-mongodb-voyage.yaml
```

When watching, the CLI renders a live Rich table showing each run's current phase:

```
Run ID       | Model             | Method    | Size | Overlap | Phase
abc123-run-0 | all-MiniLM-L6-v2  | recursive | 512  | 50      | EMBEDDING
abc123-run-1 | all-MiniLM-L6-v2  | recursive | 512  | 0       | CHUNKING
```

---

### `cancel` — Request cancellation

```bash
rag-params-finder cancel <experiment-id>
```

Posts `POST /experiments/{experiment_id}/cancel`. A running experiment stops after the current run phase completes. Not applicable once the experiment is already in a terminal status.

---

### `delete` — Delete experiment and all associated data

```bash
rag-params-finder delete <experiment-id>
rag-params-finder delete <experiment-id> --force
```

Deletes an experiment and **all** its associated data:
- Experiment metadata
- Run statuses
- Chunks (embeddings)
- Query results

| Flag | Default | Description |
|---|---|---|
| `--force` / `-f` | off | Skip confirmation prompt |

⚠️ **Warning:** This is a **permanent** operation that cannot be undone. Running experiments cannot be deleted — cancel them first.

**Examples**:
```bash
# Delete with confirmation prompt
rag-params-finder delete abc123-def4-5678-90ab-cdefg1234567

# Delete without confirmation (use with caution!)
rag-params-finder delete abc123-def4-5678-90ab-cdefg1234567 --force
```

**Use case:** Free up MongoDB Atlas storage by removing old experiments. The free M0 tier has a 512MB storage limit, and embeddings consume significant space (~40MB per 10k chunks).

---

### `recover` — Retry failed runs *(planned, Slice 10)*

**Not implemented yet.** When shipped, this command will re-execute only runs in **FAILED** *(and optionally **INTERRUPTED**)* phase for an existing experiment, scrubbing stale `chunks` / `results` for those `run_id`s and leaving **COMPLETE** runs untouched. Config comes from the stored experiment document — no YAML trimming required.

Spec and acceptance criteria: [`../slices/SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md).

---

### `version` — Print package version

```bash
rag-params-finder version
```

---

### Listing experiments without a CLI subcommand

There is no `list` or `status` Typer command. Use:

- Dashboard at `http://localhost:5173`, or
- **`GET /experiments`** and **`GET /experiments/{experiment_id}`** ([interactive API docs](http://localhost:8001/docs)), or
- **`curl`** / any HTTP client against the same URLs.

---

## 🔌 API Endpoints

The server exposes a REST API at `http://localhost:8001`. Full interactive docs at `http://localhost:8001/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Health check — returns `{"ok": true}` |
| POST | `/experiments` | Submit an experiment sweep |
| GET | `/experiments` | List all experiments |
| GET | `/experiments/vector-db-stats` | Cluster-grouped vector DB / storage stats for all experiments |
| GET | `/experiments/{id}` | Get experiment details + run statuses |
| GET | `/experiments/{id}/db-stats` | Per-experiment chunk counts, storage estimates, index names |
| GET | `/experiments/{id}/results` | Get query results for an experiment |
| GET | `/experiments/{id}/explore` | Get data for the Search Explorer screen |
| POST | `/experiments/{id}/cancel` | Request cancellation while status is running |
| DELETE | `/experiments/{id}` | Delete experiment and all associated data (chunks, results, run statuses) |
| POST | `/experiments/{id}/recover` | Retry failed / interrupted runs only *(planned — Slice 10)* |
| GET | `/runs/{id}/status` | Get a single run's current phase |

---

## 👉 See Also

- [Getting Started](getting-started.md) — install, configure, and run your first experiment
- [Configuration Reference](configuration.md) — all YAML fields and sweep expansion rules
- [Dashboard Guide](dashboard-guide.md) — reading results in the browser UI
- [Troubleshooting](troubleshooting.md) — fixing common errors
