# Elasticsearch setup

Use this guide when chunks should live in Elasticsearch and experiment run state stays on MongoDB or Postgres. It is the operator path from a clean clone to a smoke sweep and teardown.

## Choose your deployment

Pick one location. The default store stays MongoDB; Elasticsearch is opt-in.

| Mode | When to use it | Command |
|---|---|---|
| `elasticsearch-local` | Laptop, no Elastic Cloud account | `./start-services.sh --elasticsearch-local` |
| `elasticsearch-cloud` | A cluster you already run | `./start-services.sh --elasticsearch-cloud` |

Local mode pairs a run-state store. The default is `mongodb-local`, which does not need psycopg. Set `STORAGE_BACKEND=postgres` before the command to pair local Postgres instead. `STORAGE_BACKEND=elasticsearch` is rejected: Elasticsearch cannot hold experiments, runs, or results.

## Environment variables

The server reads these. The CLI configs do not contain them.

| Variable | Local | Cloud |
|---|---|---|
| `VECTOR_STORE_BACKEND` | `elasticsearch` (set by the start script) | `elasticsearch` |
| `ELASTICSEARCH_CLOUD_URL` / `ELASTICSEARCH_LOCAL_URL` | `http://elasticsearch-local:9200` inside Compose; `http://127.0.0.1:9200` on the host | Your cluster URL |
| `ELASTICSEARCH_API_KEY` | Empty (security is off) | Set when the cluster requires a key |
| `ELASTICSEARCH_INDEX_PREFIX` | `rpf` → index `rpf-chunks` | Same |
| `STORAGE_BACKEND` | `mongodb` unless you set `postgres` | `mongodb` or `postgres` |

Install the client extra before a host-side server: `uv pip install -e ".[elasticsearch]"`. The Compose server image installs that extra only when `SERVER_EXTRAS=elasticsearch`.

## Path A — local Docker

This path needs Docker and about 1 GB of heap for Elasticsearch plus the paired MongoDB container. psycopg is not part of this path.

```bash
uv pip install -e ".[elasticsearch]"
./start-services.sh --elasticsearch-local
```

The script starts Elasticsearch 9.5 (single-node, `xpack.security.enabled=false`, Basic licence, `-Xms1g -Xmx1g`, bound to `127.0.0.1:9200`) and the run-state store. You do not export URLs by hand for this path.

Confirm health:

```bash
curl -sS http://127.0.0.1:8001/healthz | python3 -m json.tool
```

Expect `storage_mode` `elasticsearch-local`, `run_state_mode` `mongodb-local`, and both `stores.vector.ok` and `stores.run_state.ok` true.

## Path B — bring your own

Point the server at an existing cluster. Security and TLS follow that cluster.

```bash
# .env
VECTOR_STORE_BACKEND=elasticsearch
ELASTICSEARCH_CLOUD_URL=https://your-cluster.example:9200
ELASTICSEARCH_API_KEY=your-api-key
STORAGE_BACKEND=postgres
./start-services.sh --elasticsearch-cloud
```

A 401 means the API key was rejected. A TLS error means the URL scheme does not match the cluster.

## Index lifecycle

The adapter creates one index, `rpf-chunks` (or `<ELASTICSEARCH_INDEX_PREFIX>-chunks`), with unquantized HNSW on `embedding_384` and `embedding_1024`. Quantized types (`int8_hnsw`, `bbq_hnsw`) fail preflight. Newly indexed chunks are refreshed before search returns, so a sweep does not observe empty results from a stale refresh interval.

```bash
rag-params-finder indexes list
```

The command calls `GET /api/stores` and prints the mapping summary. `indexes reset` stays Atlas-only.

## Before you run a sweep

1. `GET /healthz` shows the vector store and the run-state store ok.
2. `configs/elasticsearch/example-local.yaml` uses `database_provider: elasticsearch`.
3. The embedding model is 384 or 1024 dimensions. Other sizes fail preflight.
4. Documents are under `input_data/` as for the other backends.

## Run the smoke sweep

```bash
rag-params-finder run --config configs/elasticsearch/example-local.yaml
```

Open the dashboard at `http://localhost:5374`. Store labels read Index and Host. There is no cluster quota bar.

## Switching backends

Use the same YAML shape and change only the vector store. The default run-state pair is `mongodb-local`. Set `STORAGE_BACKEND=postgres` before start to keep run state on Postgres.

```bash
./start-services.sh --mongodb-local
./start-services.sh --postgres-local
./start-services.sh --elasticsearch-local
```

Dense scores use the shared `(1+cos)/2` scale so a top-3 overlap comparison across Mongo, Postgres, and Elasticsearch is meaningful. Ranks are not byte-identical.

## Sizing

Vectors are float32: 384 dimensions are 1.5 KB per chunk and 1024 dimensions are 4 KB, plus the HNSW graph (`m=16`). The local container heap is 1 GB (`-Xms1g -Xmx1g`). Plan disk for the vector bytes and the graph, and keep the process heap large enough for the graph at query time. There is no Atlas-style quota field; stats leave quota empty.

## Troubleshooting

| Symptom | What to do |
|---|---|
| Container never healthy | On Linux set `vm.max_map_count` to at least 262144, then recreate the container |
| 401 | API key missing or wrong for a secured cluster |
| TLS errors | Use `https://` for Elastic Cloud and `http://` for the local security-off node |
| 403 licence non-compliant | The node must be Basic (`xpack.license.self_generated.type=basic`), not a trial feature |
| Zero hits right after insert | Refresh is on by default in this adapter; if you changed it, search after refresh |
| Quantized preflight error | Recreate the index from `server/db/elasticsearch/index_mapping.json` (`hnsw`, not `int8_hnsw`) |
| Dimension mismatch | Only 384 and 1024 are supported |
| HTTP 422 on submit | `database_provider` must be `elasticsearch` while `VECTOR_STORE_BACKEND=elasticsearch` |

## Diagnostics cheat sheet

```bash
curl -sS http://127.0.0.1:9200/_cluster/health
curl -sS http://127.0.0.1:8001/healthz | python3 -m json.tool
curl -sS http://127.0.0.1:8001/api/stores | python3 -m json.tool
rag-params-finder indexes list
./start-services.sh elasticsearch status
```

## Related docs

- [Getting Started](getting-started.md)
- [Configuration](configuration.md)
- [Troubleshooting](troubleshooting.md)
- [ADR-006](../adr/ADR-006-elasticsearch-vector-store.md)
