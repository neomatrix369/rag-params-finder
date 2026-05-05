# ADR-002: Dual Embedding/Reranking Providers (Voyage AI + Local)

**Status**: Accepted (evolved from Voyage-only in Slice 1 → dual-provider in Slice 7)
**Date**: 2026-05-02
**Slices**: 1 (Voyage only), 7 (local sentence-transformers added)

---

## Context

The pipeline needs to embed text chunks and (optionally) rerank query results. At Slice 1, Voyage AI was the only provider. By Slice 7, local sentence-transformers models were required to remove the API-key dependency for development and testing.

---

## Decision

Support two providers via an **explicit `provider` field** in the experiment YAML config:

| Provider | Embedding model | Reranking model | Requirements |
|---|---|---|---|
| `local` | `all-MiniLM-L6-v2` (384-dim, ~23 MB) | `cross-encoder/ms-marco-MiniLM-L-6-v2` (~23 MB) | None — downloaded from HuggingFace on first use |
| `voyage` | `voyage-3.5-lite`, `voyage-3.5`, `voyage-context-3` (1024-dim) | `rerank-2.5-lite`, `rerank-2.5` | `VOYAGE_API_KEY` in `.env` |

The `provider` field is the **single source of truth** for routing — the server never infers provider from model names at runtime.

---

## Rationale

| Concern | Decision advantage |
|---|---|
| Zero-cost development | Local models need no API key or internet after first download |
| Quality | Voyage models outperform local models for RAG; available as the primary option |
| Explicit routing | Config declares `provider: local` or `provider: voyage`; Pydantic validators reject mismatches at parse time |
| Single package | `sentence-transformers` provides both `SentenceTransformer` (embedding) and `CrossEncoder` (reranking) — no extra dependency |
| Dimension isolation | Local = 384-dim, Voyage = 1024-dim. Separate Atlas vector indexes (`vector_index_384`, `vector_index_1024`) prevent cross-contamination |

---

## Consequences

- **Two Atlas vector indexes required** for projects using both providers. Each experiment config uses one provider; vectors cannot be mixed.
- **`numpy<2` pin required**: PyTorch (used by sentence-transformers) was compiled against NumPy 1.x ABI. NumPy 2.x causes `_ARRAY_API not found` crashes.
- **Model download on first use**: Local models are ~23 MB each, cached in `~/.cache/huggingface/hub/`. First run may be slow on cold cache.
- **Provider flows end-to-end**: `EmbeddingConfig.provider` → `RunParams.embedding_provider` → `embedder.py` dispatcher. No runtime inference; server restart issues cannot mis-route.

---

## Alternatives Considered

- **Voyage-only**: Simpler code, but requires an API key for every developer. Rejected as a long-term constraint.
- **Infer provider from model name**: Fragile — model names change and prefixes like `voyage-` are not guaranteed to stay unique. Rejected in favour of explicit `provider` field.
- **OpenAI / Cohere / HuggingFace Inference API**: Out of scope for the hackathon. The `provider` abstraction makes it straightforward to add new providers.
