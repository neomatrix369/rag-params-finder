# Slice 16 — Kimchi Provider

## Status

✅ COMPLETE — 2026-05-13

## Goal

Add Kimchi as an embeddings-only provider so one experiment config can sweep the Kimchi-hosted embedding catalog.

## Acceptance Criteria

- [x] `embedding.provider: kimchi` validates against Kimchi-registered model IDs.
- [x] Kimchi credentials stay server-side via `KIMCHI_BASE_URL` and `KIMCHI_API_KEY`.
- [x] Kimchi calls use an OpenAI-compatible `/v1/embeddings` adapter.
- [x] Runtime embedding dimensions route to `vector_index_<dimension>`.
- [x] `configs/example-kimchi.yaml` lists all unique requested Kimchi model IDs.
- [x] Focused tests cover validation, config loading, response parsing, and runtime index selection.
- [x] User and contributor docs describe Kimchi setup and dynamic dimensions.

## Key Decisions

| Decision | Why |
|---|---|
| Prefixed model IDs like `openai/text-embedding-3-large` | Avoid collisions across upstream providers hosted behind Kimchi |
| Runtime dimensions for Kimchi | The catalog spans multiple upstream model families with different embedding sizes |
| Kimchi embeddings only | Keeps reranking behavior unchanged and avoids inventing unsupported reranker semantics |
| Secrets in settings only | Preserves the existing server-side secret boundary |

## Verification

```bash
uv run ruff check .
uv run mypy server/ cli/
uv run pytest --tb=short -q
```
