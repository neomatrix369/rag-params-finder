# SLICE 01 — Skateboard

**MoSCoW:** MUST  
**Target time:** ~75 min  
**Status:** IN PROGRESS

## Goal

End-to-end RAG parameter sweep pipeline working with one chunker, one embedding model, one query. No rerank, no sweep expansion yet. Prove the architecture works.

## Acceptance criteria

- [ ] FastAPI boots at localhost:8001
- [ ] GET /healthz returns `{"ok": true}`
- [ ] MongoDB Atlas connection established
- [ ] 6 Atlas collections created (chunks, experiments, run_status, collections, queries, results)
- [ ] Vector index created on chunks.embedding (1024-dim, cosine similarity)
- [ ] POST /experiments accepts minimal YAML config
- [ ] Experiment runs as BackgroundTask
- [ ] Pipeline executes: PDF parse → RECURSIVE chunk → Voyage embed → Atlas write → query embed → DENSE search → write results
- [ ] CLI command `rag-params-finder run --config configs/example.yaml` submits successfully
- [ ] React dashboard ExperimentsScreen polls GET /experiments and renders one row
- [ ] README Quickstart section complete (judge can clone and run)

## Implementation Plan

### Phase 1: Server Foundation (~15 min)

**Files**:
- `server/__init__.py`
- `server/main.py` — FastAPI app, /healthz endpoint, CORS
- `server/models/enums.py` — ChunkingMethod, RetrievalMethod, Phase enums
- `server/models/config.py` — Pydantic ExperimentConfig
- `server/models/status.py` — RunStatus
- `server/models/results.py` — QueryResult
- `server/utils/logger.py` — Structured logging
- `server/db/atlas.py` — MongoDB connection

**Verification**: `uvicorn server.main:app --reload --port 8001` → http://localhost:8001/healthz

### Phase 2: MongoDB Atlas Setup (~10 min)

**Files**:
- `server/db/indexes.py` — Collection creation + vector index

**Tasks**:
1. Create 6 collections: chunks, experiments, run_status, collections, queries, results
2. Create vector index on chunks.embedding (1024-dim, cosine, filter by experiment_id + embedding_model)

**Verification**: Check Atlas UI for collections and vector index

### Phase 3: PDF Parsing + Chunking (~15 min)

**Files**:
- `server/core/pdf_parser.py` — pypdf wrapper
- `server/core/chunkers/__init__.py` — ChunkingMethod enum + dispatcher
- `server/core/chunkers/recursive.py` — LangChain RecursiveCharacterTextSplitter

**Verification**: Parse sample PDF, chunk with RECURSIVE, verify chunk count

### Phase 4: Voyage Embedding (~10 min)

**Files**:
- `server/core/embedder.py` — Voyage client singleton, embed_documents, embed_query

**Environment**:
- VOYAGE_API_KEY in .env

**Verification**: Embed 5 sample chunks, verify 1024-dim vectors returned

### Phase 5: Atlas Vector Store + Retrieval (~15 min)

**Files**:
- `server/core/retriever.py` — dense_search using Atlas $vectorSearch

**Tasks**:
1. Write chunks + embeddings to Atlas chunks collection
2. Query with dense search (top-20)
3. Return SearchResult objects

**Verification**: Store 5 chunks, query, verify top-K results

### Phase 6: Orchestrator (~10 min)

**Files**:
- `server/core/orchestrator.py` — run_experiment function (PDF → chunk → embed → store → query → results)
- `server/api/experiments.py` — POST /experiments, GET /experiments

**Tasks**:
1. Accept config via POST
2. Run orchestrator in BackgroundTask
3. Write experiment doc + run_status doc
4. Write results to results collection

**Verification**: POST config, check experiments + run_status + results collections

### Phase 7: CLI (~10 min)

**Files**:
- `cli/__init__.py`
- `cli/main.py` — Typer app + run command
- `cli/config_loader.py` — YAML parser
- `cli/api_client.py` — httpx client to server

**Verification**: `rag-params-finder run --config configs/example.yaml` → submission succeeds

### Phase 8: Frontend (~20 min)

**Files**:
- `frontend/package.json` — React 19, Vite 6, Tailwind, TypeScript
- `frontend/vite.config.ts`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/ExperimentsScreen.tsx` — Table with one experiment row
- `frontend/src/services/apiClient.ts` — Polling GET /experiments
- `frontend/src/types/index.ts` — Hand-mirrored enums

**Tasks**:
1. Install Tailwind locally (NOT CDN)
2. Create ExperimentsScreen with 0.5Hz polling
3. Display experiment_id, created_at, status columns
4. Lift Tailwind classes from predecessor (slate-900 bg, blue-600 primary)

**Verification**: `npm run dev` → http://localhost:5173 → see one row after submitting experiment

## Quick-Win cuts taken

- No reranking (Slice 2)
- No sweep expansion — single run only (Slice 3)
- No live status polling (Slice 4)
- No multiple queries — one hardcoded query (Slice 5)
- No --watch CLI flag (Slice 4)
- No recovery logic (Slice 10)
- No error handling beyond basic try/catch
- Minimal logging (print statements OK for Slice 1)

## Deferred to later slice

- Reranking (Slice 2)
- Sweep Cartesian product (Slice 3)
- Phase status tracking (Slice 4)
- Persona-based queries (Slice 5)
- Other chunkers (Slice 6)
- Other embedding models (Slice 7)
- SPARSE/HYBRID retrieval (Slice 8)
- ADRs + docs polish (Slice 9)
- Recovery (Slice 10)

## Decisions

| Decision | Why |
|---|---|
| pypdf over pdfminer.six | Simpler API, sufficient for text extraction |
| voyage-3.5-lite only | Cheapest Voyage model, add others in Slice 7 |
| RECURSIVE chunker only | Most common method, LangChain has it |
| BackgroundTasks not Celery | No queue infrastructure for MVP |
| DENSE-only retrieval | Simplify first slice, add SPARSE/HYBRID in Slice 8 |
| Hardcoded query | Defer persona JSON to Slice 5 |
| No phase tracking yet | Defer to Slice 4 when live status is added |

## Risks

| Risk | Mitigation |
|------|------------|
| Voyage API rate limits | Use voyage-3.5-lite (cheapest), small test PDF |
| Atlas vector index not ready | Wait for index build, check status endpoint |
| React 19 peer dep issues | Use --legacy-peer-deps if needed (predecessor pattern) |
| CORS issues | Configure FastAPI CORS middleware |

## Exit Criteria

All acceptance criteria checked ✅ AND:

- Server starts without errors
- CLI submits experiment successfully
- Dashboard renders experiment row
- MongoDB Atlas has 6 collections populated
- README Quickstart tested end-to-end
