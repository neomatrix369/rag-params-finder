# Handoff
> ~1 min read
>
> **Stub** — pre-slice planning notes. Slice 21 implementation details live in [SLICE-21-SIE-SKATEBOARD.md](../slices/SLICE-21-SIE-SKATEBOARD.md) and [PROGRESS.md](../slices/PROGRESS.md).

_Stub — written at end of final slice._

## What Was Built

### Slice 21 — SIE Skateboard ✅ (2026-06-27 → 2026-06-29)

**Core deliverables:**

- `server/core/embedder_factory.py` — single dispatch point for all embedding providers (voyage/local/sie); orchestrator no longer does provider `if/elif`
- `server/core/sie_embedder.py` — SIE provider: BGE-M3 (1024-dim dense), Stella-v5 (1024-dim dense), SPLADE-v3 (30522-dim learned sparse); remote gateway via `SIE_ENDPOINT` + `SIE_API_KEY`; batched encode with preflight healthcheck; cooperative cancel support
- `server/core/aim_logger.py` — Aim experiment run logging (no-op on any failure — non-fatal)
- `server/api/sweep.py` — `POST /api/v1/sweep` Tier 1 ranked sweep; caller supplies `corpus: list[str]`; falls back to topic string when empty; `GET /health` extended with `sie` status and `version`
- `configs/example-mongodb-sie.yaml` — full CLI sweep config (120 runs: bge-m3 + stella-v5 + splade-v3 × all chunking methods × all retrieval methods)
- 15 new tests across `test_sie_embedder.py`, `test_embedder_factory.py`, `test_sweep_endpoint.py`, `test_config_examples.py`

**Refinements during slice (post 2026-06-27):**

- Renamed `SIE_BASE_URL` → `SIE_ENDPOINT`; added `SIE_API_KEY` for remote gateway auth
- Added SIE preflight (health check before encode) and cooperative cancel
- Fixed SIE encode batching for large corpora
- Added Atlas search index preflight gating on `POST /api/v1/sweep`
- Clarified remote gateway (default) vs optional self-hosted Docker path in docs

### Slices 25 + 25B — Atlas Local Dev Mode + Backend Switching ✅ (2026-06-29)

**Core deliverables:**

- `docker-compose.yml` — added `mongodb-local` service under `profiles: ["local-atlas"]`; `mongodb_local_data` named volume
- `docker-compose.local-atlas.yml` — **NEW** overlay: server `MONGODB_URI` → `mongodb-local:27017`; `MONGODB_STORAGE_LIMIT_MB=0`; `depends_on: mongodb-local`
- `server/db/indexes.py` — `bootstrap_indexes()` detects non-Atlas URI and auto-provisions all vector + text search indexes on boot (no Atlas UI, no M0 3-index quota)
- `scripts/local-atlas.sh` — **NEW** standalone container manager: `start|stop|reset|status`; waits for healthy; prints connection string
- `start-services.sh` — `--local` / `RAG_LOCAL_ATLAS=1` flag; compose overlay + profile auto-applied; cloud URI validation skipped in local mode; port 27017 conflict-checked; CLI URI printed on success
- `docs/user-guide/local-atlas-setup.md` — **NEW** full quick-start: Docker stack, host dev loop, comparison table, switching reference

**What it solves:** Atlas M0 512 MB ceiling was blocking large local sweeps (incident 2026-05-23: 515 MB used → all writes blocked). Local Atlas has no storage quota, supports identical `$vectorSearch` and `$search` syntax — zero changes to `retriever.py` or `indexes.py` query paths.

## Pending / Future

| Item | Reason Deferred | MoSCoW |
|------|-----------------|--------|
| Slice 23 — Ollama + Tier 2–3 + Evidently AI | Post-hackathon; depends on Ollama install and Evidently AI setup | Could |
| Slice 10 — Run recovery | Boot reconciliation already handles main case; lowest urgency | Could |
| MCP deployment to Alpic.ai | Post-hackathon Combo C; depends on Alpic.ai account setup | Could |
| Full SIE model grid sweep (Stella v5, Qwen3-Embedding-8B) | Could/C4 in PCTO — systematic sweep after core integration proves stable | Could |

## Known Risks

- SIE first-call latency: first `encode` call per model downloads weights from HuggingFace (seconds). Warm-up call in `/health` endpoint mitigates.
- Atlas M0 storage deadlock: **mitigated for local dev** by Slice 25 — `./start-services.sh --local` runs against `mongodb-atlas-local` with no storage ceiling. Cloud production risk remains until Slice 19 (storage quota guard) ships; workaround: delete complete experiments to free space.
- `embedder.py` provider router: resolved in Slice 21 — `embedder_factory.py` is now the single dispatch point. `embedder.py` exports `embed_docs_voyage` / `embed_query_voyage` only.
