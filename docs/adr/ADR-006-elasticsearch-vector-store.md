# ADR-006: Elasticsearch as a vector-only store

**Status**: Accepted
**Date**: 2026-09-27
**Slice**: 51 — Elasticsearch operability, CI, docs, and ADR-006

---

## Context

MongoDB and Postgres already host both run state and chunks. Operators asked for an Elasticsearch option for dense and sparse retrieval without making Elasticsearch the system of record for experiments. ADR-005 stays the DoubleWord embedding decision; this record is only the vector store.

## Decision

Add Elasticsearch as a **vector-only** adapter behind the existing `VectorStore` port.

| Concern | Choice |
|---|---|
| Role | Chunks and search only. Run state stays on MongoDB or Postgres (default local pair: `mongodb-local`) |
| Index | One `rpf-chunks` index, unquantized HNSW (`type: hnsw`, `m=16`, `ef_construction=100`, cosine) |
| Hybrid | Client-side reciprocal rank fusion (`k=60`) because RRF in Elasticsearch is outside the Basic licence |
| Refresh | Refresh before search returns so a sweep does not read a stale interval |
| Local profile | Elasticsearch 9.5, single-node, security off, Basic licence, 1 GB heap, `127.0.0.1:9200` |
| Default store | Unchanged: `STORAGE_BACKEND=mongodb` |

## Consequences

- `GET /api/stores` and `scripts/lib/stores.tsv` are the operator surfaces. A new store is a registry row plus a manifest row.
- Dashboard labels are Index and Host. Quota fields stay empty.
- Dense scores stay on the shared `(1+cos)/2` scale so top-3 overlap across Mongo, Postgres, and Elasticsearch is comparable, not byte-identical.

## Alternatives considered

- **OpenSearch**: same k-NN ideas, a second client and mapping dialect. Rejected for this cycle.
- **Vespa**: strong ranking, a different operations model than the Compose profiles already here. Rejected.
- **pgvector only**: already shipped (ADR-004). Elasticsearch is an additional option, not a replacement.
- **Atlas only**: already shipped (ADR-003, superseded as the sole store by ADR-004). Kept as the default.
- **Server-side Elasticsearch RRF**: the Basic licence does not include it. Client-side fusion matches the licence we run locally.
