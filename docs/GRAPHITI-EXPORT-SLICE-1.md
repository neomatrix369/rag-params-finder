# Graphiti Memory Export — rag-params-finder Slice 1

**Group ID**: `rag-params-finder-slice-1`  
**Date**: 2026-05-02  
**Context**: Hackathon MVP build following Lean Skateboard approach

---

## Project Overview

**rag-params-finder** is a RAG parameter sweep experimentation tool for ML engineers to systematically evaluate:
- Embedding models (Voyage AI: voyage-3.5-lite/3.5/context-3)
- Chunking strategies (FIXED, RECURSIVE, TOKEN, SENTENCE, SEMANTIC)
- Retrieval methods (DENSE, SPARSE, HYBRID)

**Architecture**: Two-process system
1. **Python CLI** (thin client) — submits YAML configs
2. **FastAPI Server** (engine) — orchestrates PDF → chunk → embed → search pipeline
3. **React Dashboard** (observer) — read-only visualization

**Core Technologies**:
- MongoDB Atlas Vector Search (1024-dim, cosine similarity)
- Voyage AI (embeddings + reranking)
- LangChain (text splitting)
- FastAPI + Pydantic (server)
- React 19 + TypeScript 5.8 + Tailwind CSS (dashboard)

---

## Slice 1 — Skateboard Implementation

### Goal
End-to-end pipeline with **one chunker, one model, one query** — prove architecture works before adding features.

### What Was Built (53 files)

**Server** (20 files):
- FastAPI app with /healthz + /experiments endpoints
- Complete pipeline orchestrator
- PDF parsing (pypdf)
- RECURSIVE chunking (LangChain RecursiveCharacterTextSplitter)
- Voyage embedding client (document + query modes)
- Atlas DENSE retrieval ($vectorSearch)
- Pydantic models: ExperimentConfig, RunStatus, QueryResult
- 6 MongoDB collections + indexes
- Phase tracking: QUEUED → PARSING → CHUNKING → EMBEDDING → STORING → QUERYING → COMPLETE

**CLI** (4 files):
- Typer-based `rag-params-finder run --config` command
- YAML config loader
- HTTP client to server
- Rich terminal output

**Dashboard** (13 files):
- React 19 + Vite 6 + TypeScript 5.8
- ExperimentsScreen with 0.5Hz polling
- Tailwind CSS installed locally (NO CDN scripts)
- Hand-mirrored TypeScript types from Pydantic

**Documentation** (7 files):
- README with judge-runnable Quickstart
- ARCHITECTURE.md (system overview)
- PROGRESS.md (slice tracker + decision log)
- SLICE-01-SKATEBOARD.md (specification)

---

## Key Decisions & Rationale

### 1. Architecture

**Decision**: Two-process architecture (thin CLI + FastAPI server)  
**Why**: Clean separation of concerns, server handles all heavy lifting  
**Impact**: Secrets stay server-side only (VOYAGE_API_KEY, MONGODB_URI never in CLI)

### 2. Technology Choices

| Choice | Alternative Rejected | Why |
|--------|---------------------|-----|
| pypdf | pdfminer.six | Simpler API, sufficient for plain text extraction |
| FastAPI BackgroundTasks | Celery | No queue infrastructure needed for hackathon MVP |
| LangChain text splitters | Custom implementations | 4 of 5 chunkers already implemented |
| voyage-3.5-lite only | All 3 models | Cheapest model for Slice 1, add others in Slice 7 |
| RECURSIVE chunker only | All 5 methods | Most common method, defer others to Slice 6 |

### 3. Frontend Stack

**Decision**: Tailwind CSS installed locally (postcss + autoprefixer)  
**Why**: Spec explicitly prohibits CDN scripts in index.html  
**Impact**: Requires build pipeline, but proper production setup

**Decision**: Hand-mirror TypeScript types from Pydantic (no codegen)  
**Why**: Only 5 types + 3 enums; codegen tooling (typeshare, quicktype) overkill for hackathon  
**Impact**: Must manually sync if server models change

**Decision**: Polling at 0.5Hz for experiments list  
**Why**: Simpler than SSE for MVP, sufficient latency  
**Deferred**: SSE migration to post-MVP

### 4. MongoDB Atlas

**Decision**: 6 collections (chunks, experiments, run_status, collections, queries, results)  
**Why**: Normalized schema for clarity, denormalization not needed at this scale

