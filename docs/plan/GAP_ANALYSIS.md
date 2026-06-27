# Gap Analysis
> ~2 min read

## Capability Gaps (PCTO vs Existing Codebase)

| Area | PCTO Requirement | What Exists | Gap | Severity | Target Slice |
|------|-----------------|-------------|-----|----------|--------------|
| Inference backend | SIE (self-hosted, Apache 2.0) | Voyage AI (closed API) + local sentence-transformers | `sie-sdk` not installed; no SIE provider in model registry | **Critical** | 21 |
| Corpus builder | Tavily (live web content) | PDF / static files via `pypdf` | `tavily-python` not installed; no corpus builder module | **Critical** | 21 |
| Experiment tracking | Aim (per-sweep run logging) | MongoDB storage only | `aim` not installed; no logging hook in orchestrator | **Critical** | 21 |
| Primary API endpoint | `POST /api/v1/sweep` | `POST /experiments` (different shape, different semantics) | New route + router prefix needed | **Critical** | 21 |
| Best-config lookup | `GET /api/v1/best-config?task=...` | None | New route; requires sweep history queryable by task | **Critical** | 21 |
| Health check | SIE + Tavily + MongoDB at `GET /health` | MongoDB only at `GET /healthz` | Extend existing health endpoint | Notable | 21 |
| SIE models in registry | bge-m3, stella-v5, splade-v3, qwen3-embedding-8b | Voyage + all-MiniLM-L6-v2 only | Add SIE provider + models to `model_registry.py` | **Critical** | 21 |
| SIE reranking | BGE-reranker via SIE `score` | Voyage reranker + CrossEncoder | New reranker path in `reranker.py`; SIE provider in registry | Notable | 22 |
| SPLADE v3 sparse | Via SIE `encode` (sparse output) | Atlas text search (BM25 workaround) | Separate sparse index for SPLADE output format | Notable | 22 |
| Experiment results by ID | `GET /api/v1/experiments/{id}` | `GET /experiments/{id}` (same semantics) | Route alias at `/api/v1` prefix | Minor | 22 |
| Ollama LLM | Context Compression, HyDE, Multi-Query, RAG-Fusion | None | Ollama client + Tier 2–3 retrieval methods | Notable | 23 |
| Evidently AI monitoring | Retrieval quality drift monitoring | None | Evidently integration, drift alerts | Minor | 23 |
| MCP server | `get_rag_config(task_description)` via Alpic.ai | None | MCP wrapper around `GET /api/v1/best-config` | Minor | 22 |

## What Is Already Sufficient (No Gap)

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI framework | ✅ | Runs on port 8001; add new router at `/api/v1` |
| MongoDB Atlas integration | ✅ | Collections, indices, connection pool all working |
| Voyage AI embeddings | ✅ | Stays as numeric baseline; not replaced |
| Dense/sparse/hybrid retrieval (Tier 1) | ✅ | Reused for SIE sweep runs |
| Orchestrator pipeline | ✅ | Extend to dispatch `sie` provider; add Aim logging hook |
| Chunking (fixed, token, sentence, semantic) | ✅ | Used as-is for Tavily corpus chunks |
| Docker Compose stack | ✅ | Add SIE container to `docker-compose.yml` in Slice 21 |
| CI / quality gates | ✅ | New tests added to existing `pytest` suite |

## Divergence Check (PCTO Spec ↔ Existing Tests ↔ Existing Code)

| Area | Spec says | Tests assert | Code does | Canonical source | Action |
|------|-----------|--------------|-----------|------------------|--------|
| Embedding provider | SIE + Voyage (both) | Voyage + local only | Voyage + local only | **PCTO spec** | Add SIE path — additive, no conflict |
| Corpus source | Tavily OR provided document | PDF / static only | PDF / static only | **PCTO spec** | Add Tavily path — additive |
| Experiment logging | Aim | MongoDB storage | MongoDB storage | **PCTO spec** | Add Aim alongside MongoDB |
| API surface | `/api/v1/sweep`, `/api/v1/best-config` | `/experiments` routes | `/experiments` routes | **PCTO spec** | New routes — no overlap |

**Result**: No conflicts detected. All PCTO additions are purely additive — no existing behaviour is changed or removed.
