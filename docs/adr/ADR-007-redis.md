# ADR-007: Redis (or Valkey) as a vector-only store

**Status**: Accepted
**Date**: 2026-09-30
**Slice**: 53 — Redis vector-store adapter (Accepted); originally Proposed in Slice 52
**Depends on**: ADR-004 (dual backend), ADR-006 (Elasticsearch as third option), Slice 49A/49B (port + registry)

---

## Context

MongoDB and Postgres already host both run state and chunks. Elasticsearch is a vector-only option (ADR-006, Slice 51). Operators have requested a **Redis** option for dense and sparse retrieval with low operational overhead and strong ecosystem adoption.

Slice 52 evaluated Redis 8.0 (with integrated Query Engine) and Valkey (Linux Foundation fork with valkey-search module). Both are self-hosted, $0, and pass the free gate. Redis 8 has higher adoption (63.8k GitHub stars vs Valkey's 3.2k) and mature ecosystem. Valkey is a technically acceptable open-source alternative.

This record formalizes the decision to support Redis as a third vector-only store, following the pattern established by Elasticsearch (ADR-006).

---

## Decision

Add **Redis 8.0 (or Valkey + valkey-search)** as a **vector-only** adapter behind the existing `VectorStore` port.

> **Summary**: Redis is vector-only (chunks and search only). Run state always remains on the configured storage backend (MongoDB, Postgres, or SQLite). No new API endpoints, CLI commands, or dashboard UI components are introduced — only one `DatabaseProvider` config token, one `VectorStore` adapter module, and Docker infra.

| Concern | Choice |
|---|---|
| **Role** | Chunks and search only. Run state stays on MongoDB, Postgres, or SQLite (default: `sqlite`, ADR-008) |
| **Primary implementation** | Redis 8.0 with integrated Query Engine (`FT.CREATE` / `FT.SEARCH` / `FT.HYBRID` commands) |
| **Alternative** | Valkey (Linux Foundation fork, 2024) + valkey-search module — same API, community-maintained |
| **Index schema** | One HASH-based index (`rpf:chunks`) with per-dimension vector fields (`embedding_384` HNSW COSINE, `embedding_1024` HNSW COSINE), TAG filters (`experiment_id`, `run_id`, `embedding_model`), TEXT field for BM25 sparse search |
| **Vector isolation** | Documents carrying only one vector field (e.g., model M1 with 384-dim only) are accepted; filtered KNN on each dimension returns only matching docs (verified in PoC) |
| **Hybrid search** | Client-side reciprocal rank fusion (RRF, `k=60`) over separate dense + sparse queries (D3). `FT.HYBRID` was verified in PoC but the adapter uses client-side RRF for cross-store consistency |
| **Score conversion** | Redis COSINE distance `d` converts to `score = 1 − d/2`, equivalent to `(1+cos)/2` on [-1, 1] scale (verified within 1e-6 tolerance) |
| **Persistence** | AOF (Append-Only File) recommended for production (safe writes); RDB (snapshot) optional. Preflight warns if AOF is off |
| **Memory policy** | `noeviction` (safest; rejects writes when memory limit hit) or `volatile-lru` (cache eviction; risky if vector TTLs misconfigured). Slice 53 preflight enforces `noeviction` or flags `volatile-lru` with warning |
| **TTL guard** | Vector keys must never expire (TTL -1). Slice 53 mutation-guards `EXPIRE` on vector keys to prevent silent eviction under `volatile-lru` |
| **Local profile** | Redis 8.0, single-node, no auth (local), `127.0.0.1:6379`, 256 MB memory limit (docker-compose) |
| **Managed profile** | Redis Cloud (managed by Redis Inc.) or self-hosted cloud Redis; auth + TLS enforced (`rediss://`). Free tier 40 MB smoke-only (impractical for production sweeps) |
| **Default store** | **Unchanged**: `STORAGE_BACKEND=sqlite` (ADR-008). Redis is opt-in via `REDIS_URL` + `VECTOR_STORE_BACKEND=redis` or `./start-services.sh --redis-local` |
| **Client library** | `redis-py` (official, 8.2M downloads/week, mature) preferred over RedisVL (niche) or langchain-redis |
| **Licensing** | Redis 8: tri-licensed RSALv2 / SSPLv1 / AGPLv3 — permissive for self-hosted use. Valkey: BSD-3-Clause — fully open source (Linux Foundation) |

---

## Consequences

### Positive

- Operators can run full RAG parameter sweeps on self-hosted **Redis** with zero cost and minimal operational overhead compared to managed Elasticsearch or Postgres.
- Redis ecosystem is mature and widely deployed (cache, sessions, job queues); many operators already know Redis.
- Both Redis 8 and Valkey+valkey-search are open-source; no vendor lock-in for self-hosted deployments.
- Per-dimension vector field isolation enables mixed-provider experiments (e.g., embedding model 1 at 384-dim, model 2 at 1024-dim) on a single index without separate collections.

### Neutral / Operational

- **Code default is `sqlite` (ADR-008)**: `server/settings.py` defaults to `sqlite` for run state. Redis is opt-in via env vars or `--redis-local` flag. No planned flip of default.
- **Sizing burden**: Unlike Elasticsearch (which fixes JVM heap once), Redis holds every vector in RAM. Operator must calculate `maxmemory` based on planned sweep size. Slice 52 PoC measured ~2.1 KB per 1024-dim vector in HNSW; typical sweep (36k vectors) needs ~95 MB + overhead.
- **Managed tier risk**: Redis Cloud free tier (40 MB) is severely limited — cannot host production sweeps. Recommendation: use self-hosted or paid managed tier.
- **Eviction policy learning curve**: `volatile-lru` requires careful TTL management; naive configuration evicts vector keys silently. Slice 53 guards against this.

### Negative / Follow-ups

- Valkey adoption is nascent (2024 fork); production-scale experience unknown.
- Redis module architecture (Valkey + separate valkey-search) adds maintenance split vs Redis 8's integrated Query Engine.
- Cluster mode (multi-node Redis) not evaluated in Slice 52; single-node sufficient for this tool but may limit scale if needed later.

---

## Alternatives Considered

- **Keep Mongo-only**: Rejected — limits operator choice; Postgres (ADR-004) and Elasticsearch (ADR-006) already established multi-store pattern.
- **Valkey-only**: Rejected — Redis 8 has higher adoption and maturity; Valkey is acceptable alternative if adoption risk is acceptable to operator.
- **OpenSearch**: Rejected for this cycle (same ideas as Elasticsearch, different client, operator already familiar with Elasticsearch from ADR-006).
- **Cluster mode or Redis Sentinel**: Rejected — single-node sufficient; scaling to multi-node is a future concern.
- **Redis Stack (deprecated)**: Rejected — Redis Stack product is discontinued; Redis 8.0 (Query Engine integrated) supersedes it.

---

## References

- **Official docs**: [redis.io/docs/latest/](https://redis.io/docs/latest/) — Redis 8.0 release (2025), Query Engine integrated
- **Valkey**: [valkey.io](https://valkey.io/) — Linux Foundation fork (2024), open-source alternative
- **valkey-search**: [github.com/valkey-io/valkey-search](https://github.com/valkey-io/valkey-search) — FT.* API compatibility module
- **Client**: [redis-py](https://redis.readthedocs.io/en/stable/) — official Python client (8.2M PyPI downloads/week)
- **Research**: REDIS-EVALUATION.md (Slice 52 report), STORE-E2E-WALKTHROUGH.md §2–§3 (15-stage journey)
- **Prior ADRs**: [ADR-004](ADR-004-postgresql-pgvector-vector-store.md) (Postgres dual backend), [ADR-006](ADR-006-elasticsearch-vector-store.md) (Elasticsearch vector-only)

---

## Gate Status

**Accepted** (2026-09-30). Owner decision recorded in DECISIONS #272 (GO — Redis 8 + redis-py) and #273 (option (a) — one shared volatile-lru instance). Slice 53 implementation complete and on branch `slice/53-redis-vector-store-adapter`.

---

## Appendix: Slice 52 PoC Summary

### Compatibility verified (Redis 8.0 + Valkey 8.0)

| Scenario | Redis 8.0.1 | Valkey 8.0 | Verdict |
|----------|-------------|-----------|---------|
| FT.CREATE with per-dimension fields | ✅ | ✅ | Both pass |
| Mixed-dimension isolation (384-dim + 1024-dim docs on one index) | ✅ | ✅ | Isolation works; selective filter doesn't error |
| Filtered KNN (by experiment_id, embedding_model, run_id) | ✅ | ✅ | Both pass |
| BM25 text search | ✅ | ✅ | Both pass |
| FT.HYBRID (native hybrid search) | ✅ | ✅ | Both pass |
| Score conversion: `1 − d/2` = `(1+cos)/2` | ✅ | ✅ | Verified within 1e-6 tolerance |
| Memory overhead (HNSW m=6) | ~2.1 KB/vector | ~2.1 KB/vector | Consistent across both |
| AOF persistence | ✅ | ✅ | Both supported |
| Auth / TLS | ✅ | ✅ | Both pass |
| TTL mutation risk (requires guard) | ⚠ | ⚠ | Slice 53 blocker: prevent EXPIRE on vectors |

### Memory measurements

| Vectors | Memory | Bytes/vector | Note |
|---------|--------|--------------|------|
| 1k × 1024-dim (m=6) | 2.3 MB | ~2,300 | Sampled after FT.CREATE + HSET loop |
| 10k × 1024-dim | 23.1 MB | ~2,310 | Linear scaling confirmed |
| Extrapolated 36k (typical sweep) | ~83 MB | ~2,305 | + index overhead, metadata → ~95 MB minimum; local container capped at **256 MB** (ADR-007 remediation) |

### Licensing & IP

| Product | License | Self-host safe? | Notes |
|---------|---------|-----------------|-------|
| Redis 8.0 | RSALv2 / SSPLv1 / AGPLv3 (tri-licensed) | ✅ Yes | Permissive for self-hosted use |
| Valkey | BSD-3-Clause | ✅ Yes | Fully open source (Linux Foundation) |
| Redis Cloud | Redis Inc. Terms of Service | ⚠ Limited | Free tier 40 MB smoke-only; managed service |

---

**Proposed by**: Slice 52 research (2026-09-30)
**Next step**: Owner decision on Branch A (Slice 53 GO/NO-GO)