**Critical Learning**: Vector index must be created MANUALLY in Atlas UI  
**Why**: Pymongo doesn't support vector index creation programmatically  
**Impact**: README must document this manual step for judges

**Critical Learning**: Always filter by `embedding_model` on vector searches  
**Why**: Different Voyage models produce incompatible vectors (voyage-3.5-lite = 1024-dim, different from voyage-3.5)  
**Impact**: Query filter: `{"experiment_id": exp_id, "embedding_model": model}`

### 5. Voyage AI

**Decision**: Use `input_type="document"` for chunks, `input_type="query"` for queries  
**Why**: Voyage API optimizes embeddings based on input type  
**Impact**: Better retrieval quality vs. generic embeddings

**Decision**: voyage-3.5-lite produces 1024-dim vectors  
**Why**: Different from predecessor's Transformers.js (384-dim)  
**Impact**: Vector index must be configured for 1024 dimensions

### 6. Slice Execution Pattern

**Decision**: Create placeholder stub files for unimplemented chunkers  
**Why**: Avoid import errors when dispatcher references them  
**Pattern**: `raise NotImplementedError("Will be implemented in Slice 6")`

**Decision**: Hardcoded single query in Slice 1  
**Why**: Defer persona JSON parsing to Slice 5 for skateboard speed  
**Impact**: Fast end-to-end proof, complexity added incrementally

**Decision**: Update PROGRESS.md continuously, not at end  
**Why**: Learnings from predecessor — maintain resumable state at all times  
**Impact**: Can interrupt/resume work cleanly

---

## Implementation Stats

- **Files created**: 53 total
- **Lines of code**: ~3,473 insertions
- **Time target**: ~75 minutes (Slice 1 skateboard)
- **Status**: Code complete, pending live verification

---

## Verification Pending

1. Create `.env` with VOYAGE_API_KEY + MONGODB_URI
2. Create Atlas vector index manually (1024-dim, cosine, filters)
3. Add sample PDF to `papers/sample.pdf`
4. End-to-end test: CLI submit → server execute → dashboard display

---

## Deferred to Future Slices

| Slice | Feature | Target Time | Priority |
|-------|---------|-------------|----------|
| 2 | Reranking (Voyage rerank-2.5-lite) | ~20 min | MUST |
| 3 | Sweep expansion (Cartesian product) | ~25 min | MUST ⭐ CORE FEATURE |
| 4 | Live status tracking + LiveRunScreen | ~30 min | MUST |
| 5 | Persona-based queries (loop over JSON) | ~20 min | MUST |
| 6 | Other chunkers (FIXED, TOKEN, SENTENCE, SEMANTIC) | ~30 min | SHOULD |
| 7 | Multiple embedding models | ~15 min | SHOULD |
| 8 | SPARSE/HYBRID retrieval | ~25 min | SHOULD |
| 9 | ADRs + docs polish | ~30 min | SHOULD |
| 10 | Recovery (3-tier: passive/manual/auto) | ~30 min | COULD |

---

## Key Learnings for Future Work

1. **Atlas vector index is manual** — Document this clearly in README setup steps
2. **embedding_model filter is critical** — Easy to forget, hard to debug when mixed
3. **Hand-mirroring types is viable** — 5 types + 3 enums manageable; don't over-engineer
4. **Tailwind local install** — No shortcuts with CDN; proper build pipeline from start
5. **Placeholder stubs prevent import errors** — Better than commenting out dispatcher cases
6. **Hardcoded query is acceptable** — Skateboard = minimal viable path, not feature-complete
7. **PROGRESS.md is load-bearing** — Decision log prevents re-litigation, documents rationale

---

## Next Steps

1. ✅ Commit Slice 1 files (DONE: commit d7fc9e3)
2. ⏳ Set up .env with live credentials
3. ⏳ Create Atlas vector index
4. ⏳ Add sample PDF
5. ⏳ End-to-end verification test
6. 📋 Proceed to Slice 2 (Reranking)

---

## Import Instructions

To add to Graphiti:

```python
import_episode(
    content=<this file content>,
    group_id="rag-params-finder-slice-1",
    name="Slice 1 Skateboard Implementation"
)
```

Key entities to extract:
- rag-params-finder (project)
- MongoDB Atlas Vector Search (technology)
- Voyage AI (technology)
- FastAPI (framework)
- React 19 (framework)
- Slice 1 Skateboard (milestone)
- Two-process architecture (pattern)
