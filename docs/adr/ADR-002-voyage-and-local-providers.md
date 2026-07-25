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
| `voyage` | 12 embeddings in `EMBEDDING_MODELS` (voyage-4/3/domain/context; 1024-dim) | `rerank-2.5-lite`, `rerank-2.5`, + legacy rerankers in `RERANKER_MODELS` | `VOYAGE_API_KEY` in `.env` |

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
- **NumPy / torch pairing** (updated 2026-07-25): `sie-sdk` requires `numpy>=2`. Local embedding uses `torch>=2.6` via `[tool.uv] override-dependencies` so PyTorch’s NumPy bridge works with NumPy 2.x. Older torch 2.2.x + NumPy 2 raised `RuntimeError: Numpy is not available`. Intel macOS (`x86_64` Darwin) is outside the supported `uv` environment set (no torch≥2.6 wheels).
- **Model download on first use**: Local models are ~23 MB each, cached in `~/.cache/huggingface/hub/`. First run may be slow on cold cache.
- **`voyage-context-3` uses a different API**: Registered with `contextualized: True` in `model_registry.py`; routed to `contextualized_embed()` with automatic segment splitting for documents exceeding 32K tokens. All other Voyage models use standard `embed()`.
- **Provider flows end-to-end**: `EmbeddingConfig.provider` → `RunParams.embedding_provider` → `embedder_factory.get_embedder()`. No runtime inference; server restart issues cannot mis-route.

---

## Evolution (Slice 21 — SIE third provider)

**2026-06-29**: Added `provider: sie` as a third embedding provider without a new ADR. Dispatch moved to `server/core/embedder_factory.py` (`get_embedder(provider)` returns voyage | local | sie functions). Models: BGE-M3, Stella-v5 (1024-dim dense), SPLADE-v3 (30522-dim sparse) in `server/core/sie_embedder.py`. Preflight: `server/core/sie_guard.py`. Env: `SIE_ENABLED`, `SIE_ENDPOINT`, `SIE_API_KEY`. See [extending.md](../contributor-guide/extending.md) and [sie-setup.md](../user-guide/sie-setup.md).

Reranking providers remain **dual** (`local` | `voyage`) — SIE is embedding-only in Slice 21.

**2026-07-25**: Superseded the Slice 7 `numpy<2` pin. `sie-sdk` needs NumPy 2; Dependabot’s `numpy<3` + locked torch 2.2 broke local embeds. Resolution: `numpy>=2,<3` + `torch>=2.6` override (VERIFIED via local dense smoke on Atlas Local).

---

## Alternatives Considered

- **Voyage-only**: Simpler code, but requires an API key for every developer. Rejected as a long-term constraint.
- **Infer provider from model name**: Fragile — model names change and prefixes like `voyage-` are not guaranteed to stay unique. Rejected in favour of explicit `provider` field.
- **OpenAI / Cohere / HuggingFace Inference API**: Out of scope for the hackathon. The `provider` abstraction makes it straightforward to add new providers.
