# SLICE 57 — Method catalogue expansion: more chunking and retrieval methods (57A–57E)

**MoSCoW:** 57A MUST · 57B MUST · 57D MUST (gate) · 57C SHOULD · 57E COULD / WON'T
**Target time:** 57A ~4–6 h · 57B ~8–10 h · 57D M–L · 57C ~6–8 h
**Status:** 📋 PLANNED — **queued behind SLICE-56 (the meetup demo kit); no code until SLICE-56 is merged** (owner decision, 2026-11-05)
**Depends on:** **55** · 57C and 57D depend on **57B** · 57D also leans on [SLICE-60](SLICE-60-PHASE2-RETRIEVAL-QUALITY-METRICS.md) (Phase 2 relevance metrics) for real comparability
**Branch:** one branch per part: `slice/57a-extra-chunkers`, `slice/57b-retriever-params`, `slice/57d-method-comparability`, `slice/57c-hybrid-rerank-mmr`
**Order after the talk:** **57A → 57B → 57D → 57C →** re-sweep the four stores on the extended YAMLs → refresh `docs/about/demo-results.json`.

> Priorities are the agent's proposal; the owner confirms MoSCoW (DECISION-OWNERSHIP).

---

## Context

Today's sweep axes: chunking `fixed · recursive · token · sentence · semantic`; retrieval `dense · sparse · hybrid` plus rerankers `reranker · cross_encoder` (and the SIE `bge-reranker`). The owner wants more industry-standard methods in the mix. Exploration (2026-11-05) found the two axes are very different in cost:

- **Chunkers:** a text-only chunker with no new tunable is cheap — new module in `server/core/chunkers/`, enum member (`server/models/enums.py`), one `elif` in `chunkers/__init__.py` (`chunk_text` dispatcher, lines 39-83), TS enum mirror in `frontend/src/types/index.ts`, tests, docs. No run-config-key change, no store change. A chunker that needs extra stored fields (parent id, window text, heading path) touches the chunk schema in **all four stores** and the retrieval projections → deferred.
- **Retrievers:** the `RetrieverBackend` Protocol (`server/db/ports/retriever_backend.py:15-28`) has **no parameter slot**; `RetrieverConfig` has only `type/provider/model`; the resume signature (`server/core/pipeline/signatures.py:20-31`) and the analyzer key (`server/core/results_analyzer.py:23-41`) ignore params, so a tunable method would silently collide with its siblings; `_legacy_retrieval_fields` (`server/models/config.py:305-311`) raises for a type with no `RetrievalMethod` twin. A one-time plumbing step (57B) is the prerequisite. Client-side methods reuse the reranker pattern in `server/core/pipeline/search.py` (call `search()`, post-process) and need no per-store code.
- **Scoring is not comparable across methods:** `dense_score` is cosine-ish for dense, unbounded BM25 for sparse, ≈0.016–0.033 for RRF, logits for rerankers; one global min-max in `analyze_results`. MMR lowers similarity by design. Until relevance metrics exist, new methods can look better or worse than they are → **57D is a gate**.
- **Grid cost:** no `max_runs` guard exists; 5→8 chunkers turns the 120-run example into 192. Therefore new methods ship in **new opt-in example YAMLs** (`configs/<store>/example-methods-extended.yaml`), never in the 44 existing examples (avoids churn in `tests/server/models/test_config_examples.py` (one pinned count — SIE = 80 — plus mirrored run-count equality across the four store folders) and keeps the 120-run grid the cross-store demo data depends on).
- `docs/contributor-guide/extending.md` is stale for both methods (wrong enum style, Mongo-only retriever path, no padding/tests/YAMLs/signature/analyzer) → rewritten as part of 57A and 57B.

- **Invariants pointer:** `docs/plan/invariants.md` (additive changes, fail-closed, no store-string branching — `tests/server/test_no_store_string_branching.py`, coverage floors locked, xenon E/C/C on `server/ cli/`). Zero-LLM stance: no LLM-based methods.

## Non-goals (whole slice)

- LLM-based methods (propositional / agentic chunking, multi-query, HyDE, RAG-Fusion, query expansion).
- Editing any of the 44 existing example YAMLs (11 per store × 4) or their run counts.
- A `max_runs` guard (new behaviour; owner decision) — only documented.
- Raising any coverage or complexity ceiling.
- Changing `STORAGE_BACKEND` / `VECTOR_STORE_BACKEND` defaults.

## Output contract (whole slice)

- **Baseline:** `grep -n "class ChunkingMethod" -A6 server/models/enums.py` shows 5 members; `RetrieverType` shows dense, sparse, hybrid, reranker, cross_encoder.
- Every new method is selectable from YAML on all four stores, appears in the dashboard as a plain string, and has unit tests; existing example runs and their config keys are unchanged (run keys for old configs identical before/after).
- Extended example YAMLs exist for all four stores and pass the mirror test.
- `extending.md` describes the real procedure for both axes.

---

