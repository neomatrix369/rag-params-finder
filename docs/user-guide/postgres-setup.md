# Postgres / pgvector setup

How to run `rag-params-finder` against Postgres with the `pgvector` extension
instead of MongoDB Atlas.

Two targets share this backend:

| Target | When to use | Connection string |
|---|---|---|
| Local Docker (`pgvector/pgvector:pg16`) | Development and tests, no cloud account | `postgresql://rag:rag@localhost:5433/rag_params_finder` |
| Supabase (hosted Postgres) | Shared or deployed environments | `postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres` |

TLS is applied automatically for `*.supabase.co` hosts and left off for local
containers. Set `sslmode` explicitly in the URI to override either default.

> **Scope today:** storage (schema, CRUD, cascade delete, db-stats) and **dense**
> retrieval are working, so a dense-only sweep runs end to end on Postgres.
> Sparse and hybrid retrieval arrive in Slice 35 — until then they raise a clear
> error rather than falling back to dense, which would silently change what a
> sweep is measuring. Use `STORAGE_BACKEND=mongo` if you need them today.

---

## Path A — local Docker (recommended for development)

```bash
./start-services.sh --postgres
```

That starts the `pgvector` container alongside the server and dashboard, and
points the server at it with `STORAGE_BACKEND=postgres`.

For the host CLI or a natively-run server:

```bash
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
```

The container publishes **5433**, not 5432, so an existing local Postgres keeps
working untouched.

### Container only

```bash
docker compose --profile local-postgres up -d postgres-local
```

### Reset the data

```bash
docker rm -f rag-params-finder-postgres-local
docker volume rm rag-params-finder_postgres_local_data
```

---

## Path B — hosted Supabase

1. Create a project at <https://supabase.com/dashboard>.
2. Copy **Settings → Database → Connection string** (Session mode pooler).
3. Put it in `.env`:

```bash
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
```

No dashboard clicking is needed beyond that — see *Schema* below.

---

## Schema

Unlike the Atlas path, **there is no manual index step.** The server applies
[`server/db/schema.sql`](../../server/db/schema.sql) on every boot, idempotently,
so tables, foreign keys, and indexes appear on first start.

| Table | Holds | Notes |
|---|---|---|
| `experiments` | Experiment metadata | Promoted columns + `doc` JSONB |
| `run_status` | Per-run phase tracking | Cascades from `experiments` |
| `chunks` | Text chunks and embeddings | Fully columnar; `embedding_384` and `embedding_1024` |
| `results` | Query results | Cascades from `experiments` |

Queryable fields (`experiment_id`, `status`, timestamps, `phase`, …) are real
columns; the rest of each document lives in a `doc` JSONB column. That keeps the
document-shaped `StorageBackend` contract intact without a migration every time
a field is added.

`chunks` has one nullable vector column per supported embedding width, and every
retrieval query filters by `embedding_model` so vectors from different models are
never compared. A model whose width has no column — such as SPLADE-v3's 30522-dim
sparse vectors — raises a clear error rather than being silently dropped; sparse
storage lands in Slice 35.

---

## Run the smoke sweep

```bash
./start-services.sh --postgres
export STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://rag:rag@localhost:5433/rag_params_finder
rag-params-finder run --config configs/example-postgres-local.yaml
```

`configs/example-postgres-local.yaml` is deliberately small — four runs with
local 384-dim embeddings and dense retrieval only.

---

## Dense retrieval

Dense search ranks chunks by cosine similarity using pgvector's `<=>` operator
against HNSW indexes on `embedding_384` and `embedding_1024`.

Scores are reported on **Atlas's scale**, `(1 + cosine) / 2`, so an identical
vector scores `1.0` and an orthogonal one `0.5`. pgvector returns a cosine
*distance* instead, so the query converts it with `1 - distance / 2`. Without
that conversion the two backends would report different numbers for identical
retrieval quality, and comparing them would be meaningless.

### Why `hnsw.iterative_scan` is switched on

An HNSW index cannot apply a `WHERE` clause inside itself. The mandatory
`experiment_id` / `embedding_model` / `run_id` filters therefore run *after* the
index returns its candidate set, and anything filtered out is lost from the
top-k. Measured on a 2 472-chunk table with the planner forced onto HNSW, a query
asking for 20 rows came back with **3**.

Every pooled connection therefore sets `hnsw.iterative_scan = strict_order`
(pgvector ≥ 0.8), which keeps re-scanning until the limit is satisfied, in exact
distance order. On an older pgvector the server logs a warning and Postgres falls
back to an exact non-index scan — slower, but never short.

If you see that warning, upgrade pgvector rather than ignoring it: a truncated
result set changes the scores a sweep reports without any visible error.

---

## Tests

The Postgres adapter's integration tests need a live database:

```bash
./start-services.sh --postgres
uv run pytest tests/test_postgres_store_integration.py \
              tests/test_postgres_dense_retrieval.py -q
```

Without a reachable database they skip, so the default suite stays green on a
machine with no Docker. Point them elsewhere with `RAG_TEST_DATABASE_URL`. CI
sets `RAG_REQUIRE_POSTGRES=1`, which turns an unreachable database into a
failure instead of a skip — otherwise a broken service container would report
green forever.

---

## Troubleshooting

**`curl /healthz` returns `"mongodb": "error"` (or Docker marks the server unhealthy)**
On a Postgres stack the probe must report `"storage_backend": "postgres"` and
`"postgres": "ok"`. If you still see a Mongo field, the running image is older
than this behaviour — rebuild with `./start-services.sh --postgres`. Mongo is
not required when `STORAGE_BACKEND=postgres`.

**`DATABASE_URL not set ... required when STORAGE_BACKEND=postgres`**
The backend was selected but no connection string was given. Export
`DATABASE_URL`, or unset `STORAGE_BACKEND` to fall back to Mongo.

**`could not connect to server` on port 5433**
The container is not running or is still starting. Check with
`docker ps --filter name=postgres-local` and
`docker logs rag-params-finder-postgres-local`.

**`type "vector" does not exist`**
The image lacks the extension. Use `pgvector/pgvector:pg16` rather than the
stock `postgres` image; `schema.sql` runs `CREATE EXTENSION IF NOT EXISTS vector`
but cannot install what is not present.

**`No Postgres vector column for N-dim embeddings`**
The chosen embedding model's width has no column. Supported widths are 384 and
1024; see *Schema* above.

---

## See also

- [`mongodb-setup.md`](mongodb-setup.md) — the MongoDB Atlas path
- [`configuration.md`](configuration.md) — full environment variable reference
- [`../adr/ADR-003-mongodb-atlas-vector-store.md`](../adr/ADR-003-mongodb-atlas-vector-store.md) — why Atlas was chosen originally
