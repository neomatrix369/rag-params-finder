# Redis setup

Use this guide when chunks should live in Redis and experiment run state stays on MongoDB, Postgres, or SQLite. It is the operator path from a clean clone to a smoke sweep and teardown. Redis is a **vector-only** store: `STORAGE_BACKEND=redis` is rejected.

## Choose your deployment

Pick one location. The default store stays MongoDB; Redis is opt-in.

| Mode | When to use it | Command |
|---|---|---|
| `redis-local` | Laptop, no managed Redis | `./start-services.sh --redis-local` |
| `redis-cloud` | A managed Redis (TLS, `rediss://`) endpoint | `./start-services.sh --redis-cloud` |

Local mode pairs a run-state store. The default is `postgres-local` (D5). Set `STORAGE_BACKEND=mongodb` before the command to pair MongoDB instead. `STORAGE_BACKEND=redis` is rejected: Redis cannot hold experiments, runs, or results.

## Environment variables

The server reads these. The CLI configs do not contain them.

| Variable | Local | Cloud |
|---|---|---|
| `VECTOR_STORE_BACKEND` | `redis` (set by the start script) | `redis` |
| `REDIS_URL` | `redis://redis-local:6379` inside Compose; `redis://127.0.0.1:6379` on the host | `rediss://user:pass@host:6380` |
| `REDIS_INDEX_PREFIX` | `rpf` → index `rpf:chunks` | Same |
| `STORAGE_BACKEND` | `postgres` unless you set `mongodb` | `mongodb`, `postgres`, or `sqlite` |

Install the client extra before a host-side server: `uv pip install -e ".[redis]"`. The Compose server image installs that extra only when `SERVER_EXTRAS=redis`.

## Path A — local Docker

This path needs Docker. The local container is Redis 8 with the Query Engine built in, `--appendonly yes`, `--maxmemory 95mb`, and `--maxmemory-policy volatile-lru`.

```bash
uv pip install -e ".[redis]"
./start-services.sh --redis-local
```

The script starts Redis 8 (bound to `127.0.0.1:6379`) and the run-state store. You do not export URLs by hand for this path.

Confirm health:

```bash
curl -sS http://127.0.0.1:8001/healthz | python3 -m json.tool
```

Expect `storage_mode` `redis-local`, and both `stores.vector.ok` and `stores.run_state.ok` true.

## Path B — bring your own

Point the server at an existing Redis 8+ or Valkey instance with the Query Engine (valkey-search). Security and TLS follow that server.

```bash
# .env
VECTOR_STORE_BACKEND=redis
REDIS_URL=rediss://user:s3cret@your-managed-redis.example:6380
STORAGE_BACKEND=postgres
./start-services.sh --redis-cloud
```

A TLS error means the URL scheme does not match the server (`redis://` for plain, `rediss://` for TLS). Credentials are embedded in `REDIS_URL` and are never logged or surfaced in `/api/stores`.

## Schema

The adapter creates one index, `rpf:chunks` (or `<REDIS_INDEX_PREFIX>:chunks`), on `HASH` keys prefixed `rpf:chunk:`. The index has two `VECTOR HNSW FLOAT32 COSINE` fields: `embedding_384` (384-dim) and `embedding_1024` (1024-dim). Only the relevant field is populated per chunk, so models with different dimensions can share one index safely. TAG fields — `embedding_model`, `experiment_id`, `run_id` — are used as pre-filters on every query so chunks from different models, experiments, and runs never mix.

```bash
rag-params-finder indexes list
```

The command calls `GET /api/stores` and prints the index summary.

## Before you run a sweep

1. `GET /healthz` shows the vector store and the run-state store ok.
2. `configs/redis/example-local.yaml` uses `database_provider: redis`.
3. The embedding model is 384 or 1024 dimensions. Other sizes fail preflight.
4. The Redis instance must have the Query Engine available (`FT._LIST` must not return "unknown command").
5. `maxmemory-policy` must be one of: `noeviction`, `volatile-lru`, `volatile-lfu`, `volatile-random`, `volatile-ttl`. An `allkeys-*` policy fails preflight.
6. Documents are under `input_data/` as for the other backends.