## 57A — Extra chunkers (MUST, ~4–6 h)

**Scope**
- `sentence_transformers_token` — `SentenceTransformersTokenTextSplitter` from the already-installed `langchain-text-splitters`; token-aware for the embedding model's own tokenizer (the real gap vs tiktoken `token`).
- `semantic_percentile` and `semantic_stddev` — adjacent-sentence distance with a percentile / standard-deviation breakpoint (LlamaIndex / LangChain-experimental style), reimplemented with the existing numpy + sentence-transformers; the breakpoint type is encoded in the enum value so **no run-key slot is added**. Fix the per-call `SentenceTransformer` reload in `server/core/chunkers/semantic.py` while touching it.
- First direct unit tests for the five existing chunkers (none exist today; `tests/server/models/test_semantic_overlap.py` and `test_padding.py` only cover pieces).
- `configs/<store>/example-methods-extended.yaml` ×4 (opt-in) and mirror-test update; docs: `docs/user-guide/configuration.md` methods table, README counts only where they describe the *default* examples (leave them), `docs/contributor-guide/architecture.md`, `extending.md` chunker section rewritten.

**Reuse:** dispatcher pattern in `chunkers/__init__.py`; `_apply_padding`; `langchain_text_splitters`; existing embedding model loader. **No new dependency.**

**GWT**
- **Given** `chunking.methods: [sentence_transformers_token]` **when** the sweep expands **then** runs are created with that method and chunk sizes in model tokens.
- **Given** `semantic_percentile` **when** a document is chunked twice in one process **then** the embedding model is loaded once.
- **Given** an unknown method name **when** the config loads **then** validation fails with the supported list.
- **Given** the existing 120-run Mongo example **when** expanded before and after this slice **then** the run list and config keys are identical.

**Non-goals (57A):** page/paragraph/markdown chunkers (→ 57C), sentence-window and parent-child (need retrieval + schema), late chunking, any LLM chunker.

**Output contract:** `rag-params-finder run --config configs/redis/example-methods-extended.yaml` completes on a local store; chunk counts differ between methods on the Pell PDF.

**Closing Gates:** `nw-at-completeness-check` · `nw-software-crafter-reviewer` · `nw-documentarist-reviewer` (extending.md) · `nw-gate-evidence-validator` · `/verify-slice`.

## 57B — Retrieval params plumbing + tunable RRF k + alpha-hybrid (MUST, ~8–10 h)

**Scope**
- **Plumbing (prerequisite for every parametrised retrieval method):** optional param fields on `RetrieverConfig` with a validator; fix `_legacy_retrieval_fields`; extend `signatures.py` (resume signature) and `_run_config_key` (+ unpack, + the "unknown" fallback tuple) so runs differing only in a param are distinct; frontend: React row key, label (replace the hardcoded ternary at `ExplorePanels.tsx:696`), `displayRetrievers` in `experimentStatus.ts`; TS types.
- **Tunable RRF k:** `rrf_k` sweepable (e.g. 20 / 60 / 100). Composed **client-side in `search.py`** from two `search()` calls (dense + sparse) via `rrf_fuse(k=…)` so Mongo, Elasticsearch, Redis and Postgres behave identically (Postgres fuses in SQL today and ignores its `rrf_k` kwarg).
- **Alpha / weighted-sum hybrid:** per-list min-max normalisation in `server/core/retrieval/fusion.py`, then `alpha·dense + (1−alpha)·sparse`; client-side → identical on all four stores.
- `extending.md` retriever section rewritten (module path moved to `server/core/retrieval/`, four stores, `RetrieverType` vs `RetrievalMethod`, signature + analyzer key).

**Reuse:** `rrf_fuse` (`fusion.py:26`), the reranker post-processing pattern in `search.py`, `RunStatus.retrievers` (already persists the retriever docs).

**GWT**
- **Given** two hybrid retrievers differing only in `rrf_k` **when** a sweep is expanded and resumed **then** they are two distinct runs and neither is skipped as a duplicate.
- **Given** `rrf_k: 20` vs `60` **when** run on the same candidates **then** the fused order can differ and results record the parameter.
- **Given** `alpha_hybrid` with `alpha=1.0` **when** run **then** the ranking equals dense-only on the same candidates.
- **Given** an existing config without params **when** loaded **then** behaviour and config keys are unchanged.
- **Given** the dashboard **when** a param run is shown **then** its label includes the parameter and its row key is unique.

**Non-goals (57B):** MMR, hybrid→rerank (57C), parent-doc retrieval, per-store native fusion (`FT.HYBRID`, server-side RRF).

**Closing Gates:** `nw-at-completeness-check` · `nw-software-crafter-reviewer` · `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` (resume-signature / config-key collisions, cross-store parity) · `nw-documentarist-reviewer` · `nw-gate-evidence-validator` · `/verify-slice`.

## 57D — Cross-method score comparability (MUST — gate, M–L)

