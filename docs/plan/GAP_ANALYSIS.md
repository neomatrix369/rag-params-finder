# Gap Analysis
> ~2 min read · **Updated 2026-07-02** after Slice 21/25/25B completion and Dependabot triage

Canonical build status: [docs/slices/PROGRESS.md](../slices/PROGRESS.md)

---

## Closed Gaps (since 2026-06-27 snapshot)

| Area | Was | Now | Closed by |
|------|-----|-----|-----------|
| SIE inference backend | Not installed | BGE-M3, Stella-v5 via `sie_embedder.py` + `embedder_factory.py` | Slice 21 ✅ |
| Caller-supplied corpus | PDF only | `corpus: list[str]` on `SweepRequest` | Slice 21 ✅ |
| Aim experiment tracking | None | `aim_logger.py` (no-op on failure) | Slice 21 ✅ |
| `POST /api/v1/sweep` | Missing | Live in `server/api/sweep.py` | Slice 21 ✅ |
| SIE health check | MongoDB only | `/health` includes SIE status | Slice 21 ✅ |
| Atlas M0 storage ceiling (local dev) | Blocker | `./start-services.sh --local` + auto indexes | Slice 25/25B ✅ |
| CI action upgrades (repo-lint, gitleaks) | Mixed v4/v2 | All jobs on checkout/setup-python v6; gitleaks v3 | PRs #36–#39 ✅ |

---

## Remaining Capability Gaps

| Area | PCTO / Roadmap Requirement | What Exists | Gap | Severity | Target |
|------|---------------------------|-------------|-----|----------|--------|
| Best-config lookup | `GET /api/v1/best-config?task=...` | Stub returns placeholder message | History query + recommendation logic | **Critical** (PCTO) | Slice 22 |
| SIE reranking | BGE-reranker via SIE `score` | Voyage + CrossEncoder only | SIE score path in `reranker.py` | Notable | Slice 22 |
| SPLADE v3 sparse sweep | Full sparse retrieval via SIE | Registry + `vector_index_30522` exist; sweep path incomplete | End-to-end sparse run + index guard | Notable | Slice 22 |
| Results export | CSV/JSONL download | JSON via `/results` and `/explore` only | Export endpoint + dashboard button | **Must** (#49) | Slice 28 |
| MongoDB mode visibility | Cloud vs local indicator | URI detection exists (`mongodb_uri.py`) | `/healthz`, CLI banner, dashboard badge | Should | Slice 27 |
| Local MongoDB UX docs | Smooth onboarding | Unified `mongodb-setup.md` exists | Pre-flight, wait-for-healthy, stale volume troubleshooting | Should | Slice 26 |
| Storage quota guard | Cloud production safety | Boot reconciliation only | Preflight + runtime 8000 handling | Should | Slice 19 |
| Parallel sweep | `parallelism > 1` | Sequential `BackgroundTasks` | Bounded concurrency | Should | Slice 16 |
| Ollama + Tier 2–3 | HyDE, Multi-Query, etc. | None | Full retrieval tier expansion | Could | Slice 23 |
| Evidently AI monitoring | Drift alerts | None | Integration | Could | Slice 23 |
| MCP server | `get_rag_config` tool | None | **Won't this cycle** — use best-config HTTP | Won't | — |

---

## Toolchain / Dependabot Gaps (deferred — no active slice)

| Upgrade | Status | Blocker | Action taken |
|---------|--------|---------|--------------|
| eslint-plugin-react-hooks 5→7 | Closed (#26) | New React 19 lint rules in SearchExplorerScreen | Defer until screen refactor |
| eslint-plugin-react-refresh 0.4→0.5 | Closed (#41) | npm ERESOLVE vs eslint@8 | Defer until ESLint 9 slice |
| eslint-plugin-security 1.7→4.0 | Closed (#42) | `plugin:security/recommended` breaking change | Defer until ESLint config migration |
| vite 6→8 | Closed (#43) | `@vitejs/plugin-react@4.x` peer range | Defer intentional toolchain slice |
| sentence-transformers `<4`→`<6` | Closed (#40) | mypy CrossEncoder type mismatch | Defer ML stack slice |
| actions/checkout 6→7 | Open (#57) | Ecosystem early-adoption risk | Evaluate after v7 stabilises |
| actions/cache 5→6 | Open (#56) | Low risk | Merge after CI green |

---

## What Is Already Sufficient (No Gap)

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI + `/experiments` API | ✅ | Unchanged; `/api/v1` is additive |
| MongoDB Atlas + Local | ✅ | Same query paths; switching via env |
| Voyage AI embeddings + reranking | ✅ | Numeric baseline preserved |
| Dense/sparse/hybrid retrieval (Tier 1) | ✅ | Atlas vector + FTS |
| Orchestrator pipeline | ✅ | Provider dispatch via factory |
| Docker Compose stack | ✅ | Prod + dev HMR profiles |
| CI / quality gates | ✅ | 78+ tests; `./scripts/quality-gates.sh` |
| Chunkers (fixed, token, sentence, semantic) | ✅ | PRs #47/#48 extend further |

---

## Divergence Check (Spec ↔ Tests ↔ Code)

| Area | Spec says | Code does | Gap | Action |
|------|-----------|-----------|-----|--------|
| best-config | Returns recommendation from history | Stub only | **Yes** | Slice 22 |
| SPLADE sparse sweep | Full open-source BM25 | Index + registry ready; encode path partial | **Partial** | Slice 22 |
| SIE reranking | BGE-reranker scores | Voyage/CrossEncoder only | **Yes** | Slice 22 |
| Export | CSV/JSONL download | Not implemented | **Yes** | Slice 28 |
| All Slice 21 items | SIE + sweep + Aim | Implemented + tested | **No** | — |

**Result**: No conflicts with completed work. Remaining gaps are forward slices with clear ownership.
