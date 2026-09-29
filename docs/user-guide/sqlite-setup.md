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
MONGODB_URI=mongodb+srv://...   # required when VECTOR_STORE_BACKEND=mongodb
```

Start the server — the SQLite file and its parent directory are created automatically on first boot:

```bash
uvicorn server.main:app --reload --port 8001
```

Or with Docker Compose (SQLite file is persisted in the `sqlite_run_state` named volume):

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
| SQLite (default) | MongoDB Atlas cloud | `VECTOR_STORE_BACKEND=mongodb` + `MONGODB_URI=...` |
| SQLite (default) | MongoDB Atlas Local | `VECTOR_STORE_BACKEND=mongodb` + `MONGODB_URI=mongodb://localhost:27017/...` |
| SQLite (default) | Local pgvector | `VECTOR_STORE_BACKEND=postgres` + `DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder` |
| SQLite (default) | Elasticsearch | `VECTOR_STORE_BACKEND=elasticsearch` + `ELASTICSEARCH_URL=http://localhost:9200` |

## Migrating from MongoDB or Postgres

If you have existing experiments in MongoDB or Postgres, migrate them to SQLite before switching
the default so the server can read them:

```bash
# Dry run — inspect what would be copied (no writes)
uv run python scripts/migrate/migrate_run_state_to_sqlite.py \
  --source mongodb \
  --target ./data/run_state.db

# Execute the migration
uv run python scripts/migrate/migrate_run_state_to_sqlite.py \
  --source mongodb \
  --target ./data/run_state.db \
  --execute

# Verify parity, then optionally drop the source run-state collections
# (chunks are NEVER touched — drop-source is opt-in and run-state only)
uv run python scripts/migrate/migrate_run_state_to_sqlite.py \
  --source mongodb \
  --target ./data/run_state.db \
  --execute \
  --drop-source
```

The script:
- Copies idempotently by primary key (safe to re-run)
- Verifies row counts and a primary-key hash before any drop
- Writes a JSON backup of the source data before `--drop-source` runs
- Never touches `chunks` (vector data stays in the vector store)

If the server boots with a new/empty SQLite file but `MONGODB_URI` or `DATABASE_URL` is configured,
it logs a warning naming this migration script — check those logs after upgrading.

## Concurrency and WAL mode

Every SQLite connection opens with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`.
WAL mode allows concurrent reads alongside a single writer and eliminates `SQLITE_BUSY` errors
from the server's `SWEEP_EXECUTOR` and `HEAVY_READ_EXECUTOR` threads running in parallel.

No tuning is required for normal operation. If you observe `SQLITE_BUSY` errors under heavy load
(unlikely with WAL), increase `busy_timeout` by setting `SQLITE_BUSY_TIMEOUT_MS` in `.env`.

## Docker Compose volume

When running with Docker Compose, the SQLite file lives in the `sqlite_run_state` named volume
mounted at `/app/data` inside the server container. This persists the file across container restarts:

```yaml
# docker-compose.yml excerpt (already present)
volumes:
  - sqlite_run_state:/app/data
```

To inspect or back up the file from outside the container:

```bash
docker cp rag-params-finder-server:/app/data/run_state.db ./run_state.db.bak
```

## Health check

`GET /healthz` reports the SQLite run-state under `stores.run_state`:

```json
{
  "ok": true,
  "storage_backend": "sqlite",
  "run_state_mode": "sqlite-local",
  "stores": {
    "run_state": { "provider": "sqlite", "mode": "sqlite-local", "ok": true },
    "vector":    { "provider": "mongodb", "mode": "mongodb-cloud", "ok": true }
  }
}
```

SQLite health is a local writability probe (no network ping). The check creates and removes a
`.sqlite_health_probe` file in the database's parent directory.

## Reverting to MongoDB or Postgres

Set `STORAGE_BACKEND` back to the original engine in `.env` (and omit `VECTOR_STORE_BACKEND` if
both stores were the same engine). No migration is needed — the original collections are unchanged.

```bash
STORAGE_BACKEND=mongodb
MONGODB_URI=mongodb+srv://...
# VECTOR_STORE_BACKEND omitted → defaults to mongodb
```

## Troubleshooting

**`STORAGE_BACKEND=sqlite requires VECTOR_STORE_BACKEND`**
SQLite cannot store vectors. Set `VECTOR_STORE_BACKEND` to your vector engine in `.env`.

**`cannot create parent directory for SQLITE_DB_PATH`**
The path is unwritable. Change `SQLITE_DB_PATH` to a directory the server process can write, or
fix filesystem permissions on the parent directory.

**Experiments from before the SQLite migration are missing**
Run the migration script (see above) and restart the server. The old data is still in
MongoDB / Postgres and is never deleted without explicit `--drop-source`.

**Dashboard shows old experiments as having no infra snapshot**
Pre-migration experiments have `vector_store_snapshot: null`. The dashboard renders a graceful
null state for those fields — this is expected and not an error.