**Scope:** decide and implement how scores from different retrieval methods are compared fairly: per-method score normalisation in `analyze_results`, or hand-off to [SLICE-60](SLICE-60-PHASE2-RETRIEVAL-QUALITY-METRICS.md) relevance metrics (Recall@k / MRR / nDCG, which need expected sources — absent today). Until done, any leaderboard that mixes new retrieval methods shows a visible "scores are not comparable across retrieval methods" label.

**GWT**
- **Given** runs from dense, sparse, hybrid and an alpha-hybrid **when** ranked **then** the ranking does not depend on each method's native score scale.
- **Given** an MMR run (lower similarity by design) **when** ranked **then** it is not penalised for diversity (or is labelled as not comparable).

**Gate:** results mixing new retrieval methods are not published (demo data, README, About) until 57D is closed. **Human decision needed** on the comparability method before work starts (touches the canonical ranking).

## 57C — Hybrid→rerank candidates, MMR, optional structural chunkers (SHOULD, ~6–8 h)

**Scope**
- `candidates: hybrid` on `reranker` / `cross_encoder` entries (today the reranker candidate fetch is hardcoded to dense at `search.py:77`); hybrid-then-rerank is the most common production pipeline and composes existing rerankers.
- **MMR** (diversity re-rank, `lambda` sweepable), client-side: re-embed candidate texts with the documents' embedder (no store returns vectors; returning vectors from stores is L and not recommended).
- If still wanted: `paragraph` (split on blank lines, merge to size — **verify first** that `pypdf` output joins pages with `\n\n` and lines with `\n`, so on PDFs this ≈ page-based chunking) and `markdown_header` (`MarkdownHeaderTextSplitter` + recursive within sections; helps `.md` inputs only — PDF headings are unrecoverable).

**GWT**
- **Given** a reranker entry with `candidates: hybrid` **when** run **then** the reranked list is drawn from fused dense+sparse candidates.
- **Given** MMR with `lambda=1.0` **when** run **then** the order equals the dense order.
- **Given** MMR with a lower `lambda` **when** run **then** near-duplicate chunks are pushed down.

**Depends on:** 57B (params) and 57D (fair comparison).

## 57E — Could / Won't bucket (no work scheduled)

| Pri | Item | Reason |
|---|---|---|
| Could | Score-threshold filter | Scales differ per method; low value without relevance metrics |
| Could | `top_k` as a sweep axis | `max_score` / `avg_score` depend on k → runs not comparable |
| Could | `language_aware` chunker (`RecursiveCharacterTextSplitter.from_language`) | No code corpus today |
| Could | `semchunk` / `chonkie` | New dependency (audit, `uv.lock`, SCA); only if a gap remains |
| Won't (now) | Sentence-window, parent-child chunking; parent-doc retrieval | Need neighbour/parent data returned by retrieval in all four stores (no get-by-index on any port; Redis hardcodes `index=0`) |
| Won't (now) | SPLADE true sparse, ColBERT / multi-vector, late chunking | SPLADE vectors only work on Mongo today; multi-vector needs new storage everywhere; late chunking needs a new embedder path |
| Won't | LLM-based chunking / query expansion / HyDE / multi-query | Violates zero-LLM |
| Won't | Metadata filtering | Chunks carry no source/page metadata |

---

## Before-Checks [GATE] (each part)

- [ ] SLICE-56 merged (or the owner explicitly released this part earlier).
- [ ] Quality gates green on the starting commit; branch created for the part.
- [ ] Config-key regression fixture captured: expanded run list + keys of one existing example before any change.
- [ ] New dependency (if any) audited and logged in DECISIONS (none planned for 57A–57C).

## After-Checks [GATE] (each part)

- [ ] Every GWT scenario has ≥1 test; backend floors and frontend floors 95/90/95/95 unchanged.
- [ ] Old-config regression: run keys and run lists identical before/after.
- [ ] `ruff`, `mypy`, `xenon` (E/C/C) pass; no store-name string branching.
- [ ] Docs: CHANGELOG, `extending.md`, `configuration.md` methods tables, architecture doc, PROGRESS, DECISIONS.
- [ ] Extended example YAMLs pass `test_config_examples.py`.

### Closing Gates

- [ ] `nw-at-completeness-check` — AT completeness audit (slice close gate #8)
- [ ] `nw-software-crafter-reviewer` — code quality + TDD discipline review (slice close gate #9)
- [ ] `nw-solution-architect-reviewer` + `nw-system-designer-reviewer` — data-flow review (gate #9, parallel) for 57B / 57C / 57D
- [ ] `nw-documentarist-reviewer` — `extending.md` and methods tables
- [ ] `nw-gate-evidence-validator` — all 9 gate-evidence conditions pass
- [ ] `/verify-slice` — holistic evidence verdict COMPLETE (final closing gate)

## Gate Status

📋 PLANNED — stubs only. No gate-evidence files until the executor writes real evidence per part (`slice-57a.json`, `slice-57b.json`, `slice-57c.json`, `slice-57d.json`).
