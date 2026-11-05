# SQLite Run-State Store Setup

SQLite is the **default** `STORAGE_BACKEND` as of Slice 55 (ADR-008). It stores experiment
metadata, run status, and results in a single local file — no external service required.

SQLite is **run-state only**: it holds `experiments`, `run_status`, and `results` but **not**
vector chunks. You must set `VECTOR_STORE_BACKEND` explicitly to the engine that holds your
vectors (MongoDB Atlas, Postgres/pgvector, or Elasticsearch).

## Quick start

```bash
# .env — only VECTOR_STORE_BACKEND is required for a fresh deployment
STORAGE_BACKEND=sqlite          # already the default; explicit here for clarity
SQLITE_DB_PATH=./data/run_state.db  # default path; override if needed
VECTOR_STORE_BACKEND=mongodb    # or postgres, or elasticsearch
MONGODB_ATLAS_CLOUD_URI=mongodb+srv://...   # required when VECTOR_STORE_BACKEND=mongodb
```

Start the server — the SQLite file and its parent directory are created automatically on first boot:

```bash
uvicorn server.main:app --reload --port 8001
```

Or with Docker Compose (SQLite file is persisted in the `rag-params-finder_sqlite_run_state` named volume):

```bash
VECTOR_STORE_BACKEND=mongodb ./start-services.sh
```

## Configuration reference

| Env var | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `sqlite` | Must be `sqlite` (or omit — it's the default) |
| `SQLITE_DB_PATH` | `./data/run_state.db` | Path to the SQLite file; parent dir created on boot |
| `VECTOR_STORE_BACKEND` | *(required)* | Where vector chunks live: `mongodb`, `postgres`, or `elasticsearch` |

`VECTOR_STORE_BACKEND` has no default when `STORAGE_BACKEND=sqlite`. The server raises a clear error
at startup if it is missing.

## Pairing examples

| Run state | Vectors | .env additions |
|---|---|---|
| SQLite (default) | MongoDB Atlas cloud | `VECTOR_STORE_BACKEND=mongodb` + `MONGODB_ATLAS_CLOUD_URI=...` |
| SQLite (default) | MongoDB Atlas Local | `VECTOR_STORE_BACKEND=mongodb` + `MONGODB_ATLAS_LOCAL_URI=mongodb://localhost:27017/...` |
| SQLite (default) | Local pgvector | `VECTOR_STORE_BACKEND=postgres` + `POSTGRES_LOCAL_URL=postgresql://rag:rag@localhost:5433/rag_params_finder` |
| SQLite (default) | Elasticsearch | `VECTOR_STORE_BACKEND=elasticsearch` + `ELASTICSEARCH_CLOUD_URL=http://localhost:9200` |

## Concurrency and WAL mode

Every SQLite connection opens with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`.
WAL mode allows concurrent reads alongside a single writer and eliminates `SQLITE_BUSY` errors
from the server's `SWEEP_EXECUTOR` and `HEAVY_READ_EXECUTOR` threads running in parallel.

No tuning is required for normal operation. If you observe `SQLITE_BUSY` errors under heavy load
(unlikely with WAL), increase `busy_timeout` by setting `SQLITE_BUSY_TIMEOUT_MS` in `.env`.

## Docker Compose volume

When running with Docker Compose, the SQLite file lives in the `rag-params-finder_sqlite_run_state` named volume
mounted at `/app/data` inside the server container. This persists the file across container restarts:

```yaml
# docker-compose.yml excerpt (already present)
volumes:
  - sqlite_run_state:/app/data
```

The volume is the single home of the run-state DB for Docker runs (DECISIONS #301). Compose sets
`SQLITE_DB_PATH=/app/data/run_state.db` explicitly. Do not open the file directly from the host
and do not use plain `docker cp` on the `.db` file: in WAL mode, recent writes sit in the
`run_state.db-wal` sidecar, so a bare copy can miss them.

To inspect or back up the file from outside the container, take a consistent snapshot with the
SQLite backup API inside the container, then copy the snapshot out:

```bash
docker exec rag-params-finder-server python -c "
import sqlite3
src = sqlite3.connect('file:/app/data/run_state.db?mode=ro', uri=True)
dst = sqlite3.connect('/tmp/run_state.snapshot.db')
src.backup(dst)
dst.close(); src.close()
"
docker cp rag-params-finder-server:/tmp/run_state.snapshot.db ./run_state.snapshot.db
docker exec rag-params-finder-server rm /tmp/run_state.snapshot.db
```

The snapshot is a standalone file; open it with any SQLite tool.

| Host | Run-state location | Host access |
|---|---|---|
| macOS (Docker Desktop) | Named volume inside the Docker VM; not visible in Finder or the host filesystem | `docker exec` backup recipe above |
| Linux | Named volume under `/var/lib/docker/volumes/` (root-owned) | Same recipe; do not read the volume path directly |

Host `uvicorn` runs (no Docker) still use `./data/run_state.db` on the host and need no recipe.

## Health check

`GET /healthz` reports the SQLite run-state under `stores.run_state`:

```json
{
  "ok": true,
  "storage_backend": "sqlite",
  "run_state_mode": "sqlite-local",
  "stores": {
    "run_state": {
      "provider": "sqlite", "mode": "sqlite-local", "ok": true,
      "diagnostics": {
        "path": "/app/data/run_state.db", "exists": true, "inode": 1234567,
        "journal_mode": "wal", "db_size_bytes": 59056128, "wal_size_bytes": 0,
        "quick_check": "ok",
        "counts": { "experiments": 2, "run_status": 124, "results": 7854 }
      }
    },
    "vector":    { "provider": "mongodb", "mode": "mongodb-cloud", "ok": true }
  }
}
```

`diagnostics` (Slice 65B) shows the one DB the server is using: resolved path,
inode, journal mode, file and `-wal` sizes, `quick_check`, and row counts. A
count of `-1` means the table does not exist yet. If the path is not
`/app/data/run_state.db` inside Docker, a second DB has been created.

### Refuse to create a second DB

The default path is anchored to the repo root, so running `uvicorn` from another
folder no longer creates a stray `data/run_state.db`. For a stricter check, set
`RUN_STATE_DB_MUST_EXIST=1`: the server then exits at boot instead of creating a
missing file. It is off by default and `start-services.sh` does not set it yet.

SQLite health is a local writability probe (no network ping). The check creates and removes a
`.sqlite_health_probe` file in the database's parent directory.

## Reverting to MongoDB or Postgres

Set `STORAGE_BACKEND` back to the original engine in `.env` (and omit `VECTOR_STORE_BACKEND` if
both stores were the same engine). No migration is needed — the original collections are unchanged.

```bash
STORAGE_BACKEND=mongodb
MONGODB_ATLAS_CLOUD_URI=mongodb+srv://...
# VECTOR_STORE_BACKEND omitted → defaults to mongodb
```

## Troubleshooting

**`STORAGE_BACKEND=sqlite requires VECTOR_STORE_BACKEND`**
SQLite cannot store vectors. Set `VECTOR_STORE_BACKEND` to your vector engine in `.env`.

**`cannot create parent directory for SQLITE_DB_PATH`**
The path is unwritable. Change `SQLITE_DB_PATH` to a directory the server process can write, or
fix filesystem permissions on the parent directory.

**Pre-SQLite experiments show no infra snapshot**
Experiments created before the SQLite migration have `vector_store_snapshot: null`. The dashboard
renders a graceful null state for those fields — this is expected and not an error.
