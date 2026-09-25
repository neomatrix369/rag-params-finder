# ADR-005: DoubleWord Embedding Provider — Batch-First Architecture

**Status**: Proposed
**Date**: 2026-09-25
**Deciders**: owner (@neomatrix369)
**Related slices**: 48A, 48B, 48C, 48D

---

## Context

`rag-params-finder` supports multiple embedding providers (Local sentence-transformers, Voyage AI, SIE). All existing providers are **synchronous**: the sweep executor calls `embed_docs_fn(chunks, model)` and receives vectors back immediately within the same thread.

DoubleWord (DW) provides the `Qwen/Qwen3-Embedding-8B` model at significantly lower cost via a **batch async API**: callers upload a JSONL file, receive a `batch_id`, poll until the job completes (minutes to 24 h), then download the output vectors. There is also a synchronous `/v1/embeddings` endpoint (48D, Could) but it is priced at the highest tier and limited.

The sweep executor has **one worker** (`ThreadPoolExecutor(max_workers=1)`). Waiting inside a run for a batch job to complete would block every other experiment for hours.

### T0 Spike Results
> **⚠️ To be filled in after running `scripts/spikes/dw_embed_spike.py`**

| Check | Question | Result |
|-------|----------|--------|
| V3 | Batch API `/v1/embeddings` endpoint exists? | ❌ / ✅ — **HARD GATE** |
| V1 | `dimensions=1024` honoured in output? | pending |
| V2 | Default output dimensions? | pending |
| V4 | Output line shape (`response.body.data[0].embedding`, `usage.prompt_tokens`)? | pending |
| V5 | `input` per line is a list? | pending |
| V6 | `completion_window="1h"` accepted for embeddings? | pending |
| V9 | Exact model id for `Qwen/Qwen3-Embedding-8B`; query prefix format? | pending |
| V11 | `/jobs` async API supports embeddings? (record only) | pending |

**If V3 = NO**: pivot — promote 48D (realtime) to Must, run before 48A–C, record in DECISIONS.

---

## Decision

Adopt a **batch-first, async architecture** for DoubleWord:

1. **Pre-embed phase** (experiment level, not run level): at experiment submission, `defer_async_embeddings()` plans all document and query texts across the declared sweep space, uploads JSONL from memory, creates batch jobs via the DW API, and persists checkpoint records to `.rpf_state/doubleword_batches.json`. The sweep thread is released immediately.

2. **Embedding factory (cache-reader only)**: `embedder_factory.get_embedder("doubleword")` returns sync callables that read from the SQLite cache (`embedding_cache.py`). A cache miss raises `DoublewordCacheMissError` — it never silently embeds or stores a partial corpus. This preserves the factory's synchronous contract for existing orchestrator code.

3. **Detached asyncio watcher**: a single `asyncio.Task` started in FastAPI `lifespan` polls all pending batch IDs, fills the cache via `asyncio.to_thread`, and schedules run execution when all jobs for an experiment are complete. Supervised with exponential backoff restart.

4. **SQLite embedding cache** (`.rpf_cache/embeddings.sqlite`, WAL mode): content-addressed by `sha256(json([text, provider, model, dim, instruction, role]))`. Shared across sweeps. One shared connection; Python's `sqlite3` serialises writes internally; WAL allows concurrent reads. No separate asyncio lock needed.

5. **Checkpoint store** (`.rpf_state/doubleword_batches.json`): `threading.Lock` + atomic `os.replace`. Both the watcher (via `asyncio.to_thread`) and orchestrator threads go through the same lock. Enables restart-safe resume: same `batch_id` is polled after server reboot — no resubmission.

---

## Alternatives Considered

### A — Realtime-first (synchronous `/v1/embeddings`)
The realtime endpoint exists but is priced highest and has lower throughput limits. Docextract (reference implementation) never used it. Rejected: cost penalty, limited throughput, and the realtime endpoint's availability for embeddings is unverified (V3 spike).

### B — Poll inside the sweep run (blocking)
Wait for batch completion inside `_run_single`. Rejected: the single sweep executor would be blocked for hours, preventing any other experiment from running.