## Run the smoke sweep

```bash
rag-params-finder run --config configs/redis/example-local.yaml
```

Open the dashboard at `http://localhost:5374`. Store labels read Index and Host.

## Switching backends

Use the same YAML shape and change only the vector store. The default run-state pair is `postgres-local`. Set `STORAGE_BACKEND=mongodb` before start to keep run state on MongoDB.

```bash
./start-services.sh --mongodb-local
./start-services.sh --postgres-local
./start-services.sh --redis-local
```

Dense scores use the shared `(1+cos)/2` scale: Redis returns COSINE **distance** `d ∈ [0,2]`; the adapter converts it to `score = 1 − d/2`, identical to `(1+cos)/2`. A top-3 overlap comparison across Mongo, Postgres, Elasticsearch, and Redis is meaningful. Ranks are not byte-identical.

## Sizing

Redis holds data in RAM. Float32 embeddings use `dim × 4` bytes per vector, plus the HNSW graph (`M=16`). The local container is capped at `--maxmemory 95mb`. Based on Slice 52 measurements (~2.1 KB/vector for 384-dim), 95 MB holds roughly 45 000 384-dim vectors. Preflight rejects a sweep that would exceed `maxmemory - used_memory` before any embedding is written.

For production deployments, size Redis to hold peak vectors plus headroom for the HNSW graph. Use `INFO memory` to check `used_memory` and `maxmemory`.

## Backup & recovery

The local profile uses `--appendonly yes` (AOF). Preflight warns — but does not block — when AOF is disabled. With AOF on, a Redis restart reads the append log and restores all vectors. With AOF off, vectors are lost on restart and you must re-run the sweep.

For managed cloud Redis, persistence is handled by the provider; follow their backup guidance.

Manual snapshot: `redis-cli -u $REDIS_URL BGSAVE` writes an RDB snapshot. Wait for `LASTSAVE` to advance before stopping the service.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `FT._LIST` unknown command | Redis is running without the Query Engine. Use Redis 8+ or add the valkey-search module. See [redis-setup.md](redis-setup.md) |
| HTTP 422 — allkeys-lru policy | Change `maxmemory-policy` to `volatile-lru` (or `noeviction`) and restart Redis |
| HTTP 422 — insufficient memory | Increase `--maxmemory`, reduce the sweep size, or delete old experiments |
| Dimension mismatch | Only 384-dim and 1024-dim are supported (not SPLADE 30522-dim) |
| HTTP 422 on submit | `database_provider` must be `redis` while `VECTOR_STORE_BACKEND=redis` |
| Vectors lost after restart | Enable AOF (`--appendonly yes`) before starting the sweep |
| TLS errors | Use `rediss://` for managed endpoints and `redis://` for local |
| Empty results after pause/resume | Preflight checks that the index exists before each run; delete the index to re-create it |
| `STORAGE_BACKEND=redis` rejected | Redis is vector-only; use `mongodb`, `postgres`, or `sqlite` for run state |
| Out-of-memory write error | Reduce sweep parallelism or increase `--maxmemory`; preflight should catch this before embedding |

## Diagnostics cheat sheet

```bash
# Health
curl -sS http://localhost:8001/healthz | python3 -m json.tool

# Store listing (secrets redacted)
curl -sS http://localhost:8001/api/stores | python3 -m json.tool

# Index info
redis-cli -u "$REDIS_URL" FT.INFO rpf:chunks

# Count keys for an experiment
redis-cli -u "$REDIS_URL" --scan --pattern "rpf:chunk:<exp-id>:*" | wc -l

# Check eviction policy
redis-cli -u "$REDIS_URL" INFO memory | grep maxmemory_policy

# Check AOF status
redis-cli -u "$REDIS_URL" INFO persistence | grep aof_enabled

# Snapshot
redis-cli -u "$REDIS_URL" BGSAVE
redis-cli -u "$REDIS_URL" LASTSAVE
```
