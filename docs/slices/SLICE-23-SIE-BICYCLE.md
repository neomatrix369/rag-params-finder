<!-- file: docs/plan/slice-23-sie-bicycle.md -->

## Slice Workflow Header

Slice: 23 — SIE Bicycle — Ollama LLM + Tier 2–3 retrieval methods + Evidently AI drift monitoring

Files:
- server/core/ollama_client.py            # new: Ollama LLM wrapper for generation
- server/core/retrieval/hyde.py           # new: HyDE (SIE embeds; Ollama generates)
- server/core/retrieval/multi_query.py    # new: Multi-Query (Ollama generates variants)
- server/core/retrieval/rag_fusion.py     # new: RAG-Fusion (multi-query + RRF)
- server/core/retrieval/mmr.py            # new: MMR diversity retrieval (SIE encode only)
- server/core/retrieval/context_compress.py  # new: Context Compression (Ollama + SIE)
- server/models/enums.py                 # add Tier 2–3 retrieval method variants
- server/core/evidently_monitor.py        # new: Evidently AI drift monitor wrapper
- tests/test_tier3_retrieval.py          # GWT tests (mock Ollama, mock SIEClient)

Exit criteria:
  [ ] HyDE and Multi-Query both run end-to-end (SIE embeds, Ollama generates)
  [ ] Evidently AI shows score trends per SIE model
  [ ] Tier 2–3 methods gate behind llm_available flag in GET /health
  [ ] ./scripts/quality-gates.sh passes
  [ ] No prior tests regressed

Commit pattern:
feat(sie): add SIE Bicycle — Ollama Tier 2-3 methods, Evidently drift monitoring

- Wire Ollama for HyDE, Multi-Query, RAG-Fusion, Context Compression generation
- MMR diversity retrieval via SIE encode (no LLM needed)
- Evidently AI drift monitoring for SIE model quality over time

---

## Slice 23 — SIE Bicycle [Could — Post-Hackathon]

### Branch
`slice/23-sie-bicycle`
Create from `main` after Slice 22 is merged.

### Prerequisites (outside code)
- Ollama installed: `brew install ollama` (Mac) or official installer
- LLM pulled: `ollama pull llama3.2` (3.2 is small, generation-capable, zero API cost)
- Verify: `ollama run llama3.2 "Hello"` returns output

### Spec (GWT)

```
Scenario: Ollama client generates text
  Given Ollama is running at http://localhost:11434 with llama3.2 pulled
  When generate(model="llama3.2", prompt="Write a hypothesis about: embeddings") is called
  Then a non-empty string is returned

Scenario: Ollama unavailable — Tier 3 methods skipped gracefully
  Given Ollama is not running
  When GET /health
  Then response includes llm_available=false
  And POST /api/v1/sweep with retrieval_methods=["hyde"] returns HTTP 422 with message "LLM not available"

Scenario: HyDE retrieval — Ollama generates, SIE embeds
  Given Ollama running, SIE running, MongoDB indexed
  When POST /api/v1/sweep {"topic":"AI agents","retrieval_methods":["hyde"]}
  Then sweep completes and result includes retrieval_method="hyde"

Scenario: Multi-Query retrieval — Ollama generates variants, SIE embeds
  Given Ollama running, SIE running
  When POST /api/v1/sweep {"topic":"AI agents","retrieval_methods":["multi-query"]}
  Then sweep completes with retrieval_method="multi-query"

Scenario: MMR diversity retrieval — SIE encode only, no LLM
  Given SIE running
  When POST /api/v1/sweep {"topic":"AI agents","retrieval_methods":["mmr"]}
  Then sweep completes with retrieval_method="mmr" (does not require llm_available=true)

Scenario: Evidently drift monitor detects score drop
  Given Evidently AI configured with a reference dataset of SIE model scores
  When a new sweep produces scores > 15% below the reference window average
  Then a drift alert is logged (to server log / Aim / Evidently report)
```

