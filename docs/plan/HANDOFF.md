# Handoff
> ~1 min read

_Stub — written at end of final slice._

## What Was Built

_(populated as slices complete)_

## Pending / Future

| Item | Reason Deferred | MoSCoW |
|------|-----------------|--------|
| Slice 23 — Ollama + Tier 2–3 + Evidently AI | Post-hackathon; depends on Ollama install and Evidently AI setup | Could |
| Slice 10 — Run recovery | Boot reconciliation already handles main case; lowest urgency | Could |
| MCP deployment to Alpic.ai | Post-hackathon Combo C; depends on Alpic.ai account setup | Could |
| Full SIE model grid sweep (Stella v5, Qwen3-Embedding-8B) | Could/C4 in PCTO — systematic sweep after core integration proves stable | Could |

## Known Risks

- SIE first-call latency: first `encode` call per model downloads weights from HuggingFace (seconds). Warm-up call in `/health` endpoint mitigates.
- Atlas M0 storage deadlock: active risk until Slice 19 (storage quota guard) ships. Workaround: delete complete experiments to free space.
- Tavily rate limits during parallel corpus builds: cache Tavily results by topic in MongoDB to avoid repeated API calls.
- `embedder.py` currently acts as both Voyage implementation and provider router. Slice 21 extracts the router to `embedder_factory.py` — any code importing `embed_documents` from `embedder.py` directly (outside the orchestrator) must be updated at that point.
