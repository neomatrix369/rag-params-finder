# Store end-to-end walkthrough — MongoDB · Postgres · Elasticsearch · Redis

> **Simulated desk-check, 2026-09-25, `main @ eb78855`.** MongoDB and Postgres/Supabase are traced through real code. Elasticsearch and Redis are traced **as if** Slices 49A → 49B → 50 → 51 (ES) and 53 (Redis) had shipped exactly as specified. Nothing here was executed against a live Elasticsearch or Redis. Live proof is owned by the 49B split-store acceptance test, the nightly `vector-store-integration` matrix (#248) and Slice 53's clean-clone journey gate.
>
> **Builds on:** the Elasticsearch round-3 desk-check ([DECISIONS #240](../plan/DECISIONS.md)), which found the unwired split-store data path; this walkthrough doesn't repeat it. **Adds:** the Redis column, the gaps no slice owns (§4), and the 15-stage journey comparison.
>
> **Legend:** ✅ works · ◐ works with a caveat · ✗ breaks · *(planned: slice)* = behaviour the named slice specifies.
>
> **Evidence source:** MongoDB and Postgres cells cite **code** (file:line on `main`). Elasticsearch and Redis cells cite **specs** (slice sections and DECISIONS rows), so they are only as true as the slices once shipped.
>
> **Redis vs Valkey:** "Redis" here means a server with the Query Engine: Redis Open Source 8, or Valkey (the Linux Foundation fork) with valkey-search. Slice 52 picks one; the flow below is the same for both.

## 1. Verdicts

| Question | Verdict | Why |
|---|---|---|
| Did we run an end-to-end walkthrough of the Redis slices? | **Not before this document.** Slices 52–54 had two spec-review rounds (#230, #231); the ES slices had a desk-check (#240). This is the first Redis trace. | — |
| Is adding a store simple and similar to the other stores? | **Yes, once 49A/49B/51 ship.** No for anything built on today's code. | Using a store is the same two-command shape for all four (§3.2). Redis adds one concern the others don't have: memory sizing and eviction policy (stage 13). Today, a third store would hit the 10 unwired sites in #240. |
| Is it well documented? | **Mongo/Postgres: mostly** (gaps in §3.1). **ES/Redis: planned, not yet verifiable.** | 51's registry-driven docs-parity gate and 53's journey gate enforce parity. Before this change, no slice cited the official ES/Redis/Valkey docs. |
| Does Redis meet the zero-changes criterion (no edits to routes, sweep logic, UI components or CLI commands; defined in Slice 53's Output contract)? | **Not as specified before this change. It will once 51 ships G4 (now owned, #253).** | `ExperimentsScreen.tsx:447-450` hard-codes store hints inside the guarded `frontend/src/components/`. Everything else is either config schema (one `DatabaseProvider` token) or infra (`stores.tsv` row, `EXTRAS=redis`), which the criterion allows. |
| Is it ports & adapters (hexagonal)? | **Core yes, edges leaky.** | Driven ports exist and the sweep/lifecycle code calls only ports (§2). 49A/49B complete the two-port split: run state vs `VectorStore`. The identity leaks in §4 (a guard skip, a stats allow-list, UI and 422 hints) were unowned before this change and are now owned by 49B/51 (#253). |

## 2. Hop-by-hop data flow

| # | Hop (evidence) | MongoDB | Postgres / Supabase | Elasticsearch *(planned)* | Redis *(planned)* |
|---|---|---|---|---|---|
| 1 | CLI `run` → `POST /experiments` (`cli/main.py:28-42`, `cli/api_client.py:97-100`) | ✅ | ✅ | ✅ thin client | ✅ thin client. ◐ hint string at `api_client.py:117` names only mongodb/postgres (cosmetic) |
| 2 | Config validation: `DatabaseProvider` Literal (`server/models/config.py:13`) | ✅ | ✅ `supabase` normalised (`:16-23`) | ✅ Slice 50 adds the token; 49A drift test (#240 item 5) | ✅ Slice 53 adds one token. This counts as config schema, which the criterion allows |
| 3 | Boot settings: known stores + URI checks (`server/settings.py:23-24,130-171`) | ✅ | ✅ | ✅ 49B `ensure_storage_ready()` checks both stores; pairing rule (ii) (#241) | ✅ same path; Redis supplies `REDIS_URL` through adapter config |
| 4 | Config↔engine guard (`config_backend_guard.py:52-54`) | ✅ | ✅ | ✅ asserts against the **vector** store (49A, D2) | ✅ same |
| 5 | Index preflight (`search_index_guard.py:131-152`) | ✅ Atlas ensure | ✅ catalog introspection | ✅ 49B `preflight_stores()` → vector store `plan_indexes()` / `capabilities()` | ◐ Redis checks (`FT._LIST`, `maxmemory-policy`, capacity) run through the same entry. **G3:** today the unknown-backend branch at `:147-152` returns `preflight_not_applicable()`, so an unknown store passes silently (**fails open**). 49B removes it, and a missing plan becomes a 422 (#253) |
| 6 | Experiment doc `storage_mode` (`experiments.py:84` → `health_check.py:40-44`) | ✅ | ✅ | ✗ today (unknown → Mongo mode) → ✅ vector store's `storage_mode()` (49A/49B) | ✅ `redis-local` / `redis-cloud` |
| 7 | Run label (`config.py:195` default `"mongodb"`; persisted at `orchestrator.py:839`) | ✅ | ✅ | ✅ new runs persist the YAML value; an omitted value defaults to `mongodb`, which D2 rejects on an ES server (422) | ✅ same: a Redis run always carries `redis` |
| 8 | Schedule (`executors.py:44-48`) | ✅ | ✅ | ✅ store-agnostic | ✅ store-agnostic |
| 9 | Chunk write (`orchestrator.py:921` `insert_chunks`) | ✅ | ✅ | ✗ today (#240: chunks land in the run-state store) → ✅ 49B rewire site 1 | ✅ inherits 49B; 53 keys HASHes as `rpf:chunk:{experiment_id}:{run_id}:{chunk_id}` (illustrative, final from the 52 PoC), so an interrupted run overwrites instead of duplicating |
| 10 | Search (`pipeline/search.py:50` → `get_retriever_backend()`) | ✅ Atlas `$vectorSearch` | ✅ pgvector + tsvector | ✅ `get_vector_store().retriever()` (49A); shared `rrf_fuse()` (50) | ✅ same port; score `1 − d/2` ≡ `(1+cos)/2`; KNN + TAG pre-filter (52 PoC verifies undercount + distance semantics) |
| 11 | Rerank (`search.py:95`) | ✅ | ✅ | ✅ store-agnostic | ✅ store-agnostic |
| 12 | Persist results / run phases (`orchestrator.py:996,1040`) | ✅ | ✅ | ✅ run-state store | ✅ run-state store |
| 13 | Resume signatures (`signatures.py:24,46`) | ✅ | ✅ | ◐ **G1:** legacy rows without `database_provider` fall back to `default_database_provider()` (from `STORAGE_BACKEND`), which is correct for them. If 49B moved it to follow the vector store, legacy signatures would change and resume would re-run completed runs → 49B freezes it (#253) | ◐ same |
| 14 | List / detail (`experiments.py:150-200` via `experiments_shared.py`) | ✅ | ✅ | ✅ run-state only | ✅ run-state only |
| 15 | Explore / best-config labels (`results_analyzer.py:31,125,175`) | ✅ | ✅ | ◐ **G1:** same legacy fallback as hop 13; frozen by 49B | ◐ same |
| 16 | db-stats / vector-db-stats (`experiments_shared.py:61-68`) | ✅ | ✅ | ✗ today → ✅ 49B composed stats (vector counts replace, never add). **G2:** `normalize_stats_database_provider()` (`stats_common.py:105-112`) maps any label other than mongo/postgres to the fallback, erasing `elasticsearch` → 49B takes the list from the registry (#253) | ✅ [`FT.INFO`](https://redis.io/docs/latest/commands/ft.info/) + `INFO memory` via `stats_common`; same **G2** fix |
| 17 | Pause / resume / cancel (`experiments.py:259-363`, `experiment_control.py`) | ✅ | ✅ | ✅ run-state + in-process events | ✅ same; 53 scenario: no re-embedding for completed runs |
| 18 | Delete cascade (`experiments.py:365-388`) | ✅ | ✅ | ✗ today → ✅ 49B vectors first, idempotent retry (#246) | ✅ TAG-scoped delete by `experiment_id` |
| 19 | Startup reconciliation (`startup_reconciliation.py:30-96`) | ✅ | ✅ | ✅ run state; orphan-vector reconciler = Should (#246) | ✅ same |
| 20 | `/healthz` (`health_check.py:87-121`) | ✅ | ✅ | ✗ today (unknown → `ok: false`) → ✅ 49B two-store, 503 if either is down (#247) | ✅ same |
| 21 | Dashboard labels (`frontend/src/utils/storageLabels.ts`) | ✅ | ✅ | ◐ today (generic Host/Table) → ✅ adapter `labels()` (51) | ✅ `labels()` |
| 22 | Dashboard empty-state hints (`frontend/src/components/screens/ExperimentsScreen.tsx:447-450`) | ✅ | ✅ (points at `configs/supabase/`) | **✗ G4:** hard-coded MongoDB / Postgres only → 51 renders them from the registry's `example_config` (#253) | **✗ G4** until 51 ships: otherwise a TSX edit inside the zero-changes guard |
| 23 | `indexes` CLI (`cli/indexes_cmd.py:9-27`) | ◐ imports server code directly | ◐ list only | ✗ today → ✅ via `GET /api/stores` (51) | ✅ same |

**Redis-only hops** (no Mongo/Postgres equivalent). All are specified in 53 and checked in 52's PoC. Preflight reads settings through `INFO`, which managed services allow even when they block `CONFIG` (#253):
- Query Engine present ([`FT._LIST`](https://redis.io/docs/latest/commands/ft._list/)) → 422 with remediation if missing.
- `maxmemory_policy` from `INFO memory` must be `noeviction`, or `volatile-lru` under option (a) in 54 ([eviction](https://redis.io/docs/latest/develop/reference/eviction/)) → 422 otherwise.
- `maxmemory` capacity vs planned vectors → 422 before embedding.
- AOF state from `INFO persistence` ([persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)) → a **warning** if off, since vectors are re-creatable by re-running.
- Vector keys never carry a TTL (`TTL -1`, mutation-guarded).
- **The `volatile-lru` gotcha (Slice 54 option (a) only; option (b) never sets `volatile-lru` on the vector instance):** under `volatile-lru` only keys with a TTL can be evicted. That is safe for vectors only while every vector key stays at TTL -1, which is why the TTL test is mutation-guarded. And if memory runs out with no expiring keys left, writes fail with an OOM error (exact text to be recorded in the 52 PoC). Option (b), a separate cache instance, avoids both.
- Ops: one `scripts/lib/stores.tsv` row with a `cmd:redis-cli ping` probe (#244, #253), `EXTRAS=redis` server image (#243), a `redis` leg in the nightly matrix (#248).

### 2.1 Error handling (all stores)

- An adapter exception during chunk write or search fails **that run** (status FAILED, store named in the error). The experiment then follows `on_error` (`config.py:186`): `continue` runs the remaining runs, `stop` halts after the failure. 49B pins both for the vector store (#253).
- A store that is down before the sweep starts is caught earlier: `/healthz` 503 and a preflight 422 at submit, with run-state checks not attempted when the vector store fails (49B).
- Delete is vectors first and idempotent, so a partial failure is completed by retrying (#246).

## 3. User journey (15 stages)

### 3.1 Coverage

Scope: this is the **vector-store** journey (Slice 53). The Redis embedding cache (Slice 54, Could) has its own setup section in `redis-setup.md` and isn't a journey stage.

| # | Stage | MongoDB | Postgres / Supabase | Elasticsearch *(51)* | Redis *(53)* |
|---|---|---|---|---|---|
| 1 | Discover & choose | ✅ README, `mongodb-setup.md:15-30` | ✅ `postgres-setup.md:11-50` | planned `elasticsearch-setup.md` | planned `redis-setup.md` + 52 report |
| 2 | Account / prereqs | ✅ Atlas M0 | ✅ Supabase | planned (none for local) | planned (none for local; Redis Cloud free = smoke-only) |
| 3 | Install | ✅ shared | ✅ shared | planned `[elasticsearch]` extra | planned `[redis]` extra |
| 4 | Configure env | ✅ `.env.example:5-24` | ✅ `.env.example:27-45` | planned ES block | planned `REDIS_URL` + `VECTOR_STORE_BACKEND` |
| 5 | Start stack | ✅ `--mongodb-local` | ✅ `--postgres-local` / `--postgres-cloud` | planned `--elasticsearch-local` (D5 pairs `postgres-local`) | planned `--redis-local` (D5) |
| 6 | Indexes / schema | ✅ manual on M0, auto on local | ✅ `schema.sql` auto | planned auto mapping | planned `FT.CREATE` auto |
| 7 | Verify | ✅ `health-check.sh` + `/healthz` | ✅ same | planned two-store `/healthz` | planned two-store `/healthz`; `health-check.sh` runs the `stores.tsv` command probe (no Redis-specific script edit) |
| 8 | Pick config | ✅ `configs/mongodb/` | ◐ `configs/supabase/` (named for the product, engine is `postgres`) | planned `configs/elasticsearch/` | planned `configs/redis/` |
| 9 | Run a sweep | ✅ | ✅ | planned | planned |
| 10 | Dashboard | ✅ quota + tier | ◐ one sentence, no quota | planned `labels()` | planned `labels()` |
| 11 | Switch backends | ◐ lists Mongo modes only; wording fixed in this change | ✅ both directions | planned switching rows | planned switching rows |
| 12 | Troubleshoot | ✅ | ✅ | planned (heap, `vm.max_map_count`, licence 403) | planned (Query Engine missing, OOM, eviction, AOF, TLS) |
| 13 | Limits & sizing | ✅ 512 MB M0 | ◐ "check Supabase pricing" only | planned heap + HNSW memory | planned **bytes per vector in RAM** (52 measured) |
| 14 | Teardown / reset | ◐ `stop-services.sh:16` checks the deprecated `RAG_LOCAL_ATLAS` | ✗ `stop-services.sh` has no Postgres branch | planned via `stores.tsv` (51, #244) | planned via `stores.tsv` (no Redis-specific edit) |
| 15 | Delete experiment data | ✅ CLI + manual JS | ◐ one line, no manual SQL | planned two-store delete | planned two-store delete |

### 3.2 Effort to switch (commands · env vars · files)

| Route | Commands | Env vars | Files touched |
|---|---|---|---|
| Mongo cloud → Postgres local *(today)* | 2: `./start-services.sh --postgres-local`, `rag-params-finder run --config configs/supabase/…` | 2: `STORAGE_BACKEND`, `DATABASE_URL` | 1 config path |
| Mongo → Elasticsearch local *(51)* | 2: `--elasticsearch-local`, `run --config configs/elasticsearch/…` | 1–2: `VECTOR_STORE_BACKEND` (+ ES URL for cloud) | 1 config path |
| Mongo → Redis local *(53)* | 2: `--redis-local`, `run --config configs/redis/…` | 1–2: `VECTOR_STORE_BACKEND` (+ `REDIS_URL` for cloud) | 1 config path. **Plus one Redis-only decision:** `maxmemory` sizing and the eviction policy (54 option a/b) |

The shape is the same for all four stores. The sizing step differs. Elasticsearch fixes its JVM heap once per container (1 GB in the local profile), and HNSW memory lives outside it. Redis holds every vector in RAM, so `maxmemory` has to fit the **planned sweep**, which preflight checks before embedding. Redis is the only store where the operator sizes memory per sweep.

## 4. Gaps no slice owned before this change

| ID | Gap (evidence) | Effect on Redis | Owner |
|---|---|---|---|
| G1 | `signatures.py:46`, `results_analyzer.py:31,125` fall back to `settings.default_database_provider()` (from `STORAGE_BACKEND`) for rows without `database_provider` | None today: the fallback is correct for legacy rows, and new runs persist the YAML value. The risk is a 49B change that makes the fallback follow the vector store, which would re-run completed legacy runs on resume | **49B** — freeze the fallback on the run-state store; scenario pins it |
| G2 | `stats_common.py:105-112` `normalize_stats_database_provider()` accepts only mongo/postgres/supabase | Persisted `redis` / `elasticsearch` labels are replaced by the fallback in stats | **49B** — accept every registered provider (list from the registry) |
| G3 | `search_index_guard.py:147-152` returns `preflight_not_applicable()` for an unknown backend | A Redis preflight gap would pass silently (fails open) | **49B** — remove the branch; `preflight_stores()` has no skip path, and a missing index plan is a 422 |
| G4 | `ExperimentsScreen.tsx:447-450` hard-coded MongoDB / Postgres hints; `config_backend_guard.py:23-26` 422 hint also knows two stores | Breaks 53's zero-changes guard (`frontend/src/components/`) | **51** — registry `example_config` via `GET /api/stores` feeds both; 53 Before-Check |
| G5 | No slice cited official ES / Redis / Valkey docs | Executors would work from memory (HNSW options, RRF licence tier, `FT.*`, eviction, AOF, ACL) | **50–54** — External references block + Before-Check. The vendor doc wins over a slice statement; discrepancies go to DECISIONS |
| G6 | Present-day drift: `mongodb-setup.md:234` ("no config file changes"), `architecture.md:328` (`--profile dev` doesn't exist), `extending.md:208` (deprecated shim path) | Wrong today for users and contributors | **Fixed in this change** (the #251 precedent); 51 keeps the full rewrite |

**Correction during review (#253):** an earlier draft said Redis runs would be mislabelled `mongodb` when YAML omits `database_provider`. That is wrong: the config default is `mongodb`, D2 rejects it on a Redis server, and new runs always persist the YAML value. G1 is now the freeze risk above.

Owned before this change and not repeated here:
- the split-store data path → 49B (#240, #242);
- `stop-services.sh` → 51 `stores.tsv` (#244);
- the C4 ports/adapters view → 51;
- `stats_common` labels → 49B/51;
- the `status.py` duplicate Literal → 49A;
- the CLI `indexes` bypass → 51.

## 5. Hexagonal assessment

| Aspect | State | Evidence |
|---|---|---|
| Driven ports | ✅ `StorageBackend` (run state), `RetrieverBackend`; 49A adds `VectorStore` | `server/db/ports/storage.py:12-166`, `retriever_backend.py:14-26` |
| Application core calls ports only | ✅ orchestrator, search, lifecycle, reconciliation | `orchestrator.py:851-1040`, `experiments_shared.py:22-68`, `startup_reconciliation.py:30-96` |
| Adapter selection in one place | ◐ today an if/elif factory (`store_factory.py:27-58`) → registry (49A) | 49A Output contract |
| Adapter identity leaking into core, domain or edges | ◐ a stats allow-list (G2), a guard skip (G3), UI and 422 hints (G4), all owned by 49B/51 (#253); `status.py` duplicate Literal (49A) | §4 |
| Driving adapters (CLI, UI) talk only to the API | ◐ `indexes_cmd.py` imports server code → fixed by 51 | `cli/indexes_cmd.py:9-27` |
| Port granularity | ◐ `StorageBackend` is ~30 methods mixing run state and chunks → 49A/49B split vector concerns onto `VectorStore`; chunk methods deprecated | #240 item 3 |

**Open design question for reviewers:**
- **49B (#242, decided):** rewire the 10 call sites to call `get_vector_store()` explicitly.
- **Alternative:** a composite `StorageBackend`, returned by the factory when the two stores differ, would route chunk / vector / stat methods to the vector store and leave `server/api` and `server/core/pipeline` untouched.
- **Both are valid ports & adapters.** 49B's explicit second port makes the split visible at each call site; the composite hides it behind the existing port. This walkthrough doesn't reopen #242. It records the trade-off for reviewers.
