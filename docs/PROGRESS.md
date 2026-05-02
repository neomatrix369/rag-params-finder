# rag-params-finder — Build Progress

**Last Updated**: 2026-05-02 16:30  
**Current**: Slice 1 ✅ BUILT (pending verification) | Next: Slice 2 📋 PLANNED

---

## Quick Status

| Slice | Status | Time Target | Notes |
|-------|--------|-------------|-------|
| 1 — Skateboard | ✅ BUILT | ~75 min | Code complete, awaiting .env setup + Atlas vector index + test PDF |
| 2 — Rerank | 📋 PLANNED | ~20 min | Voyage rerank-2.5-lite integration |
| 3 — Sweep expansion | 📋 PLANNED | ~25 min | Cartesian product of runs ⭐ CORE FEATURE |
| 4 — Live status + LiveRunScreen | 📋 PLANNED | ~30 min | Phase tracking + polling |
| 5 — Multiple queries from persona JSON | 📋 PLANNED | ~20 min | Loop over persona questions |

**Legend**: 📋 PLANNED | 🔨 IN PROGRESS | ✅ BUILT | ✔️ COMPLETE

---

## Slice 1: Skateboard ✅

**Status**: ✅ BUILT (pending verification) | **Started**: 2026-05-02 | **Completed**: 2026-05-02 | **Target**: ~75 min

### Goal
End-to-end pipeline working with one chunker (RECURSIVE), one embedding model (voyage-3.5-lite), one query, no rerank, no sweep.

### Acceptance Criteria (Code Complete)
- [x] FastAPI boots; `/healthz` returns ok — **Code ready** (needs .env)
- [x] Atlas connection works; 6 collections + vector index exist — **Code ready** (needs manual vector index in Atlas UI)
- [x] `POST /experiments` accepts a minimal config and runs in BackgroundTask — **Code complete**
- [x] Pipeline: parse PDF → RECURSIVE chunker → Voyage embed → Atlas write → Voyage query embed → DENSE search → write results — **Code complete**
- [x] CLI submits and exits cleanly (no `--watch` polling yet) — **Code complete**
- [x] Dashboard ExperimentsScreen renders ONE row from `/experiments` — **Code complete**
- [x] README has Quickstart section (judge can run locally) — **Complete**

### Verification Pending
- [ ] Live test with real .env (VOYAGE_API_KEY + MONGODB_URI)
- [ ] Atlas vector index created manually
- [ ] Sample PDF added to `papers/sample.pdf`
- [ ] End-to-end run: CLI submit → server execute → dashboard display

### Files to Create
**Server**:
- `server/__init__.py`
- `server/main.py` — FastAPI app + /healthz
- `server/api/experiments.py` — POST /experiments, GET /experiments
- `server/core/pdf_parser.py` — pypdf wrapper
- `server/core/chunkers/__init__.py` — Enum + dispatcher
- `server/core/chunkers/recursive.py` — LangChain RecursiveCharacterTextSplitter
- `server/core/embedder.py` — Voyage client singleton
- `server/core/orchestrator.py` — Per-run pipeline executor
- `server/models/enums.py` — ChunkingMethod, RetrievalMethod, Phase
- `server/models/config.py` — Pydantic config models
- `server/models/status.py` — RunStatus model
- `server/models/results.py` — Result models
- `server/db/atlas.py` — MongoDB client + collection helpers
- `server/db/indexes.py` — Vector index creation
- `server/utils/logger.py` — Structured logging

**CLI**:
- `cli/__init__.py`
- `cli/main.py` — Typer app + `run` command
- `cli/config_loader.py` — YAML parser
- `cli/api_client.py` — HTTP client to server

**Frontend**:
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/ExperimentsScreen.tsx`
- `frontend/src/services/apiClient.ts`
- `frontend/src/types/index.ts` — Hand-mirrored enums + types

**Configs**:
- `configs/example.yaml`
- `configs/questions.example.json`

**Docs**:
- `docs/slices/SLICE-01-SKATEBOARD.md`
- `docs/ARCHITECTURE.md` (brief)

### Quick-Win Cuts
- No reranking (Slice 2)
- No sweep expansion (Slice 3)
- No live status tracking (Slice 4)
- No multiple queries (Slice 5)
- No recovery logic (Slice 10)
- No --watch CLI flag (Slice 4)

### Verification
```bash
# Server
uvicorn server.main:app --reload
curl http://localhost:8000/healthz

# CLI
rag-params-finder run --config configs/example.yaml

