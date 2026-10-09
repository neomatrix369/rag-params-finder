# Elasticsearch Community-Readiness Audit

| Field | Value |
|---|---|
| Date | 2026-10-08 |
| Model | Claude Opus 4.6 (`claude-opus-4-6`) |
| Effort | high (VSCode extension default) |
| Mode | VSCode extension (not CLI `acceptEdits`) |
| Host | Swamis-MBP.lan, Darwin arm64 (daily laptop, NOT disposable VM) |
| Docker | Not available — all live-ES items marked BLOCKED |
| Subagent model | Haiku 4.5 |
| Scope | Parts 1–6, 8 (read-only / static analysis). Part 7 deferred to disposable VM |

---

## Verification Ledger

> Items from Part 7 backlog + Part 8 additions.
> Labels: **RAN** = executed, **READ** = code/doc inspection only, **STUB** = deterministic stand-in used, **BLOCKED** = cannot verify in this environment.

| ID | Description | Status | Evidence | Verdict |
|---|---|---|---|---|
| L1 | Live ES test suite | BLOCKED: no Docker/ES | — | — |
| B1 | Bulk errors:true swallowed | READ | Part 1 §1 | P0 CONFIRMED |
| B2 | Payload/timeout limit | READ | Part 1 §2 | P1 CONFIRMED |
| R1 | Refresh/visibility race | READ | Part 1 §7 | P2 |
| R2 | Aggregation cap 100 | READ | Part 1 §5 | P2 CONFIRMED |
| R3 | num_candidates cap | READ | Part 1 §6 | P2 |
| C1 | ES 8.x cluster behaviour | READ | Part 3 §6 | P1 |
| C2 | Secured cluster / API key | READ | Part 3 §5 | P1 |
| C3 | Failure modes mid-sweep | READ | Part 3 §2 | P1 |
| D1 | Docker prerequisites | BLOCKED: no Docker | — | — |
| D2 | Persistence claims | BLOCKED: no Docker | — | — |
| P1 | Pairing contradiction | READ | Part 1 §3 | P0 CONFIRMED |
| P2 | stop-services.sh leftover | BLOCKED: no Docker | — | — |
| E1 | Real healthz/stores JSON | BLOCKED: no Docker/ES | — | — |
| E2 | Provider matrix never run | READ | Part 6 | P1 |
| E5 | Partial writes on failure | READ | Part 3 §2 | P1 |
| J1 | Full journey never executed | READ | Part 2 | P1 |
| J2 | Dashboard never viewed | BLOCKED: no Docker/ES | — | — |
| J3 | Cross-store claim unproven | BLOCKED: no Docker/ES | — | — |
| N1 | Nightly job reproduced | BLOCKED: no Docker | — | — |
| K1 | Docs link/consistency | RAN | Part 4 | P1 |
| K2 | Apple-silicon / ARM images | BLOCKED: no Docker | — | — |
| S1 | Sample data missing | READ | Part 8 §1 | P0 CONFIRMED |
| S2 | Docs claim consistency | READ | Part 8 §2 | P1 |
| S3 | Questions file shape | READ | Part 8 §3 | P1 |

---

## Part 1 — Known Suspects

### §1 Bulk errors silently swallowed — P0

**File:** `server/db/elasticsearch/elasticsearch_vector_store.py:109`

```python
self.call(lambda: self.client().bulk(operations=operations, refresh="wait_for"))
```

The ES bulk API returns `{"errors": true, "items": [...]}` when individual actions fail (mapping conflict, version conflict, shard unavailable). The return value is discarded. The adapter reports success even when zero documents were actually indexed. A user's experiment appears complete with zero retrievable chunks.

**Fix required:** Check `response["errors"]`, extract per-item failures, raise or log with actionable detail.

### §2 No bulk batching / timeout risk — P1

**File:** `server/db/elasticsearch/elasticsearch_vector_store.py:105-109`

All chunks for a run are sent in a single bulk call. For a large PDF (10k+ chunks × 1024-dim float32), the payload exceeds 40 MB. Combined with `request_timeout=10` in `client.py:33`, large ingestions will timeout and fail silently (see §1).

**Fix required:** Batch into configurable chunks (e.g. 500) and raise `request_timeout` for bulk operations (or make it configurable).

### §3 Run-state pairing contradiction — P0

**File:** `scripts/lib/storage_mode.sh:374,382-383`

