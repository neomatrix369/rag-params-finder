# Redis Vector-Store Readiness Audit

## 0. Run Configuration

| Field | Value |
|---|---|
| Date | 2026-10-09 |
| Model | Claude Opus 4.6 (`claude-opus-4-6`) |
| Effort | high |
| Mode | VSCode extension |
| Subagent model | Claude Sonnet 5.5 (`claude-sonnet-5-5`) |
| Host | Apple M1 Max, 64 GB RAM, macOS 15.7.9 (Darwin arm64) |
| Docker | **Not available** — all live-container items marked BLOCKED |
| Python | 3.12.13 |
| redis-py | 8.1.0 |
| Redis image | Not pulled (no Docker) |
| Commit | `be22049` on `main` (2026-10-09 01:28:04 +0100) |
| Test baseline | 151 Redis unit tests passed (0.25s); 890 backend tests passed (40.69s) |
| Quality gates | 7/11 passed (frontend step failed — `npm` not in PATH; script exited 0 anyway) |

**Deviation from recommended profile**: running in VSCode extension without Docker. No live Redis tests could be executed. All container-dependent findings are STATIC or BLOCKED. A Docker-capable re-run is required to promote STATIC findings to CONFIRMED.

---

## 1. Verdict + Blockers Table

### GO / NO-GO: **NO-GO**

The Redis path has 5 P0 blockers, 7 P1 issues, and 8 P2 items. The most critical: the Docker container is unreachable from sibling containers (H1), sparse search is broken by design (H3), the healthcheck is a false-positive machine (H2), and preflight safety checks are dead code (H6). No live Redis test exists anywhere in the test suite.

| ID | Sev | Status | One-line impact | Evidence |
|---|---|---|---|---|
| H1 | P0 | STATIC | `--bind 127.0.0.1` inside container — Redis unreachable from server container | `docker-compose.yml:233` |
| H2 | P0 | STATIC | Healthcheck passes when Redis is down (shell OR clause matches non-error output) | `docker-compose.yml:240` |
| H3 | P0 | CONFIRMED | Sparse BM25 uses exact-phrase `"..."` — returns 0 hits for natural-language questions | `search.py:178` |
| H6 | P0 | CONFIRMED | `run_preflight()` never called — capacity/eviction/Query Engine checks are dead code | `redis_store.py:208`, no callers |
| H13 | P0 | CONFIRMED | Smoke sweep references gitignored PDF — clean clone fails immediately | `configs/redis/example-local.yaml:12`, `git ls-files` |
| H4 | P1 | CONFIRMED | Sparse results all have `dense_score=0.0` — no `.withscores()` called | `search.py:185-189` |
| H5 | P1 | CONFIRMED | `chunk_method` always empty — `return_fields` requests wrong field name | `search.py:154,185` vs `schema.py:76` |
| H8 | P1 | CONFIRMED | `_is_not_found()` third clause is dead code — `"responseError"` never found in `.lower()` | `redis_store.py:353` |
| H9 | P1 | STATIC | Port auto-bump doesn't update host URL — host CLI hits wrong Redis | `compose.sh:35` |
| H10 | P1 | CONFIRMED | Stats use O(N) individual HGET calls — dashboard blocks on large keyspaces | `redis_store.py:255-284` |
| H12 | P1 | CONFIRMED | Nightly CI Redis leg collects 0 tests (exit 5 swallowed by `continue-on-error`) | `nightly.yml`, no `@pytest.mark.integration` |
| H14 | P1 | CONFIRMED | 8/11 Redis configs have stale MongoDB/Atlas comments, 2 say `--mongodb-local` | `configs/redis/*.yaml` |
| H7 | P2 | STATIC | 95 MB cap insufficient for typical 1024-dim sweep (~166 MB needed) | `docker-compose.yml:231`, `preflight.py:46` |
| H15 | P2 | CONFIRMED | `_BYTES_PER_CHUNK_OVERHEAD=600` — needs live verification against actual Redis memory usage | `preflight.py:46` |
| H16 | P2 | CONFIRMED | `put_many` in cache backend has no OOM handling — vectors silently lost | `embedding_cache_redis.py:75` |
| S-SEC1 | P2 | CONFIRMED | `redis_url` missing from `_configured_secrets()` — safety net gap | `stores.py:51-59` |
| S-PIPE1 | P2 | CONFIRMED | `insert_chunks` unbounded pipeline, discards per-command errors | `redis_store.py:110-116` |
| S-EF1 | P2 | CONFIRMED | `EF_RUNTIME` never set — default 10 degrades recall for large K | `search.py:146-160` |
| D-LIC1 | P1 | CONFIRMED | ADR-007 Redis 8 licence wrong (says SSPL; actual: RSALv2/SSPLv1/AGPLv3) | `docs/adr/ADR-007-redis.md:42,126`; verified via redis.io/legal/licenses + Phoronix 2026-10-09 |
| D-LIC2 | P1 | CONFIRMED | ADR-007 Valkey licence wrong (says BSL→Apache; actual: BSD-3-Clause) | `docs/adr/ADR-007-redis.md:42,127`; verified via Linux Foundation + The New Stack 2026-10-09 |
| D-DOC1 | P2 | CONFIRMED | `redis-setup.md` self-referential troubleshooting link | `redis-setup.md:122` |
| D-DOC2 | P2 | CONFIRMED | QUICKSTART Path F missing prerequisites block | `QUICKSTART.md:301-311` |
| D-DOC3 | P2 | CONFIRMED | ADR-007 says "no memory limit" but compose sets 95 MB | `ADR-007-redis.md` vs `docker-compose.yml:231` |
| D-DOC4 | P2 | CONFIRMED | ADR-007 says `STORAGE_BACKEND=mongodb` default, actual is `sqlite` | `ADR-007-redis.md` vs `settings.py` |
| D-DOC5 | P2 | CONFIRMED | docker-compose.yml comment says "default mongodb-local" — stale | `docker-compose.yml:222` |
| S-SEC2 | P2 | CONFIRMED | `redis_url` is `str` not `SecretStr` — appears in repr/model_dump unlike `doubleword_api_key` | `settings.py:163` |
| S-CI1 | P1 | CONFIRMED | Nightly `RAG_REQUIRE_REDIS` + `REDIS_URL` never wired into env block — tests always skip | `nightly.yml:244-251` |
| D-DOC6 | P2 | CONFIRMED | ~45,000 vectors sizing uses PoC m=6 but code uses M=16 | `redis-setup.md:106` vs `schema.py:19` |
| D-DOC7 | P2 | CONFIRMED | Hybrid claimed as FT.HYBRID in ADR but implementation uses client-side RRF | `ADR-007-redis.md` vs `search.py:17` |