# Dashboard
cd frontend && npm run dev
```

### Files Created (53 total)

**Foundation** (7):
- pyproject.toml, .env.example, .gitignore, README.md
- docs/PROGRESS.md, docs/ARCHITECTURE.md, docs/slices/SLICE-01-SKATEBOARD.md

**Server** (20):
- server/{__init__.py, main.py, utils/logger.py}
- server/models/{enums.py, config.py, status.py, results.py}
- server/db/{atlas.py, indexes.py}
- server/core/{orchestrator.py, pdf_parser.py, embedder.py, retriever.py}
- server/core/chunkers/{__init__.py, recursive.py, fixed.py, token.py, sentence.py, semantic.py}
- server/api/experiments.py

**CLI** (4):
- cli/{__init__.py, main.py, config_loader.py, api_client.py}

**Frontend** (13):
- frontend/{package.json, vite.config.ts, tailwind.config.js, postcss.config.js, index.html, tsconfig.json, tsconfig.node.json}
- frontend/src/{main.tsx, App.tsx, index.css}
- frontend/src/components/ExperimentsScreen.tsx
- frontend/src/services/apiClient.ts
- frontend/src/types/index.ts

**Configs** (2):
- configs/{example.yaml, questions.example.json}

**Placeholders** (4 chunkers):
- fixed.py, token.py, sentence.py, semantic.py (NotImplementedError, deferred to Slice 6)

### Decisions
| Decision | Why |
|---|---|
| pypdf over pdfminer.six | Simpler API, sufficient for plain text extraction |
| Voyage voyage-3.5-lite only | Cheapest model for MVP, add others in Slice 7 |
| RECURSIVE chunker only | Most common method, LangChain already has it |
| No rerank in Slice 1 | Simplify to DENSE-only retrieval first |
| BackgroundTasks not Celery | No queue infrastructure for hackathon MVP |
| Tailwind installed locally | No CDN scripts in index.html per spec |
| Hand-mirrored TS types | No codegen tooling for hackathon speed |
| Hardcoded single query | Defer persona JSON loop to Slice 5 |

---

## Deferred

- All SHOULD/COULD slices
- Error handling (basic only in Slice 1)
- Logging structure (prints for now)
- Type safety everywhere (pragmatic shortcuts OK)

---

## Decision Log

| Date | Slice | Decision | Why |
|------|-------|----------|-----|
| 2026-05-02 | 1 | pypdf for PDF parsing | Simpler than pdfminer.six, sufficient for text extraction |
| 2026-05-02 | 1 | voyage-3.5-lite only | Cheapest Voyage model, add others in Slice 7 |
| 2026-05-02 | 1 | RECURSIVE chunker only | Most common method, defer others to Slice 6 |
| 2026-05-02 | 1 | BackgroundTasks not Celery | No queue infrastructure needed for MVP |
| 2026-05-02 | 1 | Tailwind local install | No CDN per spec; postcss + autoprefixer for build pipeline |
| 2026-05-02 | 1 | Hand-mirror TS types | No codegen (typeshare/quicktype); 5 types + 3 enums manageable |
| 2026-05-02 | 1 | Hardcoded query in Slice 1 | Defer persona JSON parsing to Slice 5 for skateboard speed |
| 2026-05-02 | 1 | Atlas vector index manual | Pymongo doesn't support vector index creation; requires Atlas UI |
| 2026-05-02 | 1 | Placeholder chunkers | Create stub files with NotImplementedError to avoid import errors |

---

## Blockers & Issues

| Slice | Issue | Severity | Status | Resolution |
|-------|-------|----------|--------|------------|
| - | None yet | - | - | - |

**Severity**: 🔴 Blocker | 🟡 Workaround exists | 🟢 Minor

---

## Next Actions

**Immediate**:
1. ✅ Slice 1 code complete
2. ⏳ Commit Slice 1 files
3. ⏳ Set up .env with Voyage API key + MongoDB URI
4. ⏳ Create Atlas vector index (manual in UI)
5. ⏳ Add sample PDF to `papers/sample.pdf`
6. ⏳ End-to-end verification test

**Pipeline**:
- Slice 2: Rerank integration (~20 min)
- Slice 3: Sweep expansion ⭐ (~25 min) — THE CORE FEATURE
- Slice 4: Live status tracking (~30 min)
- Slice 5: Multiple queries (~20 min)
- Slice 6: Other chunkers (~30 min)
- Slice 7: Multiple models (~15 min)
- Slice 8: SPARSE/HYBRID (~25 min)
- Slice 9: Docs polish (~30 min)
- Slice 10: Recovery (~30 min)