`_pair_elasticsearch_run_state` rejects `sqlite` as a run-state backend, but:
- `server/settings.py` defaults `storage_backend` to `sqlite` (ADR-008)
- `docs/user-guide/elasticsearch-setup.md` says sqlite is the default run-state
- The actual Python code works fine with sqlite + elasticsearch

A user following the docs gets rejected by the shell script. This blocks `./start-services.sh --elasticsearch-local`.

**Fix required:** Allow `sqlite` pairing in `storage_mode.sh`.

### §4 Env var name drift — P1

**File:** `scripts/lib/stores.tsv` uses `ELASTICSEARCH_URL`
**File:** `server/settings.py:153-154` reads `ELASTICSEARCH_CLOUD_URL` / `ELASTICSEARCH_LOCAL_URL`

The shell script sets a variable the Python server never reads. ES connectivity fails silently — no error, just "cannot connect."

**Fix required:** Align env var names across shell and Python. Prefer the Python names as canonical.

### §5 Aggregation cap — P2

**File:** `server/db/elasticsearch/elasticsearch_vector_store.py:249`

`_term_counts` uses `terms ... size: 100`. An experiment with >100 distinct values for any aggregated field silently drops the tail. Affects dashboard stats accuracy for large experiments.

### §6 num_candidates unbounded — P2

**File:** `server/db/elasticsearch/retriever.py:66`

`num_candidates = top_k * CANDIDATES_MULTIPLIER` — no upper bound. ES caps `num_candidates` at 10,000 and returns 400 if exceeded. With `top_k=100` and a high multiplier, this can fail at query time.

### §7 refresh semantics — P2 (informational)

`refresh: "wait_for"` is correct for test/small-scale use (blocks until the next refresh makes the doc visible). For large-scale production use, this adds latency. Not a bug, but worth documenting as a known performance characteristic.

---

## Part 2 — New-User Journey

### Journey assessment: 13/15 stages complete, 2 partial

**3 HIGH severity gaps:**

1. **No QUICKSTART "Path E" for Elasticsearch** — Paths A–D exist for MongoDB/Postgres but there is no ES path. An ES-interested user landing on QUICKSTART.md hits a dead end. They must independently discover `docs/user-guide/elasticsearch-setup.md`.

2. **Docker Desktop memory requirement undocumented** — ES (1 GB JVM) + MongoDB run state containers need 2–3 GB total. Docker Desktop defaults to 2 GB on Mac/Windows. Container stays unhealthy with no explanation.

3. **`vm.max_map_count` buried in troubleshooting** — Linux users need `vm.max_map_count ≥ 262144` before ES starts. This critical prerequisite is only in the troubleshooting table (`elasticsearch-setup.md:112`), not in prerequisites.

**5 MEDIUM severity gaps:**

1. `uv pip install -e ".[elasticsearch]"` not in QUICKSTART install block — ImportError on first run
2. Model download (~46 MB) not mentioned in ES setup guide — first EMBEDDING phase looks like a hang
3. ES disk watermarks (read-only at 85%) not documented
4. No ES-native verification commands in diagnostics (no `GET rpf-chunks/_mapping`, `_count`)
5. `(1+cos)/2` score normalisation explained only in ADR-006, not in setup guide

**Time estimate:** Clone → `/healthz ok`: 10–25 min. First completed sweep: additional 25–55 min. No "smoke" config exists for ES (Postgres has a 16-run first-prove config).

---

## Part 3 — Code Checks (ES Adapter)

### §1 Boot sequence — lazy init, no ping

**File:** `server/main.py:38-54`

ES indexes are created lazily at first `submit_chunks()` via `ensure_indexes()`. No boot-time connectivity check. If ES is down at boot, the server starts healthy — the first experiment submission fails with a connection error mid-pipeline.