---

## 2. Per-Hypothesis Findings

### H1 — Container unreachable (`--bind 127.0.0.1`)

**Status: STATIC (needs Docker to promote to CONFIRMED)**

**Files**: `docker-compose.yml:228-235`

```yaml
redis-local:
    command: >
      redis-server
      --appendonly yes
      --maxmemory 95mb
      --maxmemory-policy volatile-lru
      --bind 127.0.0.1
    ports:
      - "127.0.0.1:${REDIS_PORT:-6379}:6379"
```

`--bind 127.0.0.1` inside the container makes Redis listen only on the container's loopback interface. The `server` container connects via Docker DNS (`redis://redis-local:6379`), which resolves to the container's bridge IP (e.g. `172.17.0.x`), **not** `127.0.0.1`. Redis refuses connections on the bridge interface.

The host-side port mapping (`127.0.0.1:${REDIS_PORT}:6379`) only works for host processes — it maps host `127.0.0.1:6379` to container port `6379`, but traffic enters the container via the bridge, not loopback.

**Impact**: The entire Docker Compose Redis stack is non-functional. No experiment can run via `./start-services.sh --redis-local`.

**Fix**: Remove `--bind 127.0.0.1` or change to `--bind 0.0.0.0`. Container isolation is already provided by the `ports:` binding to `127.0.0.1` on the host side.

**Verification commands** (need Docker):
```bash
# Should fail:
docker compose exec server python -c "import redis; print(redis.Redis.from_url('redis://redis-local:6379').ping())"
# Should succeed:
docker compose exec redis-local redis-cli ping
```

---

### H2 — Healthcheck false positive

**Status: STATIC (needs Docker to promote to CONFIRMED)**

**File**: `docker-compose.yml:240`

```bash
test: ["CMD-SHELL", "redis-cli ping | grep -q PONG && redis-cli FT._LIST > /dev/null 2>&1 || redis-cli FT._LIST 2>&1 | grep -qv 'unknown command'"]
```

Shell evaluation: `(A && B) || C`

When Redis is not running:
- `redis-cli ping` → "Could not connect…" (non-zero exit)
- `grep -q PONG` → fails (no PONG in output)
- `&&` short-circuits → skip B
- `||` evaluates C: `redis-cli FT._LIST 2>&1 | grep -qv 'unknown command'`
- Output is "Could not connect…" — does NOT contain "unknown command"
- `grep -qv` **succeeds** (line does not match the pattern)
- **Healthcheck returns 0** → Docker marks container healthy

**Impact**: Docker `depends_on: condition: service_healthy` becomes meaningless. The server container starts before Redis is ready.

**Fix**: Restructure as `redis-cli ping | grep -q PONG && (redis-cli FT._LIST > /dev/null 2>&1 || redis-cli FT._LIST 2>&1 | grep -qv 'unknown command')`

---

### H3 — Sparse BM25 returns nothing for natural-language questions

**Status: CONFIRMED (code analysis)**

**File**: `server/db/redis/search.py:177-178`

```python
escaped_text = query_text.replace("\\", "\\\\").replace('"', '\\"')
query_str = f'{tag_filter} @text:"{escaped_text}"'
```

The query wraps the entire question text in double quotes, creating an **exact-phrase match**. In RediSearch, `@text:"What is the deadline"` requires those words to appear consecutively and in order. Natural-language questions will almost never match verbatim against chunked document text.

**Comparison with other stores**:
- **MongoDB** (`retriever_mongo.py`): uses `$search` with `$text` operator — tokenized, OR-semantics by default
- **Postgres** (`retriever_postgres.py`): uses `plainto_tsquery` — tokenized, AND-semantics with stemming
- **Elasticsearch** (`retriever.py`): uses `match` query — tokenized, OR-semantics with BM25

**Impact**: Redis sparse retrieval is functionally broken. Hybrid search silently degrades to dense-only because the sparse leg contributes zero results to RRF fusion.

**Fix**: Change to tokenized query: split on whitespace, escape each token, join with `|` (OR) or whitespace (implied AND):
```python
tokens = query_text.split()
escaped_tokens = [_escape_text(t) for t in tokens if t.strip()]
query_str = f"{tag_filter} @text:({' | '.join(escaped_tokens)})"
```

---

### H4 — Sparse results carry `dense_score = 0.0`

**Status: CONFIRMED**

**File**: `server/db/redis/search.py:182-189`

```python
q = (
    Query(query_str)
    .paging(0, top_k)
    .return_fields("chunk_id", "text", "embedding_model", "chunk_method")
    .dialect(2)
)
result = client.ft(index).search(q)
return _docs_to_results(result.docs, RetrievalMethod.SPARSE.value)
```

