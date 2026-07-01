# SLICE 25 — MongoDB Atlas Local Dev Mode

**MoSCoW:** SHOULD *(Atlas M0 512 MB ceiling blocks large local sweeps; local Atlas is free and unlimited)*
**Target time:** ~1–2 h
**Status:** ✅ COMPLETE — 2026-06-29

---

## Goal

Add `mongodb/mongodb-atlas-local` Docker image as an opt-in local backend so developers can run the full pipeline — `$vectorSearch`, `$search` (BM25), all embedding providers — without an Atlas cloud account and without hitting the M0 storage quota.

---

## Acceptance Criteria

- [x] `./start-services.sh --local` starts server + dashboard + `mongodb-local` without error
- [x] Server connects to `mongodb-local` container via Docker network (`RAG_SERVER_MONGODB_URI`)
- [x] `bootstrap_indexes()` creates all vector + text search indexes programmatically for non-Atlas URIs (no Atlas UI step)
- [x] Atlas cloud path unchanged — `bootstrap_indexes()` still prunes unknown indexes only, deferring creation to submit preflight
- [x] Host CLI works: `MONGODB_URI=mongodb://localhost:27017/rag_params_finder?directConnection=true`
- [x] `atlas_storage.py` gracefully returns `None` quota (existing `is_atlas_uri()` guard — no code change needed)
- [x] `./scripts/quality-gates.sh` passes — 0 ruff / mypy / pytest regressions
- [x] [`docs/user-guide/mongodb-setup.md`](../user-guide/mongodb-setup.md) documents local Atlas path

---

## What Changed

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `mongodb-local` service under `local-atlas` profile; `MONGODB_URI: ${RAG_SERVER_MONGODB_URI:-${MONGODB_URI}}`; `mongodb_local_data` volume |
| `scripts/lib/compose.sh` | Local URI constants + `compose_export_local_atlas_env()` for server override |
| `start-services.sh` | `--local` / `RAG_LOCAL_ATLAS=1` applies profile + env override |
| `server/db/indexes.py` | `bootstrap_indexes()`: detect non-Atlas URI → create all search indexes on boot |
| `server/db/mongodb_uri.py` | `is_atlas_uri()` + `mongo_client_kwargs()` — TLS only for cloud |
| `server/db/atlas.py`, `server/core/health_check.py` | Use `mongo_client_kwargs()` for local vs cloud connections |
| `.env.example` | Document local URI option with `./start-services.sh --local` |
| `docs/user-guide/mongodb-setup.md` | Unified cloud/local setup guide |

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| `profiles: ["local-atlas"]` in main compose | Opt-in, not default — existing `docker compose up` is unchanged |
| `RAG_SERVER_MONGODB_URI` env override (not a second compose file) | Server container URI differs from host CLI; `start-services.sh --local` exports the override |
| Detect via `is_atlas_uri()` (`.mongodb.net` check) | Reuses existing utility; no new settings field required |
| Create all indexes on boot for local mode | No M0 3-index cluster limit; programmatic index creation works on Atlas Local |
| `MONGODB_STORAGE_LIMIT_MB=0` when local | Hides quota bar (no cloud quota applies locally) |
| No TLS for local `mongodb://` URIs | Atlas Local is plain TCP; `tlsCAFile` breaks local connections |

---

## Verification

```bash
# Start local stack (preferred)
./start-services.sh --local
./scripts/health-check.sh

# Check server logs — vector + text indexes created programmatically
docker logs rag-params-finder-server 2>&1 | grep -E "vector index created|text search"

# Run sweep from host
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
rag-params-finder run --config configs/example-mongodb-local.yaml --detach

# Quality gates (no regressions)
./scripts/quality-gates.sh --quick
```
