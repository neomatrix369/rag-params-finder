# ADR-004: Dual-Backend Storage — PostgreSQL/pgvector (Supabase) alongside MongoDB Atlas

**Status**: Accepted
**Date**: 2026-07-26
**Slice**: 38 — Cutover + ADR-004
**Supersedes**: [ADR-003](ADR-003-mongodb-atlas-vector-store.md) (MongoDB Atlas as the *sole* vector store)

---

## Context

ADR-003 chose MongoDB Atlas as the single store for embeddings and experiment documents. That choice served the hackathon skateboard (unified free-tier Atlas Vector Search), but operators now need:

1. A **Postgres/pgvector** path (local Docker or hosted **Supabase**) for SQL-native storage, HNSW indexes in-schema, and environments where Atlas is unavailable or costly at scale.
2. Continued **MongoDB** support for rollback, A/B comparison, and existing Atlas workflows.
3. A stable **port boundary** so sweeps, CLI, and the dashboard do not fork by engine.

Slices 32–37 + 43 delivered `StorageBackend` / `RetrieverBackend`, Mongo + Postgres adapters, four-mode `storage_mode`, and operator switching (`--mongodb-*` / `--postgres-*`). Slice 38 records the architectural decision: both engines are **first-class and independent** (DECISIONS #129). The **code default** stays `mongodb` permanently (DECISIONS #130 — no default flip); operators select Postgres explicitly. Neither engine is a fail-safe for the other.

---

## Decision

Support **PostgreSQL + pgvector** (including Supabase-hosted Postgres) as a **first-class storage and retrieval backend**, **in addition to** MongoDB Atlas / Atlas Local.

| Concern | Choice |
|---|---|
| Runtime select | `STORAGE_BACKEND=mongodb` \| `postgres` (legacy alias `mongo` → `mongodb`) |
| Connection | Mongo: `MONGODB_URI`. Postgres: canonical `DATABASE_URL`; optional `SUPABASE_URI` alias when unset |
| Modes | `mongodb-local` \| `mongodb-cloud` \| `postgres-local` \| `postgres-cloud` via `./start-services.sh --{mongodb\|postgres}-{local\|cloud}` |
| Configs | Mirrored stems under `configs/mongodb/` and `configs/supabase/` (`database_provider` is labeling metadata; engine must match server or HTTP 422) |
| Code default | **`mongodb`** permanently (#130) — Postgres via `STORAGE_BACKEND=postgres` / `--postgres-*` |
| Hosted Postgres | Prefer **`postgres-cloud`** (Supabase) when the operator chooses hosted Postgres (Slice 43 residuals for quality evidence); use a **Pro / non-pausing** tier for warm demos — free-tier auto-pause is a known risk |

Mongo is **not** deleted. Dual-backend is intentional through cutover and beyond until a later cleanup slice.

---

## Rationale

| Concern | Why Postgres/Supabase *and* Mongo |
|---|---|
| Operator choice | Laptop/`postgres-local` (pgvector on :5433) and hosted Supabase without requiring an Atlas account |
| Schema-as-code | Indexes and extensions live in `server/db/postgres/schema.sql`; preflight is catalog introspection (HTTP 422), not Atlas UI quota alone |
| Cost / ceiling | Atlas M0 512 MB and shared CPU vs Supabase project limits — different trade-offs; operators pick per environment |
| Equivalence, not identity | Dense scores are Atlas-scaled on Postgres; sparse/hybrid may differ (Lucene BM25 vs `ts_rank`) — compare with overlap gates, not byte-identical ranks (DECISIONS #93 / #114 / #115). On Postgres, **pgvector is dense (and hybrid’s dense leg) only**; sparse is `tsvector` FTS. |
| Rollback | Two-command **engine switch** to Mongo (`--mongodb-local\|cloud` + matching `configs/mongodb/…`) if the operator chooses — not automatic failover; backends are independent (#129) |
| Port freeze | Post-cutover work must not change `StorageBackend` / `RetrieverBackend` semantics (Slice **32C** freeze) — new engines adapt to the ports |

---

## Consequences

### Positive

- Operators can run the full RAG parameter sweep on **either** engine with the same CLI and dashboard.
- Local pgvector and Atlas Local are both pinable, reproducible Compose paths (`pgvector/pgvector:0.8.5-pg16`, `mongodb/mongodb-atlas-local:8.3.3`).
- Hosted Supabase is a documented Path B (`postgres-cloud`) with Session-mode pooler guidance.

### Neutral / operational

- **Code default is `mongodb` (#130)**: `server/settings.py`, `scripts/lib/storage_mode.sh`, and `docker-compose.yml` default to `mongodb`. There is **no** planned flip of that default. Local comparison ([`slice-38-quality-comparison.md`](../plan/gate-evidence/slice-38-quality-comparison.md), **VERIFIED** 2026-07-26) is operator A/B evidence under independent backends (#129), not a cutover tripwire.
- **Cost note**: Atlas M0 remains free but storage/CPU constrained; Supabase free tier can pause — plan hosted demos accordingly (Pro-tier detail tracked as Slice 43 residual).
- **Monitoring**: Prefer `/healthz` (`storage_mode`, backend `ok`) and QUERYING-phase failure counts; remediate Supabase pause via project wake + reconnect.
- **Engine switch (ops)**: If the Postgres path is unsuitable for an incident (e.g. recovery lead time **> 30 minutes**), operators may switch to Mongo with the two-command recipe; record in gate-evidence / ops notes. This is a deliberate backend change, not automatic fail-over.
- **32C port-semantics freeze**: Do not widen or break Protocol method contracts to “fix” one adapter; fix adapters behind the ports.

### Negative / follow-ups

- Sparse/hybrid rank drift may yield CONDITIONAL equivalence — not a reason to drop either backend.
- Formal gate-closure of tracker rows 32 / 32B / 32C / 33 remains parallel debt (not required to endorse dual-backend).
- Hosted production-claim quality matrix is **not** required to accept this ADR; it lives on Slice 43 residuals (DECISIONS #125 / #126).

---

## Alternatives Considered

- **Keep Mongo-only (ADR-003 forever)**: Rejected — blocks Supabase/pgvector operators and the migration PRD.
- **Hard cutover delete Mongo**: Rejected for this cycle — need rollback and side-by-side comparison (Won't until a later cleanup slice).
- **Postgres-only new fork of the product**: Rejected — duplicates CLI/dashboard; ports already isolate engines.
- **Flip code default to `postgres`**: Rejected permanently (DECISIONS #130 Won't) — dual-backend is operator select via flags/env; default stays `mongodb`.

---

## References

- PRD: [`docs/plan/PRD-supabase-pgvector-migration.md`](../plan/PRD-supabase-pgvector-migration.md)
- Slice: [`docs/plan/slices/SLICE-38-CUTOVER-ADR-004.md`](../plan/slices/SLICE-38-CUTOVER-ADR-004.md)
- Operator: [`docs/user-guide/postgres-setup.md`](../user-guide/postgres-setup.md), [`docs/user-guide/mongodb-setup.md`](../user-guide/mongodb-setup.md)
- Prior ADR: [`ADR-003`](ADR-003-mongodb-atlas-vector-store.md)
