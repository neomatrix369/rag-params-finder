# SLICE 25B — Seamless Atlas Backend Switching

**MoSCoW:** SHOULD *(Slice 25 added local Atlas; this slice makes cloud ↔ local switching a single-command operation)*
**Target time:** ~1 h
**Status:** ✅ COMPLETE — 2026-06-29
**Depends on:** [Slice 25 — Atlas Local Dev Mode](SLICE-25-ATLAS-LOCAL.md)

---

## Goal

A developer should be able to switch between Atlas cloud and MongoDB Atlas Local with a single flag change — no `.env` edits, no compose file surgery, no manual URI management. The two backends must be interchangeable: same CLI commands, same configs, same dashboard URL.

---

## Problem (before this slice)

After Slice 25 the local Atlas container worked, but switching required:
- Remembering a long `docker compose --profile local-atlas up -d` command
- Manually setting `MONGODB_URI` in `.env` or shell for the CLI
- No guidance on when/how to switch back

---

## Acceptance Criteria

- [x] `./start-services.sh --local` starts the full stack (server + dashboard + local Atlas) in one command
- [x] `RAG_LOCAL_ATLAS=1 ./start-services.sh` is the env-var equivalent (CI/script-friendly)
- [x] `./start-services.sh` (no flag) is unchanged — still starts the cloud stack, same as before
- [x] `./start-services.sh mongodb start` starts only the MongoDB container (for native server/frontend dev)
- [x] `./start-services.sh mongodb stop|reset|status` manage the container lifecycle
- [x] `--local` prints the CLI `MONGODB_URI` to the terminal at the end (no need to look it up)
- [x] `--local` skips the cloud Atlas URI validation in `.env` (server URI from `RAG_SERVER_MONGODB_URI`)
- [x] Port 27017 is included in the port-conflict check when `--local` is active
- [x] `./scripts/quality-gates.sh` passes — 0 ruff / mypy / pytest regressions
- [x] [`docs/user-guide/mongodb-setup.md`](../user-guide/mongodb-setup.md) documents switching + URI detection

---

## What Changed

| File | Change |
|------|--------|
| `start-services.sh` | `--local` / `-l` flag + `RAG_LOCAL_ATLAS=1` env var; compose profile + `RAG_SERVER_MONGODB_URI` export; URI validation skipped for local mode; port 27017 checked; success output shows CLI URI and switch-back hint; `mongodb` subcommand |
| `scripts/lib/compose.sh` | Shared compose helpers, local URI constants, `compose_export_local_atlas_env()` |
| `server/db/mongodb_uri.py` | `is_atlas_uri()` + `mongo_client_kwargs()` — TLS only for cloud Atlas URIs |
| `docs/user-guide/mongodb-setup.md` | Unified cloud/local setup + switching table |

---

## Switching Reference (canonical)

| Goal | Command |
|------|---------|
| Full stack — local Atlas | `./start-services.sh --local` |
| Full stack — Atlas cloud | `./start-services.sh` |
| Local Atlas only (container) | `./start-services.sh mongodb start` |
| Stop local Atlas | `./start-services.sh mongodb stop` |
| Wipe local data | `./start-services.sh mongodb reset` |
| Status + connection string | `./start-services.sh mongodb status` |

**CLI URI for local backend:**
```bash
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
```

**Nothing else changes** when switching: configs, CLI commands, dashboard URL, experiment IDs — all identical across both backends.

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| `--local` flag on `start-services.sh` (not a new script) | Single entry point for all stack variants — mirrors existing `RAG_DEV_STACK=1` / `--force-build` pattern |
| `RAG_LOCAL_ATLAS=1` env-var equivalent | CI pipelines and `Makefile` targets can set env vars without flag parsing |
| Skip cloud URI validation when `LOCAL_ATLAS=1` | Server URI comes from `RAG_SERVER_MONGODB_URI` env override in `docker-compose.yml`, not `.env` |
| Print CLI URI in success output | Eliminates "what's the connection string again?" friction |
| Port 27017 in conflict check only when `--local` | Avoids false conflict warnings on cloud-only starts |
| `mongodb` subcommand on `start-services.sh` | Container-only lifecycle without full compose invocation when iterating on native server/frontend |
| `mongo_client_kwargs()` — no TLS for local URIs | Atlas Local uses plain `mongodb://`; unconditional `tlsCAFile` caused SSL handshake failures |

---

## Verification

```bash
# 1. Full local stack
./start-services.sh --local
# → expect "Local Atlas enabled" on startup line
# → expect CLI URI printed at the end

# 2. Run sweep against local Atlas
export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
rag-params-finder run --config configs/example-mongodb-local.yaml --detach

# 3. Switch back to cloud (no --local)
docker compose --profile local-atlas down
./start-services.sh
# → expect no mongodb-local container, cloud switch-back hint in output

# 4. Standalone container manager
./start-services.sh mongodb start
./start-services.sh mongodb status
./start-services.sh mongodb reset

# 5. Quality gates
./scripts/quality-gates.sh --quick
```

---

## Migration Guide (cloud → local for active development)

1. Stop the current cloud stack: `docker compose down`
2. Start local stack: `./start-services.sh --local`
3. Set CLI URI: `export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"`
4. Run sweeps as normal — all configs, CLI commands, and dashboard are identical.

**Reverting:**
1. Stop local stack: `docker compose --profile local-atlas down`
2. Start cloud stack: `./start-services.sh` (reads `MONGODB_URI` from `.env`)
3. Unset or restore the CLI URI.

Local data is preserved in the `mongodb_local_data` Docker volume until you run `./start-services.sh mongodb reset`.