### Before-Checks [GATE]
- [ ] Branch `slice/23-sie-bicycle` created from latest `main` (Slice 22 merged and gate PASSED)
- [ ] Ollama installed and `llama3.2` pulled: `ollama run llama3.2 "ping"` returns output
- [ ] SIE Docker running
- [ ] `./scripts/quality-gates.sh` passes

### TDD Execution

1. Write failing tests in `tests/test_tier3_retrieval.py`. Mock `OllamaClient.generate()` and `SIEClient.encode()`.
2. RED — all new tests fail.
3. GREEN — implement Ollama client + HyDE + Multi-Query (minimum passing).
4. Add MMR (no LLM dependency — simpler, implement after HyDE/Multi-Query).
5. Add RAG-Fusion (Multi-Query + RRF fusion — builds on Multi-Query).
6. Add Context Compression (Ollama summarises retrieved chunks).
7. Wire Evidently AI drift monitor.
8. Refactor: extract shared `_embed_and_retrieve()` primitive used by all Tier 3 methods.
9. Full suite — no regressions.

### Implementation Steps

1. **Write `server/core/ollama_client.py`** — `OllamaClient(base_url).generate(model, prompt) -> str`; raises `RuntimeError` if Ollama unreachable
2. **Add `llm_available` flag to `GET /health`** — probe `http://localhost:11434/api/tags`; gate Tier 3 methods on this flag
3. **Write retrieval modules** (each independently importable):
   - `hyde.py` — generate hypothetical doc (Ollama) → embed (SIE) → retrieve
   - `multi_query.py` — generate N query variants (Ollama) → embed each (SIE) → merge results
   - `rag_fusion.py` — multi-query variants → RRF fusion (reuse existing RRF logic)
   - `mmr.py` — embed query (SIE) → MMR diversity filter over candidate set
   - `context_compress.py` — retrieve chunks → compress to relevant passage (Ollama)
4. **Add Tier 2–3 method variants to `RetrievalMethod` enum** in `server/models/enums.py`
5. **Wire retrieval dispatch in orchestrator** — gate Tier 2–3 on `llm_available`; skip with warning if unavailable
6. **Write `server/core/evidently_monitor.py`** — wrap Evidently `Report` + `TestSuite`; log drift alerts at sweep end
7. **Write tests** for all GWT scenarios
8. **Run `./scripts/quality-gates.sh`**

### After-Checks [GATE]
- [ ] HyDE and Multi-Query run end-to-end in a real sweep (manual smoke test)
- [ ] MMR runs without Ollama (confirmed via test with llm_available=false)
- [ ] Evidently drift report generated after ≥ 2 sweep runs
- [ ] All GWT scenarios covered by passing tests
- [ ] Quality gates pass
- [ ] Doc audit → YES: update PROGRESS.md (Slice 23 → ✅ COMPLETE); update `CLAUDE.local.md` with Ollama setup instructions
- [ ] Security audit → NO (Ollama is local; no new external API surface beyond existing pattern)
- [ ] Self-review + `/code-review` + `/clean-commit` + PR

### Gate Status
PENDING

### Expected Outcomes
- HyDE and Multi-Query both run; SIE handles embedding, Ollama handles generation — zero API cost
- MMR diversity retrieval available without LLM dependency
- Evidently AI shows score trends per SIE model; drift alerts fire when score drops > 15% over 7-day window
- `llm_available` flag in health check makes Tier 3 availability transparent to callers

### Session Metrics

| Metric | Planning phase | Execution phase |
|--------|---------------|-----------------|
| Model | claude-sonnet-4-6 | claude-sonnet-4-6 |
| Tokens — input / output (est.) | — / — | — / — |
| Turns | — | — |
| Context sources loaded | TRAIL.md, slice-21, slice-22 | + touched source files |
| Context pressure | none | — |
| Notes | MCP explicitly excluded from all PCTO slices | — |
