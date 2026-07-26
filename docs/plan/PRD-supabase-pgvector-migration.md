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
| **Dual-backend** | `STORAGE_BACKEND=mongodb` (legacy alias `mongo`) or `postgres`; Mongo adapter retained through cutover for rollback and A/B comparison. |

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
| `server/core/atlas_storage.py` | Atlas Admin API quota / dbStats | Extend `postgres_stats.py` via `pg_*` sizes (Slice 36) |
| `server/api/experiments_shared.py` | Mongo aggregation helpers | SQL via StorageBackend |
| `server/core/orchestrator.py` | Pipeline I/O | Call store + retriever ports only |
| `server/core/startup_reconciliation.py` | Stale `running` on boot | Port queries via StorageBackend |
| `pyproject.toml` | `pymongo` | Add `psycopg[binary]`; keep pymongo for dual-backend |

## Slice map

| Slice | Deliverable |
|---|---|
| 32 | Storage Protocol + Mongo adapter extract; Retriever port defined |
| 33 | Postgres schema, pool, CRUD, **local** compose (`--postgres` → later `--postgres-local`); Path A in `postgres-setup.md` |
| 34 | Dense retrieval (pgvector HNSW) + `embedding_model` filter; backend-aware `/healthz` (`storage_backend` only) |
| 35 | Sparse (`tsvector`) + hybrid (RRF) + equivalence gate vs Mongo; works for `postgres-local` and `postgres-cloud` |
| 36 | Index introspection preflight, db-stats extend, `indexes` CLI, four-value `storage_mode` (`mongodb\|postgres` × `local\|cloud`) |
| 37 | Flag vocabulary, hosted `ensure_env`, **low-friction two-command switching**, config↔server 422 gate, lifecycle, Path B docs |
| 38 | Side-by-side quality artifact, ADR-004 dual-backend; code default stays `mongodb` (#130 Won't flip) |

## Operator contract (Mongo ↔ Postgres mirror)

| Concern | Mongo | Postgres |
|---|---|---|
| Backend switch | `STORAGE_BACKEND=mongodb` (alias: `mongo`) | `STORAGE_BACKEND=postgres` |
| Local flag | `--mongodb-local` | `--postgres-local` |
| Cloud flag | `--mongodb-cloud` (or bare + `.env`) | `--postgres-cloud` — **must not require `MONGODB_URI`** |
| Detection | `is_atlas_uri()` | `is_supabase_uri()` |
| Mode on healthz/stats | `mongodb-local` \| `mongodb-cloud` | `postgres-local` \| `postgres-cloud` |
| YAML `database_provider` | `mongodb` | `postgres` (`supabase` normalizes to `postgres`) |
| Config vs server | Must match engine; mismatch → 422 with restart flag | Same |
| User docs | `mongodb-setup.md` Path A/B | `postgres-setup.md` Path A/B — **no** `supabase-setup.md` |
| Local lifecycle | `start-services.sh mongodb …` | `start-services.sh postgres …` (Slice 37) |

### Low-friction switching (Must — Slice 37)

Happy path is always two commands — flag then matching example config:

```bash
./start-services.sh --postgres-cloud
rag-params-finder run --config configs/supabase/example-local.yaml
```

- Flag exports/resolves `STORAGE_BACKEND` + compose profile; prints `storage_mode` + suggested config.
- YAML never flips the process backend; it declares engine intent and must match.
- Same `database_provider: postgres` YAML works for both `postgres-local` and `postgres-cloud`.
- Wrong pairing fails **before** persistence with remediation naming the flag and example config.

Local compose landed in Slice 33 so dense/sparse work could proceed; Slice 37 owns hosted DX + flag vocabulary + consistency gate that make switching expressible and safe.

## Documentation matrix

User guides, dev docs, and agent docs are **gated per slice** — same commit as behaviour (see `documentation-best-practices.mdc`). Full 14-row audit from `plan-generator` applies at slice close; this matrix names **which files** and **which slice owns them**.

**Every slice (32–38):** update `docs/plan/slices/PROGRESS.md` (status + decision log). Run `/sync-docs` at **37** and **38** (user-facing doc footprint).

| Doc | Audience | Slice | Action / gate |
|---|---|---|---|
| `docs/plan/slices/PROGRESS.md` | Maintainer | **32–38** | Slice status 🔨→✅; decision log row if non-obvious |
| `CLAUDE.md` Key Files | Agent | **32**, **36**, **37**, **38** | Ports (32); backend-aware preflight + `health_check` / mode helpers (36); flag vocabulary + `STORAGE_BACKEND` / `DATABASE_URL` (37); dual-backend + permanent `mongodb` default (#130) (38) |
| `docs/contributor-guide/architecture.md` | Dev | **32**, **34**, **36**, **38** | Storage/Retriever ports (32); Postgres dense retrieval (34); Postgres preflight + `storage_mode` capability rows (36); dual-backend diagram (38) |
| `docs/contributor-guide/extending.md` | Dev | **32** | How to add a `StorageBackend` / `RetrieverBackend` adapter |
| `.env.example` | Dev | **33**, **37** | `STORAGE_BACKEND`, `DATABASE_URL` (33); `RAG_{MONGODB,POSTGRES}_{LOCAL,CLOUD}` (37) |
| `docs/plan/PRD-supabase-pgvector-migration.md` | Plan | **33** | Glossary + env vars aligned with implementation |
| `docs/user-guide/configuration.md` | User | **33**, **35**, **36** | New env vars (33); sparse/hybrid retrieval notes (35); storage-mode field (36) |
| `docs/contributor-guide/development.md` | Dev | **36**, **37** | Test-tier rows for preflight + `storage_mode` suites (36); `start-services.sh --postgres-local` / `--postgres-cloud`, docker profile, postgres lifecycle (37) |
| `docs/user-guide/postgres-setup.md` | User | **33**, **36**, **37** | Path A local (33); index preflight + `storage_mode` in operational checks (36); Path B hosted pooler/TLS/pause (37) — SSOT; **do not** create `supabase-setup.md` |
| `docs/user-guide/getting-started.md` | User | **37** | Postgres/Supabase path (or branch: “Mongo vs Postgres” with links) |
| `docs/user-guide/troubleshooting.md` | User | **36**, **37** | Postgres index preflight 422 + catalog remediation (36); Supabase connection, pooler, paused project (37) |
| `docs/user-guide/cli-reference.md` | User | **36** | `indexes` CLI behaviour on both backends |
| `README.md` | User | **37**, **38** | Four-flag switching table; default backend note at cutover (38) |
| `docs/README.md` | All | **33**, **37** | Persona row + user-guide table entry for `postgres-setup.md` |
| `docs/user-guide/mongodb-setup.md` | User | **37**, **38** | Flag rename to `--mongodb-local` (37); cross-link rollback vs default (38) |
| `configs/supabase/example-local.yaml` | User | **33** | Mirrored local/pgvector example (dense today; sparse/hybrid Slice 35) |
| `configs/supabase/` (voyage, sie, parallel, bayesian twins) | User | **33+** | Parity set with `configs/mongodb/` stems; hosted Supabase uses same YAMLs + `DATABASE_URL` (Slice **37**) |
| `docs/adr/ADR-004-postgresql-pgvector-vector-store.md` | All | **38** | **Create** — supersedes ADR-003; cost + monitoring rationale |
| `docs/adr/ADR-003-mongodb-atlas-vector-store.md` | All | **38** | Status → Superseded by ADR-004 |
| `docs/plan/gate-evidence/slice-38-quality-comparison.md` | Maintainer | **38** | Cutover quality + latency + rollback evidence |
| `CHANGELOG.md` | User | **37**, **38** | Flag vocabulary (37); default backend (38) |
| `QUICKSTART.md` | User | **37** | One-liner for `--postgres-local` / link to `postgres-setup.md` |

**N/A rule:** If a matrix row does not apply to a slice, note `N/A — <reason>` in the slice After-Checks before marking ✅.

## Dual-backend comparison gates (Slice 38 — operator evidence; no code-default flip)

**Won't (#130):** do **not** flip the documented/code default to `STORAGE_BACKEND=postgres`. Default stays `mongodb`; operators select Postgres explicitly. Record comparison on the same persona query-set and corpus:

**Baseline snapshot (record in `gate-evidence/slice-38-quality-comparison.md`):**

- Corpus: configs under `configs/` used for ADR-003 baseline sweep (e.g. `example-mongodb-local.yaml` corpus paths)
- Query set: persona JSON referenced by baseline config `queries_file`
- Snapshot date: date of first passing comparison run

| Gate | Metric | Pass threshold |
|---|---|---|
| Latency | Postgres p99 vs Mongo p99 on ADR-003 baseline sweep (36×1000×1024) | Postgres ≤ **2×** Mongo p99 |
| Hybrid quality | Rank drift on hybrid retrieval vs Mongo | ≤ **5%** top-3 reordering (or ≥80% top-3 overlap — same bar as Slice 35) |
| Equivalence | Dense/sparse/hybrid rank overlap | ≥ **80%** top-3 overlap OR explicit CONDITIONAL with trade-offs in comparison artifact |

### Rollback playbook

- **Trigger:** Any cutover gate fails, or production incident on Postgres path with recovery lead time **> 30 minutes**
- **Action:** `./start-services.sh --mongodb-local` (or `--mongodb-cloud`) + matching `configs/mongodb/…`, or set `STORAGE_BACKEND=mongodb` + `MONGODB_URI`, restart, verify smoke sweep on Mongo adapter
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
- [x] Side-by-side comparison documented in `gate-evidence/slice-38-quality-comparison.md` (no default flip — #130)
- [x] Comparison gates (latency, hybrid drift, equivalence) measured per table above (latency PASS; overlap informational #129)
- [ ] Rollback playbook smoke-tested (`STORAGE_BACKEND=mongodb` / `--mongodb-*` recovery)
- [ ] **Switching:** two-command Mongo↔Postgres recipes documented and smoke-tested; config/backend mismatch returns 422 before writes
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
| **Slice 33** | CI `postgres-integration` job + local pgvector profile (done); no `quality-gates.sh --postgres` flag required |
| **Slice 38** | Dual-backend regression green on both `mongodb` and `postgres` before cutover |

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
