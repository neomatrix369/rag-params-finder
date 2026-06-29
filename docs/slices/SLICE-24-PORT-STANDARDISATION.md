# Slice 24 — Port Standardisation

**Status**: ✅ COMPLETE
**Goal**: Replace commonly-conflicting default ports with unique static alternatives applied consistently across every file — code, Docker Compose, Dockerfiles, scripts, tests, and docs.

---

## Port decisions

| Service | Old port | New port | Rationale |
|---------|----------|----------|-----------|
| FastAPI backend | 8001 | **8001** (unchanged) | Already uncommon; not a standard framework default |
| React/Vite frontend | 5173 | **5374** | 5173 is Vite's own default — any other Vite project running simultaneously collides |
| SIE Docker (external) | 8080 | **8720** | 8080 is the most widely-conflicting port in dev tooling (Jenkins, Tomcat, Hadoop, Spark, many Docker stacks) |
| Ollama (planned Slice 23) | 11434 | **11434** (unchanged) | Ollama chose this deliberately to avoid conflicts |

Ports **5374** and **8720** are unregistered by IANA and unused by any common developer tool.

**Strategy**: static ports chosen to avoid conflicts, not dynamic port scanning. Static ports are predictable, grep-able, and Docker-friendly.

---

## Acceptance criteria

- [x] `server/core/sie_embedder.py` — SIE endpoint default `http://localhost:8720` (`SIE_ENDPOINT`); docstring and `docker run` example updated (`-p 8720:8080`)
- [x] `server/api/sweep.py` — SIE endpoint default `http://localhost:8720`
- [x] `tests/test_sie_embedder.py` — all GWT docstrings updated from 8080 to 8720
- [x] `server/core/model_registry.py` — SIE section comment updated
- [x] `docs/slices/SLICE-21-SIE-SKATEBOARD.md` — GWT scenarios, docker run example, health check URL
- [x] `docs/slices/SLICE-22-SIE-SCOOTER.md` — GWT scenario and before-check
- [x] `CLAUDE.md` — key-files table and provider system section
- [x] `CHANGELOG.md` — v0.11.0 SIE Skateboard entry
- [x] `docs/contributor-guide/extending.md` — SIE note
- [x] `frontend/vite.config.ts` — `port: 5374`
- [x] `docker-compose.yml` — ports `5374:5374`, frontend healthcheck URL
- [x] `docker-compose.dev.yml` — Vite `--port 5374`
- [x] `docker/frontend.Dockerfile` — `EXPOSE 5374`, preview command, healthcheck
- [x] `docker/frontend.dev.Dockerfile` — `EXPOSE 5374`, dev command
- [x] `server/settings.py` — `_DEFAULT_CORS_ORIGINS` uses 5374; comment example updated
- [x] `cli/main.py` — `_DASHBOARD_URL = "http://localhost:5374"`
- [x] `start-services.sh` — `check_ports()` checks 8001 and 5374; fallback curl and echo messages updated; port rationale comment added
- [x] `scripts/health-check.sh` — header comment and `FRONTEND_URL` default updated
- [x] `.env.example` — port reference block added; CORS_ORIGINS example updated
- [x] `CLAUDE.md`, `AGENTS.md`, `CLAUDE.local.md` — dashboard URL references updated
- [x] All user-guide docs (`getting-started.md`, `dashboard-guide.md`, `cli-reference.md`, `cloud-setup.md`, `configuration.md`, `troubleshooting.md`)
- [x] `QUICKSTART.md`, `docs/README.md` — dashboard URL references
- [x] `docs/slices/SLICE-14-DOCKER-COMPOSE.md`, `docs/slices/SLICE-01-SKATEBOARD.md` — port references
- [x] `docs/_internal/DOCS-CODE-AUDIT.md`, `docs/_internal/DOCS-CODE-AUDIT-FIXES.md` — CORS examples

## What does NOT change

- Backend port **8001** — already unique; all existing references correct
- SIE container-internal port — SIE image always binds to 8080 internally; host mapping is `-p 8720:8080`
- Container-internal healthchecks for the server (`localhost:8001`) — internal port unchanged
- `VITE_DEV_PROXY_TARGET` (`http://server:8001`) — container-to-container traffic, no host port involved
- Atlas indexes, YAML experiment configs, MongoDB collection names

## Files changed

**Code** (8 files): `server/core/sie_embedder.py`, `server/api/sweep.py`, `server/core/model_registry.py`, `server/settings.py`, `frontend/vite.config.ts`, `cli/main.py`, `docker/frontend.Dockerfile`, `docker/frontend.dev.Dockerfile`

**Compose / scripts** (4 files): `docker-compose.yml`, `docker-compose.dev.yml`, `start-services.sh`, `scripts/health-check.sh`

**Tests** (1 file): `tests/test_sie_embedder.py`

**Config** (1 file): `.env.example`

**Docs** (18 files): CLAUDE.md, AGENTS.md, CLAUDE.local.md, QUICKSTART.md, CHANGELOG.md, docs/README.md, docs/contributor-guide/extending.md, docs/contributor-guide/development.md, docs/user-guide/getting-started.md, docs/user-guide/dashboard-guide.md, docs/user-guide/cli-reference.md, docs/user-guide/cloud-setup.md, docs/user-guide/configuration.md, docs/user-guide/troubleshooting.md, docs/slices/SLICE-01-SKATEBOARD.md, docs/slices/SLICE-14-DOCKER-COMPOSE.md, docs/slices/SLICE-21-SIE-SKATEBOARD.md, docs/slices/SLICE-22-SIE-SCOOTER.md, docs/_internal/DOCS-CODE-AUDIT.md, docs/_internal/DOCS-CODE-AUDIT-FIXES.md
