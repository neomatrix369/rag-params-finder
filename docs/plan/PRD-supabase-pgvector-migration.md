# PRD: Migrate Vector/Data Store to Supabase (pgvector) — Dual-Backend

| Field | Value |
|---|---|
| Repo | rag-params-finder |
| Current backend | MongoDB Atlas Vector Search ([ADR-003](../adr/ADR-003-mongodb-atlas-vector-store.md), Accepted) |
| Target backend | **Supabase** (hosted PostgreSQL + `pgvector`) + local Docker pgvector for dev parity |
| Status | Approved — team owns integration |
| Source | Vendor due-diligence 2026-07-09; plan integration 2026-07-09 |
| Document type | Implementation PRD (plan SSOT) |

## Glossary

| Term | Meaning |
|---|---|
| **Supabase** | Hosted product: managed PostgreSQL + dashboard + Auth. The app connects via a standard Postgres `DATABASE_URL` (pooler or direct). |
| **Postgres / pgvector** | The database engine and extension the app actually queries. Supabase **is** Postgres under the hood. |
| **Local pgvector** | Docker `pgvector` image for dev — same SQL/API as Supabase, no Supabase platform features. |
| **Dual-backend** | `STORAGE_BACKEND=mongo` or `postgres`; Mongo adapter retained through cutover for rollback and A/B comparison. |

## Goal

Replace MongoDB Atlas as the *primary* storage backend with Supabase (PostgreSQL + pgvector), **via a dual-backend storage abstraction** so Mongo remains available for rollback and side-by-side retrieval-quality comparison until cutover gates pass.

## Non-goals

- Changing embedding providers (`embedder_factory.py`)
- Frontend UX redesign beyond API shape needs
- Byte-identical retrieval scores vs Atlas
- Removing the Mongo adapter in this cycle (post–Slice 38 cleanup only)

## Resolved decisions

| Decision | Choice | Slice |
|---|---|---|
| Dual-backend vs in-place replace | **Dual-backend Protocol** (Mongo + Postgres adapters) | 32 |
| Priority vs Slice 22 | Migration **before** Slice 22; **escape hatch** if 32–36 slip (22 on Protocol, retest after 38) | TRAIL |
| Dimension layout | Single `chunks` table, nullable dim columns + mandatory `embedding_model` filter | 33–34 |
| Client | Raw SQL (`psycopg` pool recommended for sync FastAPI) — no `vecs` | 33 |
| **experiment_id** | **Keep external string `experiment_id`** (API/CLI/dashboard contract); UUID only as internal PK if needed | 33 |
| **Seam split** | `StorageBackend` = CRUD/metadata/cascade/boot-reconciliation; `RetrieverBackend` (or store retrieval methods) = dense/sparse/hybrid only | 32 |
| SPLADE fallback | If non-zeros > 1000: use `tsvector` sparse path for SPLADE sweeps until alternative designed; log in DECISIONS | 35 |

## Module inventory (Mongo → Supabase)

| Module | Responsibility | Migration action |
|---|---|---|
| `server/db/atlas.py` | Mongo connection singleton | Extract to `mongo_store.py`; keep for mongo backend |
| `server/db/mongodb_uri.py` | Cloud vs local URI detection | Keep for mongo path |
| `server/db/indexes.py` | Collection + search-index bootstrap | Mongo adapter only; Postgres indexes in `postgres_store` / schema |
| `server/core/retriever.py` | Dense/sparse/hybrid via Atlas | Postgres impl behind `RetrieverBackend` or store retrieval port |
| `server/core/search_index_plan.py` | Required indexes from config | Generalize output; backend-specific materialization |
| `server/core/search_index_guard.py` | Preflight guard | Postgres introspection in Slice 36 |
| `server/core/atlas_storage.py` | Atlas Admin API quota / dbStats | `postgres_storage.py` via `pg_*` sizes |
| `server/api/experiments_shared.py` | Mongo aggregation helpers | SQL via StorageBackend |
| `server/core/orchestrator.py` | Pipeline I/O | Call store + retriever ports only |
| `server/core/startup_reconciliation.py` | Stale `running` on boot | Port queries via StorageBackend |
| `pyproject.toml` | `pymongo` | Add `psycopg[binary]`; keep pymongo for dual-backend |

## Slice map

| Slice | Deliverable |
|---|---|
| 32 | Storage Protocol + Mongo adapter extract; Retriever port defined |
| 33 | Supabase/Postgres schema, pool, CRUD, minimal local Docker smoke |
| 34 | Dense retrieval (pgvector HNSW) + `embedding_model` filter |
| 35 | Sparse (`tsvector`) + hybrid (RRF) + equivalence gate vs Mongo |
| 36 | Index preflight, db-stats, `indexes` CLI, storage-mode indicator |
| 37 | Full local/cloud parity (`start-services.sh`), Supabase pooler/TLS docs |
| 38 | Side-by-side quality artifact, ADR-004, default-backend cutover |

