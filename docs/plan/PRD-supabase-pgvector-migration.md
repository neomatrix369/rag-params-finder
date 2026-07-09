# PRD: Migrate Vector/Data Store to Supabase (pgvector) — with Dual-Backend Abstraction

| Field | Value |
|---|---|
| Repo | rag-params-finder |
| Current backend | MongoDB Atlas Vector Search ([ADR-003](../adr/ADR-003-mongodb-atlas-vector-store.md), Accepted) |
| Target backend | Supabase / PostgreSQL + `pgvector` (alongside Mongo via storage Protocol) |
| Status | Approved — team owns integration |
| Source | Vendor due-diligence 2026-07-09; plan integration 2026-07-09 |
| Document type | Implementation PRD |

> Full acceptance criteria and module inventory live in the chat-sourced PRD (2026-07-09). This file is the plan-local SSOT pointer; slices 32–38 implement it.

## Goal

Replace MongoDB Atlas as the *primary* storage backend with Supabase (PostgreSQL + pgvector), **via a dual-backend storage abstraction** so Mongo remains available for rollback and side-by-side retrieval-quality comparison until cutover gates pass.

## Non-goals

- Changing embedding providers (`embedder_factory.py`)
- Frontend UX redesign beyond API shape needs
- Byte-identical retrieval scores vs Atlas

## Open decision (resolved in plan)

| Decision | Choice | Slice |
|---|---|---|
| Dual-backend vs in-place replace | **Dual-backend Protocol** (Mongo + Postgres adapters) | 32 |
| Priority vs Slice 22 | Migration **before** Slice 22 | TRAIL execution order |
| Dimension layout | Single `chunks` table, nullable dim columns + mandatory `embedding_model` filter | 33–34 |
| Client | Raw SQL (`asyncpg` or `psycopg`) end-to-end — no `vecs` | 33 |

## Slice map

| Slice | Deliverable |
|---|---|
| 32 | Storage Protocol + Mongo adapter extract |
| 33 | Postgres schema, pool, metadata/chunks CRUD, cascade delete |
| 34 | Dense retrieval (pgvector HNSW) + model filter invariant |
| 35 | Sparse (`tsvector`) + hybrid (RRF) |
| 36 | Index preflight, db-stats, `indexes` CLI for Postgres |
| 37 | Local Docker Postgres + hosted Supabase parity, boot reconciliation |
| 38 | Side-by-side quality gate, ADR-004, default-backend cutover docs |

## Risks (verify during slices)

- Hybrid scoring drift vs Lucene BM25
- SPLADE-v3 `sparsevec` non-zero ceiling (≤1000)
- Supabase free-tier auto-pause
- Admin/quota API parity (`pg_*` size first)
- Latency vs ADR-003 36×1000×1024 baseline

## References

- [ADR-003](../adr/ADR-003-mongodb-atlas-vector-store.md) (to be superseded by ADR-004 in Slice 38)
- [Supabase hybrid search](https://supabase.com/docs/guides/ai/hybrid-search)
- Graphiti: `rag-params-finder - Supabase migration decision - 2026-07-09`
