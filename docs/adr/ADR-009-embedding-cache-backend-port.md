# ADR-009: Embedding Cache Backend Port — SQLite Default, Redis Opt-In

**Status**: Accepted
**Date**: 2026-10-01
**Slice**: 54 — Embedding Cache Backend Port (Redis)

---

## Context

Parameter sweeps re-embed identical text across many configuration combinations. Embedding is expensive:
- **Voyage AI**: rate-limited (RPM/TPM), cost per call ($0.06–$0.12 per 1M tokens)
- **SIE gateway**: network round-trip per batch
- **Local models**: CPU/GPU-bound even when cached
- **DoubleWord**: batch-only, async polling overhead

Comparing 36 runs × 3 models × 200 queries × ~100 tokens each = 2.16M embedding operations, many redundant. A single query text appearing across 10 config combinations means re-embedding the same text 10 times.

The solution requires a memoization cache: SHA256 key built from (provider, model, dim, instruction, role, text), deterministic so identical text always hits the same key, decoupled from experiment/run IDs so cache spans multiple experiments.

## Decision

Introduce a `CacheBackend` structural protocol (`server/core/embedding/embedding_cache.py`) with two swappable implementations:

| Aspect | Choice |
|---|---|
| Protocol interface | `CacheBackend`: `get_many(keys) → dict[key → vec]`, `put_many(entries, prompt_tokens=None) → None`, `cached_keys(keys) → frozenset` |
| Cache key | Deterministic SHA256 of JSON `[provider, model, dim, instruction, role, text]` — identical text → identical key across sweeps |
| Default backend | **SQLite WAL** (`EMBEDDING_CACHE_BACKEND=sqlite`): thread-safe, no external service, persists across server restarts, stored at `embedding_cache_path` (default `./data/embedding_cache.db`) |
| Optional backend | **Redis** (`EMBEDDING_CACHE_BACKEND=redis`): fast bulk GET/SET via `MGET`/pipelined `SET`, float32 BLOB format (same encoding as SQLite for compatibility), prefix `rpf:emb:`, configurable TTL (default 7 days) |
| Redis TTL contract | Every cache key carries a TTL so it is eligible for eviction under `volatile-lru` when one Redis instance serves both the vector store and the embedding cache (DECISIONS #273 option a). Vector keys written by the vector store adapter have no TTL (`TTL = -1`), so they are never evicted under that policy — the two key types are distinguishable by TTL alone |
| Factory dispatch | `get_cache_backend()` in `embedding_cache.py`: reads `settings.embedding_cache_backend`, constructs `EmbeddingCache` (SQLite) or `RedisCacheBackend`, returns the singleton `CacheBackend` instance |
| Compat alias | `get_embedding_cache()` → `get_cache_backend()` for backward compatibility if any code path predates the Protocol rename |

## Important: Distinct from ADR-007

**This is NOT the same thing as Redis-as-a-vector-store** (ADR-007). Clarification:

- **ADR-007** (Redis vector store): `VECTOR_STORE_BACKEND=redis` selects Redis for storing document chunks and their embeddings, with vector-search capability (dense/sparse/hybrid retrieval). This is the data source for RAG queries.
- **ADR-009** (Embedding cache): `EMBEDDING_CACHE_BACKEND=redis` selects Redis as a transparent memoization layer for embedding vectors during sweep parameter experimentation. This avoids redundant re-embedding of identical text. The cache is local to a single server process; it does not feed RAG queries directly.

The two settings are orthogonal. A deployment can use:
- `VECTOR_STORE_BACKEND=mongodb` + `EMBEDDING_CACHE_BACKEND=sqlite` (MongoDB for vectors, local SQLite for embedding cache)
- `VECTOR_STORE_BACKEND=redis` + `EMBEDDING_CACHE_BACKEND=sqlite` (Redis for vectors, local SQLite for cache)
- `VECTOR_STORE_BACKEND=redis` + `EMBEDDING_CACHE_BACKEND=redis` (both Redis; DECISIONS #273 option a ensures cache keys are TTL-tagged and vector keys are not, so they are independently evictable)

## Consequences

### Positive

- **Redundancy eliminated**: identical text in a 36-run sweep (10 occurrences, 1 embed) → cache hit, save 9 API calls or model invocations
- **No service dependency (default)**: SQLite cache requires no Docker, no Postgres, no separate Redis — single file, no setup
- **Cost savings**: fewer Voyage API calls → lower billing; fewer DoubleWord batch polls → faster sweeps
- **Speed**: cache lookup is sub-millisecond; avoids waiting for remote embeddings or local model inference
- **Flexible storage**: Redis option for deployments that already run Redis; TTL contract enables cohabitation with vector store without interference
- **Thread-safe**: both SQLite (via Python's `sqlite3` serialization) and Redis (pipelined operations) handle concurrent access from the orchestrator and API reader threads

### Neutral / operational

- **SQLite capacity**: a 1000-chunk document with 10 unique text fragments cached at 1024 float32s per vector = ~40KB per vector. 1000 vectors = ~40MB file, easily manageable. Operators monitoring sweep volume can migrate to `EMBEDDING_CACHE_BACKEND=redis` if SQLite file size becomes a concern.
- **Redis TTL management**: operators must ensure Redis memory is sized for both vector store and cache. A `volatile-lru` eviction policy naturally prioritizes vectors (no TTL) over cache entries (7-day TTL), but if Redis is under extreme memory pressure, cache entries will evict first — correct, but operators should monitor.
- **Migration**: switching cache backends at runtime requires server restart (the singleton factory runs once on startup). No persistent cache data loss — both SQLite and Redis cache are read-through (missing keys simply cause re-embedding).

### Negative / follow-ups

- **Cache coherence not enforced**: if a model's output changes (e.g., provider updates embeddings silently), the cache will still serve stale vectors. Mitigated by cache-key inclusion of provider, model, and dimension — a provider version bump or model name change invalidates old keys. Full cache invalidation would require explicit deletion or TTL expiry.
- **SQLite concurrent writes**: only the server process writes to the cache; concurrent CLI instances cannot write (they submit over HTTP). If the deployment model ever adds multiple server replicas writing to the same cache file, SQLite stops being viable — Postgres or Redis remains the choice for that environment.
- **No explicit pre-warming**: the cache is populated on-demand (first experiment hits embedder, populates cache, second experiment with same text hits cache). A pre-load step for common text fragments was rejected as out-of-scope for Slice 54.

## Alternatives Considered

- **No cache at all**: rejected for cost and latency. Voyage billing + DoubleWord batch overhead justified the memoization.
- **Memcached**: evaluates to same Redis capability but with less flexible eviction — lacks TTL-based distinction between cache entries and vector store entries.
- **Application-level in-memory cache (dict)**: rejected because it does not survive server restarts and offers no multi-process sharing (the CLI and Dashboard both poll the same server, but the server's process memory is private).
- **Database query result caching**: overlapping concern (experiment sweeps repeat queries, so query result caching could also help), but distinct from embedding cache and was left as a follow-up improvement (out-of-scope for Slice 54).
- **Bloom filter for quick misses**: rejected as micro-optimization; the MGET/SELECT cost is already negligible compared to embedding latency.

## References

- Slice: [`docs/plan/slices/08-embedding-providers/SLICE-54-CACHE-BACKEND-PORT-REDIS.md`](../plan/slices/08-embedding-providers/SLICE-54-CACHE-BACKEND-PORT-REDIS.md)
- Code: [`server/core/embedding/embedding_cache.py`](../../server/core/embedding/embedding_cache.py), [`server/core/embedding/embedding_cache_redis.py`](../../server/core/embedding/embedding_cache_redis.py)
- Redis vector store (distinct): [ADR-007](ADR-007-redis.md)
- Shared Redis instance design: DECISIONS #273 option (a)
- Operator guide: [Configuration Reference § Embedding Cache Backend](../user-guide/configuration.md) and [Redis Setup § Embedding Cache](../user-guide/redis-setup.md)