## Cutover decision gates (Slice 38 — required before default flip)

Flip documented default to `STORAGE_BACKEND=postgres` only when **all** pass on the same persona query-set and corpus:

| Gate | Metric | Pass threshold |
|---|---|---|
| Latency | Postgres p99 vs Mongo p99 on ADR-003 baseline sweep (36×1000×1024) | Postgres ≤ **2×** Mongo p99 |
| Hybrid quality | Rank drift on hybrid retrieval vs Mongo | ≤ **5%** top-3 reordering (or ≥80% top-3 overlap — same bar as Slice 35) |
| Equivalence | Dense/sparse/hybrid rank overlap | ≥ **80%** top-3 overlap OR explicit CONDITIONAL with trade-offs in comparison artifact |

### Rollback playbook

- **Trigger:** Any cutover gate fails, or production incident on Postgres path with recovery lead time **> 30 minutes**
- **Action:** Set `STORAGE_BACKEND=mongo`, restart server, verify smoke sweep on Mongo adapter
- **Docs:** Record incident + rollback in `gate-evidence/slice-38-quality-comparison.md` and ADR-004

## Acceptance criteria (PRD §9)

- [ ] All endpoints in `api/experiments.py`, `api/runs.py`, `api/sweep.py` work with `STORAGE_BACKEND=postgres` — no client-facing behavior change
- [ ] Dense, sparse, hybrid return results on a real sweep; hybrid uses RRF fusion
- [ ] `embedding_model` filtering enforced in every vector query path (unit-tested)
- [ ] Index preflight rejects sweeps with missing indexes (HTTP 422 parity)
- [ ] Dashboard db-stats panels render non-error data on Postgres backend
- [ ] Cascade delete removes all rows for a deleted experiment
- [ ] Boot reconciliation marks orphaned in-flight runs interrupted/partial
- [ ] ADR-004 authored; ADR-003 superseded
- [ ] Side-by-side comparison documented in `gate-evidence/slice-38-quality-comparison.md` before default flip
- [ ] Cutover gates (latency, hybrid drift, equivalence) measured and PASS per table above
- [ ] Rollback playbook smoke-tested (`STORAGE_BACKEND=mongo` recovery)
- [ ] **CI:** Postgres integration/regression job runs on every PR touching `server/db/*` or storage/retriever paths (mandatory before merging Slices 33–37)

## Risks (verify during slices)

- Hybrid scoring drift vs Lucene BM25 — **equivalence gate in Slice 35/38**
- SPLADE-v3 `sparsevec` ≤1000 non-zeros — **fallback to tsvector path if exceeded**
- Supabase free-tier auto-pause — budget Pro tier for warm demos; document in Slice 37
- Admin/quota API parity — `pg_database_size()` / `pg_total_relation_size()` first
- Latency vs ADR-003 36×1000×1024 baseline — **cutover gate: ≤2× Mongo p99**
- Cost vs Atlas — M0 free vs Supabase Pro (~$25/mo); document in ADR-004 rationale
- Slice 28 export — must use `analyze_results()` / StorageBackend, not raw Mongo queries

## CI / dual-backend (mandatory)

| When | Requirement |
|---|---|
| **Before Slice 32 merge** | Cutover gates + rollback playbook documented in PRD (this section) |
| **Before Slices 33–37 merge** | CI job with Postgres/pgvector service runs storage + CRUD smoke (`STORAGE_BACKEND=postgres`) |
| **Slice 33** | Add minimal `docker compose --profile local-postgres` smoke step to CI or `quality-gates.sh --postgres` |
| **Slice 38** | Dual-backend regression green on both `mongo` and `postgres` before cutover |

Without Postgres CI from Slice 33 onward, Postgres code paths will bitrot before Slice 38 cutover.

## References

- [ADR-003](../adr/ADR-003-mongodb-atlas-vector-store.md) (superseded by ADR-004 in Slice 38)
- [Supabase hybrid search](https://supabase.com/docs/guides/ai/hybrid-search)
- [Supabase connection pooling](https://supabase.com/docs/guides/database/connecting-to-postgres)

## Reviews

| Date | Reviewer | Verdict | Notes |
|---|---|---|---|
| 2026-07-09 | nw-solution-architect-reviewer | Conditionally approved → iter 2 APPROVED | See TRAIL ## Reviews |
| 2026-07-09 | nw-platform-architect-reviewer | Conditionally approved | Cutover gates + mandatory Postgres CI — applied same day |