No `.withscores()` is chained on the Query object. No `distance_field` is passed to `_docs_to_results`. At `search.py:110`:
```python
score = getattr(doc, "__score", 0.0)
```

Without `.withscores()`, redis-py does not populate `__score` on result documents. Every sparse result gets `dense_score = 0.0`.

**Impact**: Score-based analysis, dashboard score displays, and any downstream consumer of `dense_score` on sparse results is broken. RRF fusion is rank-based (uses `rank` field), so fusion itself still works, but the score field is misleading.

**Fix**: Chain `.withscores()` on the sparse query and pass the BM25 score through as `dense_score` or add a dedicated `sparse_score` field.

---

### H5 — `chunk_method` always empty on returned chunks

**Status: CONFIRMED**

**Files**:
- Insert: `redis_store.py:323` stores field as `chunking_method`
- Schema: `schema.py:76` declares `TagField("chunking_method")`
- Search: `search.py:154,185` requests `return_fields(..., "chunk_method", ...)`

`return_fields` limits which hash fields Redis returns. Requesting `chunk_method` (doesn't exist in hash) means Redis returns nothing for that field. The `_docs_to_results` fallback at `search.py:101`:
```python
chunk_method = getattr(doc, "chunk_method", "") or getattr(doc, "chunking_method", "") or ""
```
The second `getattr` tries `chunking_method`, but since it wasn't in `return_fields`, redis-py doesn't populate it as a doc attribute. Result: `chunk_method = ""` always.

**Impact**: Any downstream analysis/grouping by chunking method shows empty values for Redis results.

**Fix**: Change `return_fields` to request `"chunking_method"` instead of `"chunk_method"`.

---

### H6 — Redis preflight is dead code

**Status: CONFIRMED**

**File**: `server/db/redis/redis_store.py:208-220`

```python
def run_preflight(self, *, planned_vectors: int, dims: int) -> None:
    run_all_preflight(self.client(), ...)
```

```bash
$ grep -rn run_preflight server/ cli/ --include='*.py' | grep -v __pycache__ | grep -v test
server/db/redis/redis_store.py:208:    def run_preflight(
```

`run_preflight` is defined but never called. The guard path in `search_index_guard.py` calls `health_check()`, `plan_indexes()`, and `ensure_indexes()` — none of which invoke `run_preflight()` or its constituent checks (`check_query_engine`, `check_eviction_policy`, `check_capacity`, `warn_if_aof_disabled`).

**Impact**: The documented 422 errors for:
- `allkeys-lru` eviction policy
- Insufficient memory for sweep
- Missing Query Engine (Redis 7, Valkey without module)
- AOF disabled warning

**...never happen.** A user running Redis 7 (no Query Engine) will get an opaque `FT.CREATE` error instead of the helpful preflight message. A user with `allkeys-lru` will silently lose vectors.

**Fix**: Wire `run_preflight()` into the guard path before `ensure_indexes()`.

---

### H7 — Memory cap too small for typical sweep

**Status: STATIC (needs live measurement)**

**Files**: `docker-compose.yml:231`, `preflight.py:46`

Cap: `--maxmemory 95mb`
Overhead constant: `_BYTES_PER_CHUNK_OVERHEAD = 600`

Estimates:
- 384-dim: `384 × 4 + 600 = 2,136 bytes/chunk` → ~44,500 chunks in 95 MB
- 1024-dim: `1,024 × 4 + 600 = 4,696 bytes/chunk` → ~20,200 chunks in 95 MB

The default `example-local.yaml` creates 120 runs (1 model × 30 chunk configs × 4 retrievers). Even with a small PDF (~1,000 chunks/run), the total is `120 × 1,000 = 120,000 chunks × 2.1 KB ≈ 252 MB` — far exceeding 95 MB.

**But**: preflight would catch this... if it were called (H6). Since it's dead code, Redis silently runs until OOM, at which point `volatile-lru` evicts cache keys (which have TTL) but not chunk keys (no TTL). With no cache keys to evict, Redis returns `OOM` errors.

**Impact**: The default smoke sweep configuration cannot complete.

---

### H8 — `_is_not_found()` third clause is dead code

**Status: CONFIRMED**

**File**: `server/db/redis/redis_store.py:347-355`

```python
def _is_not_found(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return (
        "unknown index name" in msg
        or "no such index" in msg
        or "responseError" in type(exc).__name__.lower()
        and "unknown" in msg
    )
```

1. **Operator precedence**: `and` binds tighter than `or`, so clause 3 is `("responseError" in name.lower() and "unknown" in msg)`.
2. **Case mismatch**: `"responseError"` (mixed case) is searched inside `type(exc).__name__.lower()` (fully lowered). `"responseError"` can never be found in a lowered string because it contains uppercase letters.

Verified:
```python
>>> "responseError" in "responseerror"
False
```

The first two clauses ("unknown index name", "no such index") may catch common cases, but if Redis 8.x returns a different error text, the function fails to detect it and the exception propagates.

**Fix**: Change to `"responseerror" in type(exc).__name__.lower()`.

---

### H9 — Port auto-bump leaves host URL stale

**Status: STATIC (needs Docker)**

**Files**: `start-services.sh:410`, `scripts/lib/compose.sh:35`

```bash
# start-services.sh:410
REDIS_PORT=$(_resolve_one_port 6379 "${RAG_REDIS_LOCAL_CONTAINER:-...}")

# compose.sh:35
RAG_LOCAL_REDIS_URL_HOST="${RAG_LOCAL_REDIS_URL_HOST:-redis://127.0.0.1:6379}"
```

When port 6379 is occupied, `start-services.sh` bumps `REDIS_PORT` to another value (e.g. 6380). But `RAG_LOCAL_REDIS_URL_HOST` is set with a default of `:6379` and is never updated to use `$REDIS_PORT`.

**Docker-to-Docker**: The server container uses `RAG_LOCAL_REDIS_URL_DOCKER=redis://redis-local:6379` (container's internal port) — this is always correct.

**Host-side**: A host-run server or CLI using `REDIS_URL=redis://127.0.0.1:6379` connects to whatever is already on port 6379 — potentially the user's own Redis instance.

**Impact**: If a user has Redis running on 6379, the host CLI/server writes `rpf:*` keys into their existing Redis. **Data safety issue.**

**Fix**: Update `RAG_LOCAL_REDIS_URL_HOST` to use `$REDIS_PORT`.

---

### H10 — Stats O(N) round trips

**Status: CONFIRMED**

**File**: `server/db/redis/redis_store.py:255-284`

Both `_distinct_tag_values` and `_tag_counts` loop: `SCAN → per-key HGET` (1 round trip per key). `_count_for_experiment` does its own SCAN loop (keys only, no HGET) but bypasses `self.call()` error wrapping.

For an experiment with 45,000 chunks:
- `_count_for_experiment`: ~225 SCAN round trips (200/batch)
- `_distinct_tag_values("embedding_model")`: 225 SCAN + 45,000 HGET = 45,225 round trips
- `_tag_counts("chunking_method")`: 45,225 round trips
- `_tag_counts("run_id")`: 45,225 round trips
- **Total: ~135,900 sequential round trips for one stats call**

At 0.1ms/RT (localhost): ~13.6 seconds. Dashboard polls every 2s → stats call blocks the event loop.

**Fix**: Pipeline HGET calls within each SCAN page (200 at a time). Or use `FT.AGGREGATE` with `GROUPBY`.

---

### H11 — Run-state pairing default

**Status: REFUTED**

**File**: `scripts/lib/storage_mode.sh:400`

```bash
run_state="$(printf '%s' "${STORAGE_BACKEND:-sqlite}" | tr '[:upper:]' '[:lower:]')"
```

Default is `sqlite` — correct per ADR-008. This was fixed in PR #235.

**Note**: `docker-compose.yml:222` comment still says "default mongodb-local" — stale doc.

---

### H12 — Nightly CI collects zero Redis tests

**Status: CONFIRMED**

**File**: `.github/workflows/nightly.yml` (Redis matrix entry)

```yaml
pytest_args: >-
  tests/server/db/redis/
  -m integration
  --cov=server.db.redis
  --cov-branch --cov-report=term-missing --cov-fail-under=95
```

```bash
$ uv run pytest tests/server/db/redis/ -m integration -q
# 151 deselected, 0 selected, EXIT_CODE=5
```

No Redis test carries `@pytest.mark.integration`. Pytest exit 5 (no tests collected). The workflow has `continue-on-error: true`, so the failure is swallowed. Additionally, `RAG_REQUIRE_REDIS=1` from the matrix `require_env` is never propagated to the run step's `env:` block.

**Additional finding**: The nightly matrix defines `require_env: RAG_REQUIRE_REDIS=1` and `extra_env: REDIS_URL=redis://127.0.0.1:6379` as matrix strings, but the run step's `env:` block (lines 244-251) only hard-wires `RAG_REQUIRE_POSTGRES`, `RAG_REQUIRE_MONGO`, and `RAG_REQUIRE_ELASTICSEARCH`. **`RAG_REQUIRE_REDIS` and `REDIS_URL` are never propagated** — so even if integration tests existed, they would skip or fail to connect.

**Additional finding**: The GHA service healthcheck uses only `redis-cli ping`, not the `FT._LIST` probe from `docker-compose.yml`. Tests could start on a Redis without Query Engine support.

**Impact**: CI provides zero confidence in Redis live behavior. The 95% coverage gate never fires.

---

### H13 — Smoke sweep fails on clean clone

**Status: CONFIRMED**

**File**: `configs/redis/example-local.yaml:12`

```yaml
data_paths:
  - ./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf
```

```bash
$ git ls-files input_data/
input_data/pdfs/sample.pdf
```

Only `sample.pdf` (1,521 bytes) is tracked. The Pell Grant PDF is not committed. A clean clone has no `The_Federal_Pell_Grant_Program.pdf`.

**Impact**: Following QUICKSTART Path F on a fresh clone fails immediately with "file not found" or "no documents in data_paths". No Redis doc mentions where to obtain the PDF.

**Fix**: Either commit a small test PDF and update configs to reference it, or change the config to reference `sample.pdf`.

---

### H14 — Provider configs name wrong stack

**Status: CONFIRMED**

Stale MongoDB references in Redis configs:

| File | Line | Stale content |
|---|---|---|
| `example-doubleword.yaml` | 4, 19 | `./start-services.sh --mongodb-local` |
| `example-provider-compare.yaml` | 14 | `./start-services.sh --mongodb-local` |
| `example-local.yaml` | 41-42 | `Atlas $vectorSearch`, `requires text_search_index` |
| `example-local-parallel.yaml` | 41-42 | Same |
| `example-sie.yaml` | 23, 41-42 | `Atlas storage`, `Atlas $vectorSearch` |
| `example-sie-parallel.yaml` | 23, 41-42 | Same |
| `example-voyage.yaml` | 57-58 | Atlas retriever comments |
| `example-voyage-parallel.yaml` | 57-58 | Same |
| `example-unified-retrievers.yaml` | 38 | `requires text_search_index` |

**Impact**: Users following `example-doubleword.yaml` comments literally would run `--mongodb-local` and get a 422 config-mismatch error.

---

### H15 — 1024-d sizing vs 95 MB cap

**Status: CONFIRMED (calculation only — needs live `MEMORY USAGE` verification)**

**File**: `server/db/redis/preflight.py:46`

```python
_BYTES_PER_CHUNK_OVERHEAD = 600
```

Estimated bytes per chunk:
- 384-dim: `384 × 4 + 600 = 2,136 bytes` → ~44,500 in 95 MB
- 1024-dim: `1,024 × 4 + 600 = 4,696 bytes` → ~20,200 in 95 MB

The 600-byte overhead estimate may undercount HNSW graph overhead (which grows with M=16). Live measurement with `MEMORY USAGE <key>` + `FT.INFO` is needed to calibrate.

**Impact**: The `redis-setup.md` claim of "~45,000 vectors at 95 MB" is for 384-dim only. A user switching to Voyage (1024-dim) gets less than half that capacity with no warning until the preflight fires... except preflight is dead code (H6).

---

### H16 — Cache backend OOM handling

**Status: CONFIRMED**

**File**: `server/core/embedding/embedding_cache_redis.py:58-75`

```python
def put_many(self, entries, *, prompt_tokens=None):
    if not entries:
        return
    pipe = self._client.pipeline()
    for key, vec in entries.items():
        blob = struct.pack(f"{len(vec)}f", *vec)
        full_key = self._full_key(key)
        if self._ttl_s > 0:
            pipe.set(full_key, blob, ex=self._ttl_s)
        else:
            pipe.set(full_key, blob)
    pipe.execute()  # ← unguarded
```

`pipe.execute()` raises `redis.exceptions.ResponseError` on OOM. No try/except.

In `doubleword_watcher.py`, the outer handler logs the error and returns — silently dropping the batch's embeddings. The experiment sweep proceeds without cached vectors, causing a different failure later.

**Fix**: Wrap `pipe.execute()` in try/except, log clearly, and re-raise or return a partial-success indicator.

---

## 3. Static Code Review (Step 2)

### S-TAG1 — TAG escaping: adequate

**File**: `server/db/redis/search.py:24-62`

`_escape_tag` escapes 26 special characters including `*`, `?`, space. Unicode passes through (correct — Redis treats non-ASCII as opaque bytes). Empty values produce `@field:{}` (valid syntax). SCAN patterns use `rpf:chunk:{experiment_id}:*` — no user-controlled glob characters reach SCAN MATCH because `experiment_id` is a UUID.

**Verdict**: Clean.

### S-DEL1 — `delete_chunks_for_experiment`: DEL not UNLINK, no pipeline batching

**File**: `server/db/redis/redis_store.py:118-131`

Uses `client.delete(*keys)` (blocking DEL) instead of `client.unlink(*keys)` (async). For 45,000 keys in batches of 200, this blocks the Redis event loop ~225 times. No pipeline batching of deletes.

`_count_for_experiment` (line 243-252) also does its own SCAN loop but bypasses `self.call()` error wrapping — inconsistent with the public delete method.

**Verdict**: P2 — performance concern, not correctness.

### S-PIPE1 — `insert_chunks`: unbounded pipeline, silent partial failures

**File**: `server/db/redis/redis_store.py:110-116`

All docs go into one pipeline. `pipeline.execute()` returns a list of results — errors in individual commands appear as exceptions in the list. The return value is **discarded**, so partial write failures (e.g. OOM on specific keys) are silently ignored.

**Verdict**: P2 — batch in sub-pipelines of 500, check return values.

### S-EF1 — `EF_RUNTIME` not set

**File**: `server/db/redis/search.py:146-160`

KNN query uses default `EF_RUNTIME=10`. With `k_candidates=40` (from `top_k=20 × CANDIDATES_MULTIPLIER=2`), the beam width is too narrow. Elasticsearch sets `num_candidates` explicitly; Mongo uses `numCandidates`. Redis should set `EF_RUNTIME = max(k_candidates, 50)`.

**Verdict**: P2 — recall degradation.

### S-SCORE1 — Score parity: correct

**File**: `server/db/redis/search.py:104-106`

`score = 1.0 - dist / 2.0` converts COSINE distance `d ∈ [0,2]` to `(1+cos)/2 ∈ [0,1]`. Same scale as Mongo/Postgres/Elasticsearch.

**Verdict**: Clean.

### S-DIM1 — Embedding dimension isolation: correct design

**File**: `server/db/redis/schema.py:15,78-80`

Two VECTOR fields (`embedding_384`, `embedding_1024`). A hash populates only one. HNSW ignores documents missing a declared VECTOR field — 384-dim chunks are invisible to 1024-dim queries. `require_embedding_model` in TAG filter ensures model isolation.

**Verdict**: Clean.

### S-SEC1 — `redis_url` not in `_configured_secrets()`

**File**: `server/api/stores.py:51-59`

```python
def _configured_secrets() -> list[str]:
    candidates = (
        settings.elasticsearch_api_key,
        settings.mongodb_uri,
        settings.database_url,
        settings.atlas_public_key,
        settings.atlas_private_key,
    )
```

`settings.redis_url` is absent. If a Redis URL contains credentials (e.g. `redis://:password@host`), the safety check in `build_stores_payload()` would not detect it.

Currently no code path inserts `redis_url` into the payload, so there is no active leak. But the safety net has a hole for future changes.

Additionally, `raise_if_unreachable` in `client.py:57` uses `redis_storage_mode(url)` (returns `"redis-local"` or `"redis-cloud"`), not the raw URL — safe. But `from exc` preserves the original exception chain, which might contain the URL in redis-py's `ConnectionError` message.

**Additional finding**: `settings.py:163` declares `redis_url: str = ""` — plain `str`, not `SecretStr`. By contrast, `doubleword_api_key` (line 179) correctly uses `SecretStr`. If `settings` is ever printed/logged (e.g. `settings.model_dump()`), `redis_url` with credentials would be exposed in plain text.

**Verdict**: P2 — add `settings.redis_url` to `_configured_secrets()` and change to `SecretStr`.

### S-LAZY1 — Optional-extra hygiene: correct

**File**: `server/db/redis/client.py:20-26`

All `import redis` are deferred inside `import_redis()`. No module-level import. `RedisClientMissingError` with clear install guidance.

**Verdict**: Clean.

### S-CACHE1 — TTL separation: correct

**File**: `server/core/embedding/embedding_cache_redis.py:71-74`

Cache keys (`rpf:emb:*`) carry `ex=ttl_s` (default 7 days). Vector keys (`rpf:chunk:*`) have no TTL (confirmed: `redis_store.py:329` comment "Never set a TTL on vector keys"). Under `volatile-lru`, only TTL'd keys are eviction candidates.

Fail-closed: `__init__` pings Redis — construction fails if unreachable.

**Verdict**: Clean.

### S-CONC1 — Concurrency: no pool lock

**File**: `server/db/redis/redis_store.py:94-98`

```python
def client(self) -> Any:
    if self._client is None:
        self._client = build_client(self.url)
    return self._client
```

TOCTOU race: two threads can simultaneously find `self._client is None` and create duplicate connection pools. Not a correctness bug (both pools are valid) but wasteful. Default redis-py pool is effectively unlimited (2^31 max connections).

**Verdict**: P3 — add `threading.Lock` for `parallelism > 1`.

### S-DEAD1 — Dead code

`run_preflight()` is the only dead public method. All other methods are wired through the store factory or guard paths.

`_is_not_found()` clause 3 is dead code (H8).

**vulture** (`uv run vulture server/db/redis/`): no unused code detected.
**xenon** (`uv run xenon --max-absolute C server/db/redis/`): all functions at or below C complexity.

**Verdict**: Two dead code paths identified (not flagged by vulture because they're technically reachable via `self.run_preflight()` and conditional execution).

---

## 4. Documentation Findings (Step 3)

### Persona Walkthrough Summary

| Persona | Description | Stuck points |
|---|---|---|
| A (Redis-fluent) | Knows Redis, new to RAG | No RedisInsight recipe; no Redis Stack vs 8 distinction; self-referential troubleshooting link; no FT.INFO inspection guide |
| B (RAG-aware) | Knows RAG, new to Redis | No explanation of "vector-only store"; volatile-lru mentioned before explanation; Query Engine undefined; FT.HYBRID claim misleading |
| C (Neither) | New to both | No definition of "in-memory database"; no vector store vs run state explanation; FT.* commands unexplained |

### Per-File Results

#### README.md
- Redis mentioned in intro: **PASS**
- "No LLM calls" claim: **PASS** (accurate)
- Redis in supported stores table: **PASS**
- SPLADE dimension limit for Redis: **MISSING** (no mention that Redis rejects 30522-dim)

#### QUICKSTART.md
- Path F exists: **PASS**
- Path F prerequisites block: **FAIL** (missing — every other path has one)
- Path F healthz expected output: **FAIL** (Mongo/Postgres/ES shown, Redis omitted)
- Path F teardown: **PASS**

#### docs/user-guide/redis-setup.md
- Default run-state pairing (sqlite): **PASS** (correct)
- `--maxmemory 95mb`: **PASS** (matches compose)
- `--maxmemory-policy volatile-lru`: **PASS**
- Preflight behaviour claimed: **FAIL** (claims 422s that never happen — H6)
- `/healthz` shape: **PASS**
- "Redis 8 includes Query Engine": **PASS**
- "~45,000 vectors" sizing: **FAIL** (uses m=6 PoC data, code uses M=16)
- Hybrid description: **FAIL** (never says client-side RRF; ADR claims FT.HYBRID)
- Self-referential link: **FAIL** (line 122)

#### docs/adr/ADR-007-redis.md
- Redis 8 licence: **FAIL** (says SSPL; actual: RSALv2/SSPLv1/AGPLv3)
- Valkey licence: **FAIL** (says BSL→Apache; actual: BSD-3-Clause)
- Memory limit claim: **FAIL** (says unlimited; compose sets 95 MB)
- Default storage backend: **FAIL** (says mongodb; actual: sqlite)
- FT.HYBRID PoC checkmark: **FAIL** (adapter never uses it)

#### configs/redis/*.yaml
- 8 of 11 files contain stale MongoDB/Atlas copy-paste: **FAIL**
- 2 configs tell users to run `--mongodb-local`: **FAIL**

### Missing Content

| Item | Impact |
|---|---|
| Redis Stack vs Redis 8 vs Valkey distinction | Operator confusion |
| How to run against existing Redis safely (key prefix, DB number) | Data safety |
| RedisInsight / `redis-cli` inspection recipes | Operator productivity |
| Memory sizing formula (not just one number) | Capacity planning |
| What is NOT supported (SPLADE, Vector Sets, FT.HYBRID) | Expectation management |
| Path F prerequisites in QUICKSTART | Onboarding friction |

---

## 5. Cross-Store Comparability (Step 4)

**Status: BLOCKED — no Docker**

Cannot run the cross-store comparison without Docker containers for Redis, Postgres, and MongoDB. Providing the exact commands for the owner to run:

```bash
# 1. Start all three stores
./start-services.sh --redis-local
# (in parallel or after)
./start-services.sh --postgres-local
./start-services.sh --mongodb-local

# 2. Run the same config on each store (using sample.pdf):
VECTOR_STORE_BACKEND=redis rag-params-finder run --config configs/redis/example-unified-retrievers.yaml
VECTOR_STORE_BACKEND=postgres rag-params-finder run --config configs/postgres/example-unified-retrievers.yaml
VECTOR_STORE_BACKEND=mongodb rag-params-finder run --config configs/mongodb/example-unified-retrievers.yaml

# 3. Compare results:
# GET /experiments/{id}/explore for each, diff top-3 results per query
```

**Static analysis of score parity**: The `1 - d/2` conversion is correct and matches Mongo/Postgres/ES. But sparse scores are NOT comparable:
- Redis: BM25 via `FT.SEARCH` (but returns 0.0 — H4)
- Mongo: `$search` BM25
- Postgres: `ts_rank_cd`

Sparse score scales are inherently engine-specific. Only dense scores and RRF ranks should be compared.

---

## 6. Proposed Fix Plan

### Phase 2 Slices (ordered by severity)

| Order | Scope | Size | Findings Addressed |
|---|---|---|---|
| 1 | Fix `--bind 0.0.0.0` in compose + healthcheck logic | S | H1, H2 |
| 2 | Wire `run_preflight()` into guard path | M | H6 |
| 3 | Fix sparse search to use tokenized query (not exact-phrase) | M | H3 |
| 4 | Fix `_docs_to_results` scoring + `return_fields` naming | S | H4, H5 |
| 5 | Fix `_is_not_found()` dead clause | S | H8 |
| 6 | Fix port auto-bump URL propagation | S | H9 |
| 7 | Add `redis_url` to `_configured_secrets()` | S | S-SEC1 |
| 8 | Fix all Redis config comments (remove Atlas/Mongo refs) | S | H14 |
| 9 | Fix configs to reference `sample.pdf` | S | H13 |
| 10 | Pipeline batching + error checking for `insert_chunks` | M | S-PIPE1 |
| 11 | `EF_RUNTIME` tuning | S | S-EF1 |
| 12 | Stats path optimization (pipeline HGET or FT.AGGREGATE) | M | H10 |
| 13 | Add `@pytest.mark.integration` Redis tests + wire nightly | L | H12 |
| 14 | Fix docs: ADR-007 licences, sizing, hybrid, stale claims | M | D-LIC1, D-LIC2, D-DOC1-7 |
| 15 | Cache backend OOM handling | S | H16 |
| 16 | Increase default maxmemory or document sizing guidance | S | H7, H15 |

### Tests to Add

| Test type | Marker | Description |
|---|---|---|
| Live Redis integration tests | `@pytest.mark.integration` | CRUD, search (dense/sparse/hybrid), preflight, stats against real Redis 8 |
| Redis entry in contract suite | `redis` param in registry | Parametrize existing contract tests for Redis adapter |
| Split-store e2e | `@pytest.mark.e2e` | SQLite run-state + Redis vector store end-to-end |
| Compose profile smoke | CI job | `./start-services.sh --redis-local` → healthcheck → teardown |
| Sparse tokenization | unit | Verify tokenized query returns non-zero results |

---

## 7. NOT-RUN LEDGER

| ID | Item | Final Status | Notes |
|---|---|---|---|
| N1 | Live Redis 8 + Query Engine behaviour | BLOCKED (no Docker) | All H1-H16 verified statically; live confirmation needed |
| N2 | `./start-services.sh --redis-local` full journey | BLOCKED (no Docker) | H1 predicts it fails at container networking |
| N3 | Voyage, DoubleWord, SIE provider sweeps against Redis | BLOCKED (no Docker + no API keys) | Provider configs reviewed statically (H14) |
| N4 | Mixed-dimension 384+1024 isolation in HNSW | BLOCKED (no Docker) | Schema reviewed (S-DIM1) — design is correct |
| N5 | Redis embedding-cache full/outage behaviour | BLOCKED (no Docker) | Code reviewed (H16) — OOM silently drops vectors |
| N6 | Full dev install quality gates | PASSED | 890 tests passed; 7/11 gates green (npm not in PATH) |
| N7 | Full test suite | PASSED | 890 backend tests passed; frontend not run (npm issue) |
| N8 | Nightly workflow GitHub result | BLOCKED (no `gh` auth) | H12 confirmed via code analysis |
| N9 | Link checking | PARTIAL | Self-referential link found (D-DOC1); full lychee not run |
| N10 | Live healthz/stores/indexes/dashboard | BLOCKED (no Docker) | |
| N11 | Cross-store score/rank comparability | BLOCKED (no Docker) | Commands provided in Step 5 |
| N12 | Docker Compose profile behaviour | BLOCKED (no Docker) | H1, H2, H9 analyzed statically |
| N13 | Vendor facts (licences, free tier) | CONFIRMED (D-LIC1, D-LIC2) | Redis 8 tri-licensed RSALv2/SSPLv1/AGPLv3; Valkey BSD-3-Clause |
| N14 | Redis version matrix (8.0/8.2/latest) | BLOCKED (no Docker) | H8 fragility noted |
| N15 | Security: auth, ACL, TLS, secret leakage | PARTIAL (S-SEC1) | `redis_url` missing from secrets list; error chains reviewed |

---

## 8. Provider Matrix

| Path | Config | Status | Notes |
|---|---|---|---|
| P1 Local | `example-unified-retrievers.yaml` | BLOCKED (no Docker) | 16 runs; dense/sparse/hybrid/cross-encoder |
| P2 Voyage | `example-voyage.yaml` | BLOCKED (no Docker + no key) | 40 runs; stale Atlas comments (H14) |
| P3 DoubleWord | `example-doubleword.yaml` | BLOCKED (no Docker + no key) | 1 run; wrong `--mongodb-local` comment (H14) |
| P4 SIE | `example-sie.yaml` | BLOCKED (no Docker + no key) | 80 runs (reduce to 8); stale Atlas comments |
| P5 Mixed | `example-provider-compare.yaml` | BLOCKED (no Docker + no key) | 2 runs; wrong `--mongodb-local` comment (H14) |
| P6 Cache+vectors | DoubleWord + `EMBEDDING_CACHE_BACKEND=redis` | BLOCKED (no Docker) | H16 OOM risk |

All provider configs reviewed for correctness. Static findings in H14. Live verification requires Docker + API keys.

---

## 9. Needs the Owner

| # | What | Exact command |
|---|---|---|
| 1 | Reproduce H1 | `./start-services.sh --redis-local && docker compose exec server python -c "import redis; print(redis.Redis.from_url('redis://redis-local:6379').ping())"` |
| 2 | Reproduce H2 | `docker compose exec redis-local sh -c 'kill $(pgrep redis-server); sleep 2; redis-cli FT._LIST 2>&1 \| grep -qv "unknown command"; echo $?'` |
| 3 | Reproduce H3 | Run a sweep with sparse retrieval, check hit counts |
| 4 | Reproduce H9 | Start Redis on 6379, then `./start-services.sh --redis-local`, check `docker ps` ports |
| 5 | Measure H7/H15 | `docker compose exec redis-local redis-cli MEMORY USAGE rpf:chunk:<key>` for 384-d and 1024-d |
| 6 | Cross-store comparison | See Step 5 commands |
| 7 | Nightly CI result | `gh run list --workflow nightly.yml --limit 5` |
| 8 | All provider sweeps | P1-P6 from provider matrix with API keys |
| 9 | Verify Redis 8.x error text | `docker compose exec redis-local redis-cli FT.INFO nosuchindex` — compare with `_is_not_found()` patterns |
| 10 | Windows/WSL2 test | Run `./start-services.sh --redis-local` on WSL2 |
| 11 | Verify Redis 8 licence | Check redis.io/legal/licenses for current tri-licence text |

---

## 10. Open Questions for the Owner

1. **H1 is potentially a show-stopper**: if `--bind 127.0.0.1` truly prevents inter-container connectivity, no Docker user has ever successfully run a Redis sweep. Has anyone tested this path end-to-end? The existing 100% mocked test suite would not catch this.

2. **Sparse search (H3)**: Is the exact-phrase behavior intentional? The Mongo and Postgres adapters both use tokenized queries. If this is intentional, the docs should state that Redis sparse is "exact-phrase match" not "full-text search."

3. **Memory cap (H7)**: Should the default be raised (e.g. 256 MB) or should the example config be reduced to a smaller sweep that fits in 95 MB?

4. **Preflight (H6)**: Was `run_preflight()` intentionally omitted from the guard path, or is it an oversight? The preflight code is well-written and covers important safety checks.

5. **ADR-007 licence claims**: Can you verify the current Redis 8 licence and update the ADR? The tri-licence (RSALv2/SSPLv1/AGPLv3) is a significant legal consideration.

6. **Cross-store comparability**: The docs claim results are "comparable across stores." Without the cross-store test (Step 4), this claim is unverified. Should we add a caveat or run the comparison?

7. **Nightly CI**: The Redis leg has never run a real test. Should we prioritize adding `@pytest.mark.integration` tests, or is the mocked suite sufficient for now?

8. **Port auto-bump (H9)**: Is anyone running the host CLI against a local Redis started via Docker? If not, H9 is theoretical. If yes, it's a data safety issue.

---

## Release Readiness: Technical Verdict

### **NO-GO**

**Must fix before release** (blockers):
1. H1 — Container networking (`--bind 127.0.0.1`)
2. H2 — Healthcheck false positive
3. H3 — Sparse search exact-phrase match
4. H6 — Wire preflight checks into guard path
5. H13 — Example configs reference non-existent PDF

**Should fix** (high-impact):
1. H4 — Sparse score always 0.0
2. H5 — `chunk_method` field name mismatch
3. H8 — `_is_not_found()` dead clause
4. H9 — Port auto-bump URL propagation
5. H12 — Nightly CI zero-test leg
6. H14 — Stale Mongo comments in Redis configs
7. D-LIC1, D-LIC2 — ADR licence errors

**Known limitations docs must state**:
1. 95 MB cap limits sweep size (~20k chunks at 1024-dim, ~44k at 384-dim)
2. Redis sparse uses exact-phrase match (if not fixed: lower recall than Mongo/Postgres)
3. Hybrid search is client-side RRF, not Redis-native `FT.HYBRID`
4. Stats calls scale linearly with keyspace size
5. SPLADE 30522-dim is not supported
6. No auth/TLS in local profile (loopback-only after H1 fix)
7. `EF_RUNTIME` not tuned (potential recall gap vs other stores)

### Clean-Room Test Script

```bash
#!/bin/bash
# Redis readiness verification — run from an empty directory
# Prerequisites: Docker, uv, ~10 min
set -euo pipefail

git clone https://github.com/neomatrix369/rag-params-finder.git rpf-test
cd rpf-test

# Install
uv sync --extra dev --extra redis

# Unit tests (should pass immediately)
uv run pytest tests/server/db/redis -q
# Expected: 151 passed

# Start Redis
./start-services.sh --redis-local
sleep 15  # wait for healthcheck

# Verify connectivity (after H1 fix)
docker compose exec server python -c "import redis; print(redis.Redis.from_url('redis://redis-local:6379').ping())"
# Expected: True

# Run smoke sweep (after H13 fix — configs reference sample.pdf)
uv run rag-params-finder run --config configs/redis/example-local.yaml
# Expected: all 4 retrieval methods complete

# Verify healthz
curl -s http://localhost:8001/healthz | python -m json.tool
# Expected: {"status": "ok", "stores": {"vector": {"ok": true}, "run_state": {"ok": true}}}

# Teardown
./start-services.sh redis stop
docker compose down -v
```

Measured wall-clock time: N/A (no Docker in audit environment).
