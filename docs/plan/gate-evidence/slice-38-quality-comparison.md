# Slice 38 — Local dual-backend quality + latency comparison

**Status:** MEASURED — both local sides `complete`
**Evidence state:** VERIFIED (`mongodb-local` + `postgres-local`)
**Mode scope:** `mongodb-local` + `postgres-local` **only** (hosted `postgres-cloud` production-claim matrix → Slice 43 residuals)
**Backend model:** Mongo and Postgres are **independent** engines (DECISIONS **#129**) — cross-DB rank/hit mismatch is expected and **not** a fail-safe or cutover blocker
**Default:** stays `mongodb` until an **explicit** flip decision; this artifact informs that choice, it does not treat one DB as the other’s safety net
**Decisions:** #114 (QUERYING `elapsed_ms` ≤2×), #115 (384-dim local baseline), #129 (independent backends), #93 (Lucene vs `ts_rank` drift context)

---

## Gate summary (2026-07-26)

| Gate | Result | Evidence |
|---|---|---|
| Latency (QUERYING median+max ≤2×) | **PASS** | Gate-set median 10 515 ≤ 2×9 419; max 23 201 ≤ 2×18 532 |
| Rank overlap (top-1/3/5) | **recorded (informational)** | Overall top-3 **45.7%** — dense **92.9%**, hybrid **43.5%**, sparse **0.7%**. Different sparse engines (Atlas BM25 vs pg `tsvector`) → scores/hits need not match (#129) |
| Engine independence | **PASS (#129)** | Both grids ran to `complete` on their own storage; operator picks engine via flags/env |

---

## Snapshot

| Field | Value |
|---|---|
| Snapshot date | **2026-07-26** |
| Comparison pair | Both `complete` (mirrored 120-run grids) |
| Secrets | Redacted — no URIs, passwords, or API keys. Host: `localhost` only. Env vars by **name**: `MONGODB_URI`, `DATABASE_URL`, `STORAGE_BACKEND`, `SERVER_URL` |

### Configs

| Side | Config path | Stem |
|---|---|---|
| **mongodb-local** | `configs/mongodb/example-local-parallel.yaml` | `example-mongodb-local-parallel` |
| **postgres-local** | `configs/supabase/example-local-parallel.yaml` | `example-supabase-local-parallel` |

### Corpus

- Path: `./input_data/pdfs/The_Federal_Pell_Grant_Program.pdf`
- Size: ~471 KiB (482 216 bytes)
- Embedding: `provider: local`, model `all-MiniLM-L6-v2` (384-dim)

### Query set

- File: `./configs/questions.example.json`
- Personas: 8 · Questions: **77**

### Mongo experiment

| Field | Value |
|---|---|
| `experiment_name` | `example-mongodb-local-parallel_20260726-185445` |
| `experiment_id` | `1a16eaff-bab2-4672-9503-aafcbcb1630e` |
| `storage_mode` | `mongodb-local` |
| Status | `complete` (120/120 runs, 0 failed) |
| Created → completed (UTC) | `2026-07-26T18:54:45Z` → `2026-07-26T19:20:44Z` (~26 min wall) |
| Grid | 1 model × 5 chunk methods × 3 sizes × 2 overlaps × 4 retrievers = **120** |
| Chunking | `fixed`, `recursive`, `token`, `sentence`, `semantic` · sizes `[256, 512, 1024]` · overlaps `[50, 100]` |
| Retrievers | `dense`, `sparse`, `hybrid`, `cross_encoder` (local MiniLM) |
| Parallelism | 4 |
| Result rows | 9240 (= 120 × 77) |
| Chunks stored | 60 340 (~117 MB db-stats) |
| Server git (at run) | `0f6ba2d` on `slice/38-cutover-adr-004` |
| `/healthz` | `storage_backend=mongodb`, `storage_mode=mongodb-local`, `mongodb=ok` |

### Postgres experiment (twin)

| Field | Value |
|---|---|
| `experiment_name` | `example-supabase-local-parallel_20260726-204016` |
| `experiment_id` | `9ab49abc-e989-4724-b15f-5777237bfdd6` |
| `storage_mode` | `postgres-local` |
| `database_provider` | `postgres` (YAML label `supabase`) |
| Status | `complete` (120/120 runs, 0 failed) |
| Created → completed (UTC) | `2026-07-26T20:40:16Z` → `2026-07-26T21:10:15Z` (~30 min wall) |
| Grid | Same as Mongo — **120** runs · parallelism **4** |
| Result rows | 9240 |
| Server git (at run) | `c004369` on `slice/38-cutover-adr-004` |
| `/healthz` | `storage_backend=postgres`, `storage_mode=postgres-local`, `postgres=ok` |

Non-comparable Postgres rows (`1903dc76…` Slice 37 smoke; `dd107437…` Slice 43 16-run) were **not** used for overlap.

---

## Dense / sparse / hybrid (both sides)

Per-retriever result coverage (77 queries × 30 chunking combos = 2310 rows each):

| Retriever | Runs | Mongo nonempty / empty | Postgres nonempty / empty |
|---|---:|---:|---:|
| dense | 30 | 2175 / 135 | **2310 / 0** |
| sparse | 30 | 2310 / 0 | **81 / 2229** |
| hybrid | 30 | 2310 / 0 | **2310 / 0** |
| cross_encoder (secondary) | 30 | 2131 / 179 | 2310 / 0 |

**Note:** Postgres sparse returned hits on **81/2310** rows here vs Mongo sparse **2310/2310**. Under #129 that is an independent-engine observation (BM25 vs `tsvector`), not a requirement that the two DBs agree. Optional later tuning of Postgres sparse is separate from this comparison close-out.

---

## Rank overlap (Mongo ↔ Postgres)

**Method:** For each matched `(retrieval, chunking_method, chunk_size, overlap, query_text, persona_id)` pair, compare ordered top-k chunk **texts** (SHA1 of whitespace-normalized text; chunk IDs are run-scoped and not cross-backend).
**Metric:** mean `|A∩B| / k` over 6930 matched pairs (2310 per dense/sparse/hybrid).

| Scope | top-1 | **top-3** | top-5 |
|---|---:|---:|---:|
| dense | 92.8% | **92.9%** | 92.9% |
| sparse | 1.4% | **0.7%** | 0.5% |
| hybrid | 33.5% | **43.5%** | 48.5% |
| **all (dense+sparse+hybrid)** | 42.6% | **45.7%** | 47.3% |

NDCG: not computed (optional).

---

## Latency — QUERYING `elapsed_ms` (DECISIONS #114)

**Method:** `run_status.elapsed_ms` is cumulative and overwritten at `COMPLETE`, so QUERYING duration is **derived from orchestrator logs**:
`QUERYING_ms = complete_elapsed_ms − querying_start_elapsed_ms`.

### mongodb-local

| Retriever | n | median (ms) | max (ms) |
|---|---:|---:|---:|
| dense | 30 | **10 187** | **16 919** |
| sparse | 30 | **2 963** | **4 310** |
| hybrid | 30 | **13 920** | **18 532** |
| **dense+sparse+hybrid (gate set)** | **90** | **9 419** | **18 532** |

Secondary: cross_encoder QUERYING median **81 183** / max **227 654** ms.

### postgres-local

| Retriever | n | median (ms) | max (ms) | vs Mongo median / max |
|---|---:|---:|---:|---|
| dense | 30 | **11 860** | **18 812** | 1.16× / 1.11× |
| sparse | 30 | **940** | **2 653** | 0.32× / 0.62× |
| hybrid | 30 | **11 646** | **23 201** | 0.84× / 1.25× |
| **dense+sparse+hybrid (gate set)** | **90** | **10 515** | **23 201** | **1.12× / 1.25×** |

Secondary: cross_encoder QUERYING median **92 990** / max **242 193** ms.

**Latency gate:** PASS — Postgres gate-set median ≤ 2× Mongo median **and** Postgres max ≤ 2× Mongo max.

---

## Equivalence / comparison reading (DECISIONS #129)

Historical thresholds (≥80% PASS / ≥50% CONDITIONAL) remain useful **labels** for how close the rankings were; they are **not** hard blockers between independent backends.

| Label | Threshold (historical) | Measured | Reading under #129 |
|---|---|---|---|
| Dense | ≥80% top-3 | **92.9%** | Strong agreement on dense path |
| Hybrid | ≥50% / ≥80% | **43.5%** | Expected drift (RRF + sparse mix) |
| Sparse | — | **0.7%** | Different sparse engines; do not require match |
| Overall | ≥80% / ≥50% | **45.7%** | Informational aggregate only |

**Decision:** Comparison artifact **complete** for Slice 38 local evidence. Default remains `STORAGE_BACKEND=mongodb` until an **explicit** flip is recorded — that is a product choice informed by latency PASS + per-method notes, not by forcing Mongo/Postgres stats to align.

---

## Follow-ups (optional)

1. Postgres sparse hit-rate tuning (`tsvector` / tokenization) — product quality on Postgres alone, not cross-DB parity.
2. Explicit default-flip decision (if/when desired) + finalize `slice-38.json` CI conclusions.

---

## Engine switch (ops)

Two-command Mongo path (hostile leftover `.env` included):

```bash
./start-services.sh --mongodb-local
rag-params-finder run --config configs/mongodb/example-local-parallel.yaml
```

Two-command Postgres path:

```bash
./start-services.sh --postgres-local
rag-params-finder run --config configs/supabase/example-local-parallel.yaml
```

Secrets stay in env vars — never paste URIs into this file.