### C — Autobatcher (DW client abstraction)
DoubleWord provides an `autobatcher` helper. Rejected (DW_FB #7): autobatcher hides `batch_id`, making checkpoint/resume impossible. Restart safety requires explicit `batch_id` control.

### D — Generic `requires_env` schema field
A registry flag marking providers as "requires pre-submission". Rejected (#192): YAGNI — only one async provider currently. If a second async provider appears, extract `EmbeddingStrategy` (see DECISIONS #235 escape hatch).

---

## Consequences

### Positive
- Sweep worker is never blocked by DW batch latency; other experiments proceed normally.
- Restart-safe: checkpoints survive server crashes; same batch is polled after reboot.
- Cache is shared across sweeps: if the same text/model pair appears in two experiments, it is embedded once.
- 48C (MRL axes) derives lower-dim vectors from the cached max-dim output — no second paid embedding pass.

### Negative / Trade-offs
- New infrastructure: SQLite cache, checkpoint store, watcher task, pre-embed orchestration (~5 new modules, ~9–11 h in 48A).
- Orchestrator gains a second provider-aware branch (`defer_async_embeddings`; the first is the `"local"` parallelism kwarg). Documented YAGNI seam; escape hatch: `EmbeddingStrategy` if pattern repeats (DECISIONS #235).
- `openai` SDK added as a dependency (pinned major; pip-audit required before merge — DECISIONS #210).
- Cache durability: Docker compose named volume required. If `.rpf_cache/` is deleted, vectors are not recoverable from DW servers — experiments must be re-run. See `doubleword-setup.md` restart-safety section.
- Single model risk: if `Qwen/Qwen3-Embedding-8B` is withdrawn from DW, the unavailable-model registry provides graceful degradation (422 at submit); no auto-fallback to Voyage equivalents (YAGNI).

### Neutral
- Storage and retrieval ports (`StorageBackend`, `RetrieverBackend`) are unchanged.
- The `embedding_model` mandatory filter rides the existing infrastructure; 48C's composite identity (`model#d<dim>`) extends it without new filter fields; pre-48C records are migrated at boot (see § Embedding Identity).

---

## Mixed-Provider Axis (48A S1)

Before 48A, `EmbeddingConfig.provider` was a required single value for the entire experiment. 48A makes it optional; when omitted, each model's provider is derived from the registry via `model_registry.provider_for_model(model_id)`. This enables one sweep to compare Local / Voyage / DoubleWord models directly.

Existing single-provider configs are byte-identical after the change (regression lock tested).

## Embedding Identity (48C)

Owner decisions 2026-09-25 (DECISIONS #238, #239). **Decided, not yet implemented.**

- Stored `embedding_model` for DoubleWord documents is `Qwen/Qwen3-Embedding-8B#d<dim>`, so vectors of different MRL sizes never share a retrieval filter.
- Records written before 48C (plain id) are rewritten once at server boot to `#d<dim>`, with `<dim>` read from the stored vector. The migration covers `chunks`, `run_status` and `results` on both backends, is idempotent, and runs before orphan reconciliation and the watcher. A single exact-match identity filter is kept; no dual-identity query path.
- Postgres gains an `embedding_512` column + HNSW index (additive `ADD COLUMN IF NOT EXISTS`), so the `{384, 512, 1024}` allowlist is backed by storage.

---

## References
- Reference implementation: `playgroup_202602_docextract` → `llm_doubleword.py`, `extractor.py::_run_all_doubleword`, `DW_FB.md`
- [`BRIEF-doubleword-embedder.md`](../plan/BRIEF-doubleword-embedder.md) (full design brief + reconciliation table)
- Slices: [48A](../plan/slices/08-embedding-providers/SLICE-48A-DOUBLEWORD-BATCH-PROVIDER.md) · [48B](../plan/slices/08-embedding-providers/SLICE-48B-DOUBLEWORD-COST-HARDENING.md) · [48C](../plan/slices/08-embedding-providers/SLICE-48C-DOUBLEWORD-MRL-INSTRUCTION-AXES.md) · [48D](../plan/slices/08-embedding-providers/SLICE-48D-DOUBLEWORD-REALTIME-MODE.md)
- ADR-002 (Voyage + Local providers) — the mixed-provider axis extension lives in this ADR (§ Mixed-Provider Axis), not in ADR-002
