# ADR-008: SQLite as the Central Run-State Store

**Status**: Proposed
**Date**: 2026-09-29
**Slice**: 55 — SQLite Run-State Store
**Supersedes (partial)**: [ADR-004](ADR-004-postgresql-pgvector-vector-store.md) — DECISIONS #130 only, the clause "the code default stays `mongodb` permanently... no default flip." ADR-004's dual-backend decision (Mongo and Postgres both first-class, independent engines) stands unchanged.

---

## Context

Slices 49A/49B already split run-state storage (`experiments`, `run_status`, `results`) from vector storage (`chunks`) behind two independent ports — `StorageBackend` and `VectorStore` — resolved from two independent settings, `STORAGE_BACKEND` and `VECTOR_STORE_BACKEND`. That work solved *which engine can be asked to hold vectors*. It did not solve a related but distinct problem operators raised:

1. Switching or scaling the vector backend still drags run/experiment history along with it whenever `STORAGE_BACKEND` and `VECTOR_STORE_BACKEND` happen to be the same engine (the common case today).
2. Non-vector data (experiment metadata, run status, query results) consumes Atlas free-tier storage quota alongside embeddings, with no way to separate the two.
3. Comparing experiments across different vector-store choices means comparing history stored in different engines.
4. Seeing run history locally requires a real Mongo or Postgres service running, even though `experiments`/`run_status`/`results` are plain relational data with no vector-search requirement.

The run-state store has never used a feature specific to Mongo or Postgres beyond plain CRUD, cascade delete, and a handful of aggregation queries for dashboard stats (`server/db/ports/storage.py`). Nothing about it requires a document store or a vector-capable engine.

## Decision

Add **SQLite** as a new `StorageBackend` provider — a run-state-**only** engine, the mirror image of how Elasticsearch was added as a vector-**only** engine (`can_host_run_state=False`). SQLite can never be selected as `VECTOR_STORE_BACKEND`; it has no vector capability at all.

| Concern | Choice |
|---|---|
| Runtime select | `STORAGE_BACKEND=sqlite` (new) alongside existing `mongodb` \| `postgres` |
| Connection | A single file at `SQLITE_DB_PATH` (default `./data/run_state.db`), created on first use; `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` on every connection |
| Default | **`STORAGE_BACKEND` now defaults to `sqlite`**, reversing ADR-004/DECISIONS #130's "permanent, no default flip" clause for this one setting. `mongodb` and `postgres` remain fully supported, explicit, non-default choices — nothing is removed |
| Vector pairing | `VECTOR_STORE_BACKEND` must be set **explicitly** when `STORAGE_BACKEND=sqlite` (it can never default to `sqlite`, since sqlite cannot host vectors) |
| Migration | One-time migration of run-state data (experiments, run_status, results) from MongoDB or Postgres into the SQLite file. Vector data (`chunks`) is never touched — chunks stay in `VECTOR_STORE_BACKEND` |
| Deployment | Single file, no separate service/container for a local/single-instance deployment; `docker-compose.yml` mounts a volume for the file path so container restarts persist it, same as the existing Mongo/Postgres data volumes |
| Per-run infra snapshot | **(revised after system-design + risk review)** Split by cost and variance, not one blob: the **experiment** document gains a `vector_store_snapshot` (`provider`, `storage_mode`, `cluster_host` — hostname only, port stripped — `collection_name`, `index_names`, `container`, `image`), captured **once at experiment-creation/preflight time by reusing the index plan `preflight_stores()` already validated** — zero new DB round-trip, and the values are invariant across every run in that experiment (same vector store for the whole sweep). Each **run** document gains only `embedding_dimensions` (a pure model-registry lookup from `run.embedding_model`, no DB call at all — this one *can* vary per run in a mixed-provider sweep). A naive "snapshot at every run creation" design was rejected: it would issue one live catalog query per run (36 extra Postgres `pg_indexes` queries for a 36-run sweep) for data that's identical across the whole experiment. Genuinely dynamic fields (`total_chunks`, `total_results`, storage-size estimates) are explicitly **not** snapshotted anywhere — they stay live-queried |

