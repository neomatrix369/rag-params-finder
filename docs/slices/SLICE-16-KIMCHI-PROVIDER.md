# Kimchi Provider (delivered slice)

> **Note:** Filename uses `SLICE-16` for historical reasons. Parallel sweep execution is tracked separately in [`SLICE-16-PARALLEL-SWEEP-RUNS.md`](./SLICE-16-PARALLEL-SWEEP-RUNS.md).

## Status

✅ COMPLETE — 2026-05-13 (core) · hardened 2026-05-20 (CAST payload, db-stats, example config)

## Goal

Add Kimchi as an embeddings-only provider so one experiment config can sweep the Kimchi-hosted embedding catalog.

## Acceptance Criteria

- [x] `embedding.provider: kimchi` validates against Kimchi-registered model IDs.
- [x] Kimchi credentials stay server-side via `KIMCHI_BASE_URL` and `KIMCHI_API_KEY`.
- [x] Kimchi calls use an OpenAI-compatible `/v1/embeddings` adapter.
- [x] Runtime embedding dimensions route to `vector_index_<dimension>`.
- [x] `configs/example-kimchi.yaml` sweeps four verified OpenAI-family models (24 runs); additional registry IDs parked in YAML until CAST account verification.
- [x] Focused tests cover validation, config loading, response parsing, and runtime index selection.
- [x] User and contributor docs describe Kimchi setup and dynamic dimensions.

## Key Decisions

| Decision | Why |
|---|---|
| Prefixed model IDs like `openai/text-embedding-3-large` | Avoid collisions across upstream providers hosted behind Kimchi |
| Runtime dimensions for Kimchi | The catalog spans multiple upstream model families with different embedding sizes |
| Kimchi embeddings only | Keeps reranking behavior unchanged and avoids inventing unsupported reranker semantics |
| Secrets in settings only | Preserves the existing server-side secret boundary |
| Full LiteLLM model ID to CAST API | Stripping the `openai/` prefix broke routing |
| CAST embedding payload shape | Request body must match CAST template (`input` + `model`) |
| Sample stored embeddings for db-stats | Registry `dimensions: None` — storage estimates need one chunk vector per model |

## Post-delivery fixes (2026-05-20)

- Vector DB stats no longer crash on Kimchi experiments (`_sample_embedding_dimension` in `experiments_shared.py`).
- `KIMCHI_BASE_URL` documented as `https://llm.cast.ai/openai` (not the supported-providers discovery URL).
- Example config pared to four active models; Mistral/Gemini/Azure/etc. remain in registry but commented as parked.

## Verification

```bash
uv run ruff check .
uv run mypy server/ cli/
uv run pytest --tb=short -q
```