**Recommendation (P2):** Add a boot-time ES ping in `lifespan()` (log warning, don't block startup).

### §2 Failure modes — incomplete error coverage — P1

**File:** `server/db/elasticsearch/client.py:39-52`

`is_connection_failure` catches `ConnectionError`, `ConnectionTimeout`, `OSError` but misses:
- **401/403** — wrong API key or insufficient privileges → raw `ApiError` bubbles up
- **429** — bulk rate limit hit → no retry logic
- **503** — cluster red/unavailable → not retried

Mid-sweep, any of these kills the experiment with an unhelpful traceback instead of a clear "ES authentication failed" or "ES rate-limited, retrying."

### §3 Sparse score comparability claim — P1

**File:** `server/db/elasticsearch/retriever.py:1-7` (module docstring)

The comment claims cross-store score comparability. For dense cosine, the `(1+cos)/2` normalisation works. For BM25 sparse scores, ES returns unbounded floats that are stored in `dense_score` — these are not comparable to MongoDB's `$searchScore` or Postgres's `ts_rank`. The dashboard's score comparison view is misleading for sparse/hybrid.

### §4 Filter isolation — PASS

All query paths (`dense_search`, `sparse_search`, `hybrid_search`) mandate `experiment_id`, `embedding_model`, and `run_id` as keyword filters. IDs use `keyword` mapping type — no analyser tokenisation issues. Chunk isolation is sound.

### §5 Credential leak risk — P1

**File:** `server/db/elasticsearch/client.py:49`

`raise_if_unreachable` logs the full ES URL. If the URL contains embedded credentials (`https://user:pass@host`), they appear in server logs. Additionally, `server/api/stores.py:51-59` `_configured_secrets()` does not include ES URL — it won't be redacted from `/api/stores` response if someone adds ES URL exposure there.

**File:** `scripts/lib/stores.tsv` — the ES URL variable appears in shell logs during `start-services.sh` execution.

### §6 Version coupling — P1

**File:** `pyproject.toml` — `elasticsearch>=8.0.0` (no upper bound)

**File:** `docker-compose.elasticsearch-local.yml` — `docker.elastic.co/elasticsearch/elasticsearch:9.0.2`

The client library declares `>=8.0.0` but the Docker image is 9.x. An 8.x cluster user would get no error at import time but could hit breaking API changes at runtime. The error message says "Elasticsearch 9.x required" even though 8.x is technically supported by the client library.

### §7 Contract test coverage — ZERO

**File:** `tests/` — no files matching `test_elasticsearch*` or `test_es_*` exist.

Zero contract tests for the ES adapter. Compare: MongoDB has integration tests, Postgres has `test_postgres_store_integration.py`. The ES adapter is entirely untested beyond static analysis (ruff/mypy pass).

---

## Part 4 — Docs Checks

### ES setup guide review

**File:** `docs/user-guide/elasticsearch-setup.md`

- **Structure:** Clear Path A (local) / Path B (cloud) split. Prerequisites listed.
- **Gap:** No mention of `vm.max_map_count` in prerequisites (only in troubleshooting table)
- **Gap:** Docker Desktop memory requirement not stated
- **Gap:** No "first smoke run" walkthrough — user reads setup, then must find config examples separately

### Config example prerequisites — P1

**File:** `configs/elasticsearch/example-doubleword.yaml:4` — says `--mongodb-local` (wrong, should be `--elasticsearch-local` or `--elasticsearch-cloud`)

**File:** `configs/elasticsearch/example-provider-compare.yaml:14-15` — same wrong prerequisite

7 of 7 ES config files have Atlas-specific comments referencing `$vectorSearch` and `text_search_index` — copy-paste from MongoDB configs, misleading for ES users.

### Cross-doc consistency — P1

- `QUICKSTART.md` mentions ES in the sweep code block but has no "Path E" section
- `CLAUDE.md` correctly documents `--elasticsearch-local` and `--elasticsearch-cloud`
- `README.md` backend table includes ES but links to setup guide (correct)
- `elasticsearch-setup.md` references `ELASTICSEARCH_LOCAL_URL` (matches `settings.py`)
- `stores.tsv` uses `ELASTICSEARCH_URL` (does NOT match — see Part 1 §4)

---

## Part 5 — Announcement Readiness

### Go / No-Go Summary

| Priority | Count | Verdict |
|---|---|---|
| **P0 — must fix before announcement** | 3 | **NO-GO** |
| **P1 — should fix before announcement** | 12 | — |
| **P2 — can ship, document as known** | 4 | — |
| **BLOCKED — cannot verify without Docker** | 9 | — |

### **VERDICT: NO-GO for community announcement**

Three P0 blockers prevent announcing:

| ID | Finding | Why P0 |
|---|---|---|
| B1 | Bulk errors silently swallowed | User's experiment "completes" with zero indexed chunks. Data loss with no error. |
| P1-pair | Run-state pairing rejects sqlite | `./start-services.sh --elasticsearch-local` fails on fresh clone following docs |
| S1 | Sample PDF not in git | Every example config's `data_paths` points to `input_data/pdfs/` which is gitignored. Fresh clone → immediate FileNotFoundError |

### Prioritised Fix List

**P0 — Must fix (blocks announcement):**

| Fix ID | Description | Files | Effort |
|---|---|---|---|
| F-B1 | Check bulk response `errors` field, raise on failures | `elasticsearch_vector_store.py` | S |
| F-P1 | Allow sqlite pairing in `_pair_elasticsearch_run_state` | `storage_mode.sh` | XS |
| F-S1 | Add a sample PDF to `input_data/pdfs/` (or update gitignore) | `.gitignore`, `input_data/` | XS |

**P1 — Should fix (announce with caveats if not fixed):**

| Fix ID | Description | Files | Effort |
|---|---|---|---|
| F-B2 | Batch bulk calls (500 chunks) + raise timeout | `elasticsearch_vector_store.py`, `client.py` | M |
| F-C1 | Test with ES 8.x, fix version message | `client.py`, docs | S |
| F-C2 | Wrap 401/403/429/503 in actionable errors | `client.py` | M |
| F-C3 | Handle partial write cleanup on failure | `elasticsearch_vector_store.py` | M |
| F-E2 | Create ES contract tests (at least CRUD + search) | `tests/` | L |
| F-E4 | Align env var names (stores.tsv vs settings.py) | `stores.tsv` | XS |
| F-J1 | Add QUICKSTART Path E for Elasticsearch | `QUICKSTART.md` | S |
| F-K1 | Fix config prerequisites (remove `--mongodb-local`) | `configs/elasticsearch/*.yaml` | XS |
| F-K2 | Remove Atlas-specific comments from ES configs | `configs/elasticsearch/*.yaml` | XS |
| F-S2 | Fix sparse score comparability claim | `retriever.py` docstring | XS |
| F-S3 | Fix questions file schema mismatch in docs | docs | XS |
| F-C5 | Mask credentials in logged ES URLs | `client.py` | S |

**P2 — Known limitations (document, fix later):**

| Fix ID | Description | Files | Effort |
|---|---|---|---|
| F-R1 | Document `refresh: wait_for` performance characteristic | docs | XS |
| F-R2 | Cap or document aggregation `terms.size: 100` limit | `elasticsearch_vector_store.py` or docs | XS |
| F-R3 | Cap `num_candidates` at 10,000 | `retriever.py` | XS |
| F-Boot | Add boot-time ES ping (warning only) | `main.py` | S |

### Known Limitations (draft for README)

```markdown
## Elasticsearch Support — Known Limitations

Elasticsearch vector store support is available as of vX.Y.Z. Please note:

- **Dimensions:** Only 384-dim (local models) and 1024-dim (Voyage/SIE/DoubleWord) embeddings
  are supported. Other dimensions require manual index mapping changes.
- **Score comparability:** Dense cosine scores are normalised to [0,1] across all stores.
  Sparse (BM25) scores are store-specific and not directly comparable across backends.
- **Bulk ingestion:** Very large PDFs (10k+ chunks) may require increasing the ES client
  timeout. Default is 10 seconds.
- **Aggregation cap:** Dashboard term aggregations are capped at 100 unique values per field.
- **Refresh latency:** `refresh: wait_for` is used for correctness. High-throughput
  production deployments may want to tune this.
- **ES version:** Tested with Elasticsearch 9.x. ES 8.x may work but is not officially tested.
- **Contract tests:** ES adapter has zero automated tests. MongoDB and Postgres have
  integration test suites.
```

### Smoke-test script (draft)

```bash
#!/usr/bin/env bash
# scripts/smoke-es.sh — Quick ES smoke test (requires running ES + server)
set -euo pipefail

ES_URL="${ELASTICSEARCH_LOCAL_URL:-http://localhost:9200}"
SERVER_URL="${SERVER_URL:-http://localhost:8001}"

echo "=== ES Smoke Test ==="

# 1. ES reachable?
echo -n "ES cluster health... "
curl -sf "${ES_URL}/_cluster/health" | python3 -c "
import sys, json; h=json.load(sys.stdin)
print(f\"{h['status']} ({h['number_of_nodes']} nodes)\")
if h['status'] == 'red': sys.exit(1)
"

# 2. Server healthy?
echo -n "Server /healthz... "
curl -sf "${SERVER_URL}/healthz" | python3 -c "
import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))
"

# 3. Submit minimal config
echo "Submitting smoke config..."
RESULT=$(curl -sf -X POST "${SERVER_URL}/experiments" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "es-smoke-test",
    "database_provider": "elasticsearch",
    "data_paths": ["input_data/pdfs/"],
    "embedding": {"provider": "local", "models": ["all-MiniLM-L6-v2"]},
    "chunking": {"methods": ["recursive"], "chunk_sizes": [500], "overlaps": [50]},
    "retrieval": {"retrievers": [{"type": "dense"}], "top_k": [5]},
    "queries_file": "configs/questions.example.json"
  }')
EXP_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['experiment_id'])")
echo "Experiment: ${EXP_ID}"

# 4. Poll until terminal
echo -n "Waiting for completion"
for i in $(seq 1 60); do
  STATUS=$(curl -sf "${SERVER_URL}/experiments/${EXP_ID}" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  case "$STATUS" in
    complete|partial) echo " ${STATUS}"; break;;
    failed|cancelled) echo " FAILED (${STATUS})"; exit 1;;
    *) echo -n ".";;
  esac
  sleep 5
done

# 5. Check chunks indexed
echo -n "Chunks in ES... "
COUNT=$(curl -sf "${ES_URL}/rpf-chunks-384/_count" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['count'])")
echo "${COUNT}"
[ "$COUNT" -gt 0 ] || { echo "FAIL: zero chunks indexed"; exit 1; }

echo "=== SMOKE PASS ==="
```

### 10-minute first-run script (draft)

```bash
#!/usr/bin/env bash
# scripts/first-run-es.sh — ES first run (10-min target on fast connection)
set -euo pipefail

echo "=== Elasticsearch First Run ==="
echo "Target: working experiment in ~10 minutes"
echo ""

# Prerequisites check
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker not installed"; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "ERROR: uv not installed (pip install uv)"; exit 1; }
docker info >/dev/null 2>&1 || { echo "ERROR: Docker not running"; exit 1; }

# Check Docker memory (Mac/Windows)
if [[ "$(uname)" == "Darwin" ]]; then
  MEM=$(docker info 2>/dev/null | grep "Total Memory" | awk '{print $3}')
  echo "Docker memory: ${MEM} (recommend ≥4 GiB for ES + run-state)"
fi

# Linux vm.max_map_count check
if [[ "$(uname)" == "Linux" ]]; then
  MAPCOUNT=$(cat /proc/sys/vm/max_map_count)
  if [ "$MAPCOUNT" -lt 262144 ]; then
    echo "ERROR: vm.max_map_count=${MAPCOUNT} (need ≥262144)"
    echo "Fix:   sudo sysctl -w vm.max_map_count=262144"
    exit 1
  fi
fi

# 1. Install deps
echo "[1/5] Installing Python dependencies..."
uv venv --quiet 2>/dev/null || true
source .venv/bin/activate
uv pip install -e ".[elasticsearch]" --quiet

# 2. Start ES
echo "[2/5] Starting Elasticsearch..."
./start-services.sh --elasticsearch-local

# 3. Wait for healthy
echo "[3/5] Waiting for ES + server health..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8001/healthz >/dev/null 2>&1; then
    echo "  Server healthy!"
    break
  fi
  sleep 2
done

# 4. Pre-download local model
echo "[4/5] Pre-downloading embedding model (~23 MB)..."
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>/dev/null

# 5. Run smoke config
echo "[5/5] Running smoke experiment..."
rag-params-finder run --config configs/elasticsearch/example-local.yaml

echo ""
echo "=== Done! Open http://localhost:5374 to view results ==="
```

---

## Part 6 — Embedding-Provider Matrix

### Supported combinations (READ, not RAN)

| Provider | Models | Dims | ES Index | Status |
|---|---|---|---|---|
| local | all-MiniLM-L6-v2 | 384 | `rpf-chunks-384` | READ: mapping exists |
| voyage | voyage-3.5-lite, voyage-3.5, voyage-context-3 | 1024 | `rpf-chunks-1024` | READ: mapping exists |
| sie | bge-m3, stella-v5 (dense) | 1024 | `rpf-chunks-1024` | READ: mapping exists |
| sie | splade-v3 (sparse) | 30522 | — | READ: **NOT SUPPORTED** (30522-dim not in SUPPORTED_DIMS) |
| doubleword | qwen3-embedding-8b | 1024 | `rpf-chunks-1024` | READ: mapping exists |

**Key gap:** SIE SPLADE-v3 (sparse, 30522-dim) is silently rejected by `mapping.py` SUPPORTED_DIMS check. This should produce a clear error message, not a silent dimension mismatch.

### Quantized mapping detection — PASS

`_reject_quantized()` at `elasticsearch_vector_store.py:299-304` correctly detects `bbq_hnsw` or `bbq_flat` mapping types and raises `ValueError` with a clear message. An 8.x cluster that was auto-upgraded to 9.x with quantized indexes will get a clear error.

### Partial writes on failure — P1

If embedding fails mid-batch (API rate limit, network error), chunks already indexed remain in ES. There is no cleanup/rollback. A retry re-indexes the full batch, creating duplicates (no upsert/dedup logic). The `experiment_id` filter prevents cross-experiment contamination but within one experiment, duplicate chunks inflate retrieval results.

---

## Part 8 — Additional Findings

### §1 Sample data missing from git — P0

**File:** `.gitignore:67` excludes `input_data/`

Every ES example config references `data_paths: ["input_data/pdfs/"]`. On a fresh clone, this directory does not exist. The first experiment fails immediately with `FileNotFoundError`.

**Fix:** Either include a small sample PDF in the repo (add `!input_data/pdfs/sample.pdf` to `.gitignore`), or change example configs to reference a URL or bundled test fixture.

### §2 Questions file schema mismatch — P1

**File:** `server/core/query_loader.py:58-73`

The code expects:
```json
{"personas": [{"id": "...", "questions": [...]}]}
```

But `docs/user-guide/configuration.md` and `CLAUDE.local.md` document:
```json
[{"persona_id": "...", "queries": [...]}]
```

The actual `configs/questions.example.json` uses the code format (with `personas`/`id`/`questions`), not the documented format. New users following docs will create the wrong format.

### §3 Config backend guard gap

`configs/elasticsearch/example-doubleword.yaml` has `database_provider: elasticsearch` (correct for the guard), but the header comment says to run with `--mongodb-local` which would set `VECTOR_STORE_BACKEND=mongodb`, causing a 422 mismatch. The guard catches this — but the user sees a confusing error after following the config's own instructions.

### §4 Static analysis results — PASS

- `ruff check .` → 0 errors
- `mypy server/ cli/` → 0 errors
- 36/37 tests pass (1 skipped: postgres integration)
- 77.78% coverage (above 70% floor)

---

## BLOCKED Items (require Docker / disposable VM)

| ID | What | Why blocked |
|---|---|---|
| L1 | Full ES live test suite | No Docker/ES available |
| D1 | Docker compose up/down cycle | Not disposable host |
| D2 | Data persistence across restarts | Not disposable host |
| P2 | stop-services.sh cleanup | Not disposable host |
| E1 | Live /healthz and /api/stores JSON | No running ES |
| J2 | Dashboard with ES data | No running ES |
| J3 | Cross-store score comparison | No running ES + Mongo/Postgres |
| N1 | Nightly CI job reproduction | No Docker |
| K2 | ARM / Apple Silicon image pull | No Docker |

---

## Appendix: All Findings by Priority

### P0 — Blockers (3)

1. **B1** — Bulk API errors silently swallowed (`elasticsearch_vector_store.py:109`)
2. **P1-pair** — `storage_mode.sh` rejects sqlite pairing for ES (`storage_mode.sh:374,382-383`)
3. **S1** — Sample PDF not in git; all example configs fail on fresh clone (`.gitignore:67`)

### P1 — Should Fix (12)

1. **B2** — No bulk batching; 10s timeout too short for large ingestion
2. **C1** — ES 8.x untested; version message misleading
3. **C2** — 401/403/429/503 not caught as actionable errors
4. **C3** — Partial chunk cleanup on failure (duplicates on retry)
5. **E2** — Provider matrix never executed (zero ES contract tests)
6. **E4** — Env var name drift (`stores.tsv` vs `settings.py`)
7. **J1** — No QUICKSTART Path E for Elasticsearch
8. **K1-a** — Config prerequisites say `--mongodb-local` (wrong)
9. **K1-b** — Atlas-specific comments in ES configs
10. **S2** — Sparse score comparability claim is false
11. **S3** — Questions file schema: docs vs code mismatch
12. **C5** — ES URL with embedded credentials logged in plaintext

### P2 — Known Limitations (4)

1. **R1** — `refresh: wait_for` performance characteristics undocumented
2. **R2** — Aggregation `terms.size: 100` cap
3. **R3** — `num_candidates` not capped at 10,000
4. **Boot** — No boot-time ES connectivity check
