# SLICE 25 — MongoDB Atlas Local Dev Mode

**MoSCoW:** SHOULD *(Atlas M0 512 MB ceiling blocks large local sweeps; local Atlas is free and unlimited)*
**Target time:** ~1–2 h
**Status:** ✅ COMPLETE — 2026-06-29

---

## Goal

Add `mongodb/mongodb-atlas-local` Docker image as an opt-in local backend so developers can run the full pipeline — `$vectorSearch`, `$search` (BM25), all embedding providers — without an Atlas cloud account and without hitting the M0 storage quota.

---

## Acceptance Criteria

- [x] `docker compose -f docker-compose.yml -f docker-compose.local-atlas.yml --profile local-atlas up -d` starts without error
- [x] Server connects to `mongodb-local` container via Docker network
- [x] `bootstrap_indexes()` creates all vector + text search indexes programmatically for non-Atlas URIs (no Atlas UI step)
- [x] Atlas cloud path unchanged — `bootstrap_indexes()` still prunes unknown indexes only, deferring creation to submit preflight
- [x] Host CLI works: `MONGODB_URI=mongodb://localhost:27017/rag_params_finder?directConnection=true`
- [x] `atlas_storage.py` gracefully returns `None` quota (existing `is_atlas_uri()` guard — no code change needed)
- [x] `./scripts/quality-gates.sh` passes — 0 ruff / mypy / pytest regressions
- [x] `docs/user-guide/local-atlas-setup.md` written with runnable commands

---

## What Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `mongodb-local` service under `local-atlas` profile; added `mongodb_local_data` named volume |
| `docker-compose.local-atlas.yml` | **NEW** — overlay: server `MONGODB_URI` override → `mongodb-local:27017`; `depends_on: mongodb-local` |
| `server/db/indexes.py` | `bootstrap_indexes()`: detect non-Atlas URI → call `create_vector_indexes()` + `create_text_search_index()` on boot |
| `.env.example` | Document local URI option (Option A/B) with start command |
| `docs/user-guide/local-atlas-setup.md` | **NEW** — full quick-start: Docker stack, host dev loop, comparison table, reset instructions |

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| `profiles: ["local-atlas"]` in main compose | Opt-in, not default — existing `docker compose up` is unchanged |
| Separate `docker-compose.local-atlas.yml` overlay | `MONGODB_URI` for the server differs from host CLI; overlay is the compose-native way to override per service |
| Detect via `is_atlas_uri()` (`.mongodb.net` check) | Reuses existing utility in `atlas_storage.py`; no new settings field required |
| Create all indexes on boot for local mode | No M0 3-index cluster limit; `create_search_indexes` is supported programmatically on Atlas Local |
| `MONGODB_STORAGE_LIMIT_MB=0` in overlay | Hides quota bar (no cloud quota applies locally); 0 = hidden is the existing default |
| No change to `search_index_guard.py` | Local Atlas creates all indexes at startup → `is_satisfied=True` by submit time; cluster_limit logic never triggered |

---

## Verification

```bash
# Start local stack
docker compose \
  -f docker-compose.yml \
  -f docker-compose.local-atlas.yml \
  --profile local-atlas \
  up --build -d

# Check server logs — expect "local mode: all search indexes ensured programmatically"
docker logs rag-params-finder-server | grep "local mode"

# Run sweep from host
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
rag-params-finder run --config configs/example-mongodb-local.yaml

# Quality gates (no regressions)
./scripts/quality-gates.sh
```
