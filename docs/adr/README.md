# Architecture Decision Records

Index of ADRs for **rag-params-finder**. ADRs capture hard-to-reverse or cross-cutting decisions;
smaller reversible choices live in the continuous log at [`../plan/DECISIONS.md`](../plan/DECISIONS.md).

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](ADR-001-two-process-architecture.md) | Two-Process Architecture (CLI + Server) | ✅ Accepted | 2026-05-02 |
| [002](ADR-002-voyage-and-local-providers.md) | Dual Embedding/Reranking Providers (Voyage AI + Local) | ✅ Accepted | 2026-05-02 |
| [003](ADR-003-mongodb-atlas-vector-store.md) | MongoDB Atlas as the Vector Store | ⛔ Superseded by [004](ADR-004-postgresql-pgvector-vector-store.md) | 2026-05-02 |
| [004](ADR-004-postgresql-pgvector-vector-store.md) | Dual-Backend Storage — PostgreSQL/pgvector (Supabase) alongside MongoDB Atlas | ✅ Accepted | 2026-07-26 |
| [005](ADR-005-doubleword-embedding-provider.md) | DoubleWord Embedding Provider — Batch-First Architecture | 📋 Proposed | 2026-09-25 |

> **ADR-006** (Local Elasticsearch vector store) is referenced from the split-store track
> ([`../plan/invariants.md`](../plan/invariants.md), DECISIONS #215) but **not yet authored** — it lands with Slice 50/51.

## Status vocabulary

`Accepted` · `Proposed` (decision drafted, not ratified) · `Superseded` (replaced by a later ADR; kept for history) · `Deprecated`.

## ADR format

Each record follows: **Context** → **Decision** → **Consequences** → **Alternatives considered**, with a
`Status` / `Date` / `Slice` header. A superseding ADR names what it replaces (`Supersedes:`); the superseded
one links forward (`Superseded by:`). See any existing ADR for the shape.
