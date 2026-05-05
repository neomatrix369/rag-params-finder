# ADR-003: MongoDB Atlas as the Vector Store

**Status**: Accepted
**Date**: 2026-05-02
**Slice**: 1 — Skateboard

---

## Context

The pipeline stores text chunks with embeddings and needs to perform approximate nearest-neighbour (ANN) vector search at query time. Dedicated vector databases (Pinecone, Weaviate, Qdrant, Chroma) are purpose-built for this, but the project also needs to store experiment metadata, run status, and query results as structured documents.

---

## Decision

Use **MongoDB Atlas** for all storage — both vector embeddings and structured documents — via Atlas Vector Search.

---

## Rationale

| Concern | Decision advantage |
|---|---|
| Unified storage | Chunks + embeddings, experiment metadata, run status, and results all live in one cluster — no second service to provision, connect, or monitor |
| Free tier | Atlas M0 (free) supports vector search — zero infrastructure cost for development and hackathon judging |
| Production-ready | Atlas Vector Search uses HNSW under the hood; same API works on M0 and M10+ |
| Hybrid search | Atlas supports both vector (dense) and full-text BM25 (sparse) search in the same collection, enabling hybrid retrieval without a second index service |
| Familiar query model | MongoDB aggregation pipeline (`$vectorSearch` stage) is composable; filtering by `embedding_model`, `experiment_id`, `chunk_size` is first-class |

---

## Consequences

- **Manual index creation**: MongoDB Atlas does not support programmatic vector index creation via pymongo. The `vector_index_1024` (Voyage) and `vector_index_384` (local) indexes must be created once in the Atlas UI. See [README — Configure Environment](../../README.md#2-configure-environment).
- **Index build time**: After creation, the index takes ~1–2 minutes to build. Queries return no results until the index is ready.
- **Dimension-specific indexes**: Each embedding dimension (384, 1024) requires its own index. Mixed-dimension queries fail silently or error.
- **M0 storage limit**: 512 MB on the free tier. A typical sweep (36 runs × 1000 chunks × 1024-dim × 4 bytes) uses ~147 MB. Large experiments or many sweeps may exhaust the free tier.
- **Shared CPU on M0**: Free-tier clusters share compute. Vector search latency may be higher during peak Atlas usage.

---

## Alternatives Considered

- **Pinecone**: Purpose-built vector DB with managed indexing (no manual index creation). Rejected because it adds a second external service while MongoDB Atlas already handles structured data.
- **Weaviate / Qdrant**: Strong vector DB options, but require a separate running service (Docker or cloud). Adds operational complexity for local judging.
- **Chroma (local)**: Fully local, no cloud required. Rejected because the project targets MongoDB Atlas as a showcase of Atlas Vector Search capabilities (hackathon context).
- **pgvector (PostgreSQL)**: Good option for production, but requires a Postgres instance. No free hosted tier with vector support as straightforward as Atlas M0.