## Rationale

| Concern | Why SQLite for run state |
|---|---|
| Right-sized engine | Run state needs plain relational CRUD + cascade delete + aggregation — no vector search, no separate network service. A file is sufficient |
| Simpler local dev | Fresh checkout, no `.env` DB vars, `uvicorn` boots and experiment history is visible immediately — no Docker container required for run state |
| Quota relief | Atlas/Supabase free-tier storage is no longer shared with non-vector data |
| Comparable history | Experiment history lives in one place regardless of which vector engine (Mongo/Postgres/Elasticsearch) a given experiment used |
| Reuses the existing seam | `StorageBackend` Protocol, `store_factory.get_storage_backend()`, and the provider-capability pattern (`can_host_run_state`) from Slices 49A/49B/50 already do the necessary abstraction work; SQLite is one more registered provider, not a new architecture |
| Concurrency is handled, not assumed away | The server process is the sole writer (CLI talks to it over HTTP, per ADR-001's two-process split), but *within* that process the background sweep executor and the concurrent-read executor both touch run state. WAL mode + `busy_timeout` handle this; a plain rollback-journal SQLite connection would not |
| Historical accuracy without over-collecting | Today only `database_provider` and `storage_mode` (string labels) are ever persisted per run — everything else the dashboard reports (`cluster_host`, `collection_name`, `index_names`, `embedding_dimensions`) is recomputed **live** against whatever the vector store *currently* is. If that infra changes later (migrated cluster, renamed collection, bumped image), historical experiments would silently show current infra, not what was true when they ran. Snapshotting fixed-at-execution-time identity fields closes that gap, while genuinely dynamic fields (chunk/result counts, storage size) correctly stay live |
| Snapshot cost stays flat regardless of sweep size | Capturing the experiment-level snapshot once (reusing preflight's already-executing, already-validated index-plan query) means a 3-run experiment and a 300-run sweep both pay exactly one extra query, not N. The only per-run addition (`embedding_dimensions`) is a pure registry lookup already available from the run's config — no I/O at all |

## Consequences

### Positive

- Local dev and CI no longer need a live Mongo/Postgres service to exercise run-state code paths — unit tests for the new adapter run with zero external dependencies, which is faster than the existing mocked-client test suites.
- Atlas/Supabase storage quota is no longer consumed by non-vector data.
- Run history is comparable across experiments regardless of vector-store choice.

### Neutral / operational

- **Default flip is provisional, not final** (tracked as Slice 55's own forward-roadmap item): this ADR deliberately reverses ADR-004/DECISIONS #130's permanence claim once, on the strength of run-state's actual feature needs; a follow-up slice will confirm the flip with real-world mileage rather than treating it as immediately re-permanent.
- **Docker/Compose**: the SQLite file path must be a mounted volume (`./data:/app/data` or a named volume), matching the existing pattern for `mongodb_local_data` / `postgres_local_data`. Omitting this silently loses run history on every container restart.
- **Concurrency ceiling**: SQLite assumes a single server *process*. If the deployment model ever moves to multiple server replicas/processes sharing one run-state store, SQLite stops being viable as-is and Postgres remains the correct choice for that environment — not a regression, a known boundary.
- **Capacity**: `experiments`/`run_status`/`results` are small relative to `chunks` (no vectors). A representative sweep — 36 runs × ~1000 queries — produces on the order of tens of thousands of `results` rows; SQLite handles this comfortably. Operators running very large numbers of experiments over a long time horizon should monitor file size and can migrate to `STORAGE_BACKEND=postgres` if SQLite stops fitting their needs — the migration script's Protocol-based copy approach works in either direction.

### Negative / follow-ups

- **Destructive drop step**: after migration is verified, the old run-state collections/tables are deleted from the source engine (decision, not a bug) — mitigated by a mandatory pre-drop backup export and primary-key-hash verification, but this is still a one-way door per environment unless the operator keeps the backup file.
- `MongoStorageBackend`/`PostgresStorageBackend`'s `StorageBackend` method implementations remain in the codebase (still needed by anyone choosing `STORAGE_BACKEND=mongodb`/`postgres`) — a later cleanup slice may reconsider this once/if those choices are formally deprecated.
- Whether to eventually deprecate `mongodb`/`postgres` as `STORAGE_BACKEND` choices entirely (hard cutover) is explicitly **not** decided here — left to a follow-up slice.
- **Container/image snapshot is best-effort, not verified**: it reuses `local_runtime.py`'s existing hardcoded lookup table (the same source `/healthz` already exposes), not true Docker API introspection. True introspection would require mounting the Docker socket into the server container — a real security/ops tradeoff explicitly deferred, not silently assumed equivalent. **Known limitation**: if an operator overrides the actual running image/container via a Compose override, the snapshot still records the hardcoded default and that wrong value is now permanent in historical run-state — today's live-only `/healthz` has the same inaccuracy but it at least self-corrects on the next probe; a snapshot does not. Documented here rather than silently assumed accurate.
- **`cluster_host` redaction requires a fix to `_mongodb_cluster_hint()` first**: as of this writing, Mongo's hint helper (`server/db/mongo/mongo_stats.py`) does not strip the port from the parsed host, unlike Postgres's `_cluster_host()` which does — so "hostname only, no port" is not yet true for Mongo. This slice's Before-Checks must confirm that gap is closed (align Mongo's helper with Postgres's behavior) before the snapshot ships, not after.
- **Pre-existing/migrated experiments have no snapshot**: any experiment created before this field existed (including everything the Slice 55 migration script copies from Mongo/Postgres into SQLite) has `vector_store_snapshot: null`. The API and dashboard must render that gracefully (an explicit "not available" state, not a crash) — this is a required acceptance criterion, not an edge case to discover later.

## Alternatives Considered

- **Postgres as the central run-state store for everyone**: already possible today (`STORAGE_BACKEND=postgres`) and remains fully supported. Rejected as the *default* because it requires a running Postgres service even for a single local experiment — the opposite of the "simpler local dev" motivation.
- **Redis**: evaluated separately for vector storage (Slices 52-53, ADR-007) — not relational, not a natural fit for experiment/run/result CRUD with cascade delete and aggregation queries.
- **In-memory / no persistence**: rejected outright — experiment history must survive server restarts; this is the entire point of the run-state store.
- **Keep `mongodb` as the permanent default forever (ADR-004/DECISIONS #130 as originally written)**: rejected for this decision specifically — the "permanent" clause was written when run-state and vector storage were not yet independently selectable (pre-49A/49B); now that they are, the constraint that motivated permanence (avoiding churn on a single conflated setting) no longer applies to the run-state half of that setting.
- **Hard cutover, deprecating `mongodb`/`postgres` as `STORAGE_BACKEND` choices immediately**: rejected for this slice — keeps existing deployments working unchanged if they explicitly set `STORAGE_BACKEND`, and defers deprecation to a follow-up slice with more evidence.

## References

- Slice: [`docs/plan/slices/05-storage/SLICE-55-SQLITE-RUN-STATE-STORE.md`](../plan/slices/05-storage/SLICE-55-SQLITE-RUN-STATE-STORE.md)
- Superseded clause: [`ADR-004`](ADR-004-postgresql-pgvector-vector-store.md), DECISIONS #130
- Prior seam: Slices 49A/49B (`StorageBackend` / `VectorStore` port split), [`ADR-006`](ADR-006-elasticsearch-vector-store.md) (vector-only provider precedent, mirrored here as run-state-only)
- Operator guide: `docs/user-guide/sqlite-setup.md`
