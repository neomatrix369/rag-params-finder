# SLICE 54 — Embedding-Cache Backend Port + Redis Cache Adapter (Branch B)

**MoSCoW:** COULD *(proposed. Only if Slice 52 finds a concrete need that SQLite can't meet, e.g. a cache shared across hosts/containers — #225, #227)*
**Target time:** ~3–4 h
**Status:** 📋 PLANNED
**Depends on:** **48A** (`server/core/embedding/embedding_cache.py` on `main`) · **52** (Branch B cache GO). Soft: **53** (reuse the `redis-local` compose profile + `REDIS_URL` conventions; otherwise this slice adds a minimal profile).
**Branch:** `slice/54-cache-backend-port-redis`
**Feature:** Redis as supporting infrastructure — embedding cache only

---

## Context

48A plans a content-addressed embedding cache (`cache_key(text, provider, model, dim, instruction, role)`, `get_many` / `put_many`, SQLite WAL, shared across sweeps). This slice lifts **the storage behind those two calls** into a small `CacheBackend` port. SQLite stays the default and Redis is a second adapter, chosen by `EMBEDDING_CACHE_BACKEND=sqlite|redis`. The cache key, the callers and the semantics don't change.

- **Depends-on outputs:** 48A `embedding_cache.py` API + tests; Slice 52 Branch B verdict (the measured need + combined-deployment stance); Slice 53 compose/URI conventions (if shipped).
- **Invariants pointer:** `docs/plan/invariants.md`. Fail-closed on cache miss for DoubleWord runs (`DoublewordCacheMissError`, 48A). Single uvicorn worker (48A).

## Non-goals

- Wiring the cache into Voyage / local / SIE embedders. That is a separate generalisation (48A non-goal, Rule of 3) and is independent of Redis.
- `JobQueue` or `RateLimiter` ports (Won't, #226 — no second implementation exists; flip trigger lives in Slice 16).
- Semantic / LLM response cache (no LLM calls exist).
- TTL-based invalidation logic (content-addressed keys never go stale; TTL is only an eviction aid).

## Output contract

- **Baseline:** `EMBEDDING_CACHE_BACKEND` unset → SQLite path; 48A cache tests green.
- A `CacheBackend` Protocol with exactly `get_many(keys) -> dict[str, CachedVector]` and `put_many(items) -> None`, typed, in the module that owns the cache.
- The existing 48A cache tests run **parametrised over both backends** and pass unchanged.
- With `EMBEDDING_CACHE_BACKEND=redis`, a second sweep over the same texts makes **zero** provider calls (same observable as 48A's "everything cached skips submission").

## Reuse ledger (reuse-first — don't reinvent the wheel)

| Need | Existing code to reuse/extend | Action |
|---|---|---|
| Cache key | `cache_key(...)` — `server/core/embedding/embedding_cache.py` (48A) | **Reuse** unchanged (the key *is* the contract) |
| Cache API | `get_many` / `put_many` (48A) | **Extract** their signatures into the `CacheBackend` Protocol; the SQLite code becomes the first adapter (moved, not rewritten) |
| Backend selection | Settings normaliser pattern (`normalize_storage_backend`, `server/settings.py`) + factory dispatch pattern (`embedder_factory.get_embedder`) | **Reuse** the pattern: `EMBEDDING_CACHE_BACKEND` + a small lazy dispatch |
| Vector encoding | 48A float32 BLOB encoding | **Reuse** the same bytes as the Redis value (no second encoding) |
| Redis connection / URL / TLS | `server/db/redis/config.py` + `redis_uri.py` (53) | **Reuse** if 53 shipped; otherwise the minimal subset lands here and 53 reuses it |
| Compose profile | `redis-local` (53) | **Reuse**. Cache keys use prefix `rpf:emb:` and never collide with vector keys |
| Tests | 48A cache tests | **Parametrise** over `{sqlite, redis}`, with no second test file per backend |
| **Net-new (only)** | `CacheBackend` Protocol, `RedisCacheBackend` (`MGET` / pipelined `SET`), `EMBEDDING_CACHE_BACKEND` setting, docs rows | Write new |

**Combined deployment (HITL at 52/54 start):** one Redis instance cannot run both `noeviction` (vectors, required by 53 preflight) and `allkeys-lru` (cache). There are two options: (a) one instance with `volatile-lru`, where cache keys carry a TTL and vectors have none, so only cache keys are evictable; (b) two instances/profiles. Slice 52 recommends; the owner decides.

| Criterion | (a) one instance, `volatile-lru` | (b) two instances |
|---|---|---|
| Cost / footprint | One container, one `maxmemory` budget shared | Two containers, two budgets |
| Ops complexity | Lower: one profile, one URL | Higher: two profiles, two URLs, two health checks |
| Failure mode | A vector key that ever gains a TTL becomes evictable; cache pressure can starve vector headroom; a key evicted **between** pre-embed planning and the run reading it raises 48A's `DoublewordCacheMissError` | Isolated: cache eviction can never touch vectors |
| TTL management | Mandatory TTL on every cache key; vector keys must stay TTL `-1` (asserted in 53 and here) | TTL optional for the cache (`allkeys-lru` works) |
| Durability of cache | AOF shared with vectors | Cache instance can run without persistence |

---

## Slice Workflow Bundle

- Slice name: `slice-54-cache-backend-port-redis`
- Branch: `slice/54-cache-backend-port-redis`
- Files (expected): `server/core/embedding/embedding_cache.py` (**edit** — Protocol + SQLite adapter moved in place), `server/core/embedding/embedding_cache_redis.py` (**new**), `server/settings.py` (**edit**), 48A cache tests (**edit** — parametrise), `docs/user-guide/configuration.md` + `redis-setup.md` (**edit** — cache section), `.env.example`, CHANGELOG.
- Exit criteria: both backends pass the same tests; default behaviour byte-identical; combined-deployment stance documented.
- Commit pattern: `refactor(embedding): CacheBackend port (SQLite default)` then `feat(embedding): Redis cache backend`

---

## Spec (GWT)

```gherkin
Feature: The embedding cache can live in SQLite or Redis without changing callers

  Scenario Outline: Both backends honour the same cache contract
    Given EMBEDDING_CACHE_BACKEND=<backend>
    When put_many stores vectors and get_many reads the same keys back
    Then the returned vectors are byte-identical to what was stored
      And unknown keys are absent from the result rather than raising
    Examples:
      | backend |
      | sqlite  |
      | redis   |

  Scenario: Default behaviour is unchanged
    Given EMBEDDING_CACHE_BACKEND is unset
    When a DoubleWord experiment runs
    Then the SQLite cache at settings.embedding_cache_path is used exactly as in 48A

  Scenario: A repeat sweep served from Redis makes no provider calls
    Given EMBEDDING_CACHE_BACKEND=redis and a completed sweep
    When the same config is submitted again
    Then zero embedding batches are submitted

  Scenario: An unreachable Redis cache stops the server from starting
    Given EMBEDDING_CACHE_BACKEND=redis and REDIS_URL unreachable
    When the server starts
    Then startup logs that the cache backend is unreachable and the process exits non-zero
      And it does not silently fall back to SQLite

  Scenario: Evicted cache entries are re-embedded at the next submission
    Given option (a) and some cache keys evicted after a completed sweep
    When the same config is submitted again
    Then the pre-embed plan contains exactly the evicted texts
      And no run of that submission fails with a cache miss unless a key is evicted after planning (the option (a) failure mode above)

  Scenario: In a shared instance, only cache keys can expire
    Given one Redis instance serving vectors and the cache under volatile-lru
    When key TTLs are inspected after a sweep
    Then every rpf:emb: key has a TTL and every vector key reports TTL -1

  Scenario: Cache keys cannot collide with vector-store keys
    Given one Redis instance serving both the vector store and the cache
    When both write keys
    Then cache keys use the rpf:emb: prefix and vector keys never match it
```

---

## Before-Checks [GATE]

- [ ] 48A ✅ on `main`; Slice 52 Branch B cache GO recorded, with the concrete need.
- [ ] `[redis]` extra scope confirmed: this slice reuses Slice 53's extra (or introduces it, if 53 hasn't shipped); no second Redis extra.
- [ ] harness-scout `detect_confirm` at slice start.

## After-Checks [GATE]

- [ ] Specification coverage: every GWT scenario ↔ ≥1 test.
- [ ] Branch coverage: 100% line + branch on the cache modules (48A's floor for `embedding_cache.py` carries over).
- [ ] Complexity evidence: policy `enforcing` (xenon via `./scripts/ci/quality-gates.sh`); local `bash scripts/ci/complexity-report.sh` → `.reports/complexity/pr-body.md`.
- [ ] Mutation on the Redis adapter's miss handling: survival budget met or waiver.
- [ ] `docs/plan/gate-evidence/slice-54.json` with coverage/complexity fields.

---

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9): cache port boundary, eviction/TTL stance, fail-closed startup
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED (Could) — blocked on 48A ✅ + 52 Branch B GO.
