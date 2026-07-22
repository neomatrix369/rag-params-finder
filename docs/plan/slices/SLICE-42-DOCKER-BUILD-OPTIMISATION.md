# SLICE 42 — Docker Build Optimisation

**Status**: 📋 PLANNED
**MoSCoW**: Should *(build/CI hygiene — same class as Slice 20/40 toolchain hardening; no user-facing behaviour change)*
**Branch**: `slice/42-docker-build-optimisation`
**Target time**: ~2–3 h
**Depends on**: none *(independent of 32–38 Supabase path)*
**Last Updated**: 2026-07-22

---

## Motivation

Inspecting CI run #239 (tied to PR #84) and the `ci.yml` job graph reveals no job builds or validates Docker images. Inspecting the actual Docker assets confirms the layering causes full, expensive rebuilds far more often than necessary.

Specific confirmed problems (evidence: files as of 2026-07-22):

| # | File | Problem |
|---|------|---------|
| 1 | `docker/server.Dockerfile` | Single stage — `build-essential` + `curl` + compiler toolchain persist in **runtime** image |
| 2 | `docker/server.Dockerfile` | `COPY server ./server` before `RUN uv pip install ... torch==2.11.0` — any source edit (including README typo) busts the PyTorch cache layer (~2 GB CPU wheel) |
| 3 | `docker/server.Dockerfile`, `docker/frontend*.Dockerfile` | No BuildKit cache mounts on `uv pip install` / `npm ci` |
| 4 | `docker/frontend.Dockerfile` | Runtime stage runs `npm run preview` (Vite docs: not for production) and ships full `node_modules` |
| 5 | `.github/workflows/ci.yml` | No Docker build step — regressions ship silently |
| 6 | `scripts/docker-build-context.sh` | Workaround for problem #2, not a fix |

Follows the pattern of Slice 14 (introduced the Docker stack) and Slice 20/40 (CI trigger hardening).

---

## MoSCoW

| Priority | Item |
|----------|------|
| **Must** | Multi-stage `docker/server.Dockerfile`: `deps` stage installs from `pyproject.toml` + `uv.lock` only; `runtime` stage copies installed env then `server/`, `cli/`, `README.md` |
| **Must** | `--mount=type=cache,target=/root/.cache/uv` on deps install step + apt cache mount for `build-essential`/`curl` |
| **Must** | `--mount=type=cache,target=/root/.npm` on `npm ci` in `docker/frontend.Dockerfile` and `docker/frontend.dev.Dockerfile` |
| **Should** | Replace frontend runtime stage `npm run preview` with `nginx:alpine` serving `dist/` + SPA fallback via `docker/frontend.nginx.conf` |
| **Should** | New path-scoped CI job `docker-build` — triggered only on changes to `docker/**`, `docker-compose*.yml`, `server/**`, `cli/**`, `frontend/**`, `pyproject.toml`, `uv.lock`; non-blocking (`continue-on-error: true`) on first landing |
| **Could** | Trim/confirm `scripts/docker-build-context.sh` source lists now that native layer cache does the fine-grained work |
| **Could** | Add short "Docker build architecture" note to `docs/contributor-guide/development.md` |
| **Won't** | Postgres profile, image publishing/registry push, making CI docker job merge-blocking on day one |

---

## GWT Specs

### Must-1: Source changes do not bust PyTorch cache

**Given** the multi-stage `deps` stage has been built (torch install layer cached),
**When** a developer edits only `server/main.py` (no `pyproject.toml` or `uv.lock` change) and rebuilds,
**Then** the `uv pip install torch` layer shows `CACHED` in BuildKit output and no network download occurs.

### Must-2: README change does not bust PyTorch cache

**Given** the `deps` stage is cached,
**When** a developer edits only `README.md` (badges, typos — common repo activity) and rebuilds,
**Then** the torch install layer shows `CACHED`.

### Must-3: npm dependency layer survives source changes

**Given** the frontend `npm ci` layer is cached,
**When** a developer edits only `frontend/src/App.tsx` and rebuilds,
**Then** the `npm ci` step shows `CACHED` in BuildKit output.

### Should-4: Compiler toolchain absent from runtime server image

**Given** the rebuilt `runtime` stage server image,
**When** running `docker run --rm <server-image> which gcc`,
**Then** the command exits non-zero (gcc not installed in runtime image).

### Should-5: Frontend runtime image is minimal

**Given** the rebuilt frontend production image (nginx:alpine runtime),
**When** inspecting the image with `docker run --rm <frontend-image> ls /app`,
**Then** no `node_modules` directory is present; image size is measurably smaller than the previous `node:22-alpine` + `node_modules` runtime.

### Should-6: Existing start-services behaviour unchanged

**Given** the optimised Dockerfiles are in place,
**When** running `./start-services.sh` followed by `./scripts/health-check.sh`,
**Then** all SLICE-14 acceptance criteria pass unmodified.

### Should-7: CI path filter — docs-only PR skips Docker job

**Given** a PR that touches only `docs/**` files,
**When** the CI `Detect changed paths` job runs,
**Then** the `docker` output is `false` and the `docker-build` job does NOT appear in the run.

### Should-8: CI path filter — Docker-touching PR triggers build

**Given** a PR that touches any file under `docker/**`,
**When** CI runs,
**Then** the `docker-build` job triggers, both `server.Dockerfile` and `frontend.Dockerfile` build successfully, and the job reports `success` (or `continue-on-error: true` absorbs non-zero while it stabilises).

### Should-9: GHA cache hit on second CI run

**Given** the first CI run on a branch has completed (GHA cache populated),
**When** a second CI run triggers on the same branch with no dependency changes,
**Then** the `docker-build` job completes measurably faster than the first run (cache hit visible in BuildKit output).

---

## Files to Create / Modify

| File | Change | Priority |
|------|--------|----------|
| `docker/server.Dockerfile` | Rewrite: multi-stage `deps` + `runtime`; cache mounts | **Must** |
| `docker/frontend.Dockerfile` | Add `--mount=type=cache` on `npm ci`; replace runtime with `nginx:alpine` | **Must/Should** |
| `docker/frontend.dev.Dockerfile` | Add `--mount=type=cache` on `npm ci` | **Must** |
| `docker/frontend.nginx.conf` | NEW — nginx config: listen 5374, SPA fallback (`try_files $uri /index.html`) | **Should** |
| `.github/workflows/ci.yml` | Add `docker` filter to paths-filter job; add `docker-build` job (non-blocking) | **Should** |
| `scripts/docker-build-context.sh` | Optional: trim source list after native cache absorbs fine-grained work | **Could** |
| `docs/contributor-guide/development.md` | Optional: short "Docker build architecture" note | **Could** |

---

## Before-Checks

- [ ] `./start-services.sh && ./scripts/health-check.sh` passes — baseline before changes
- [ ] `./scripts/quality-gates.sh` passes (zero regressions baseline)
- [ ] `docker buildx version` ≥ 0.10 (BuildKit cache mounts require Buildx; already default on Docker Desktop)
- [ ] **Spike**: run `uv sync --frozen --no-install-project` (or `uv pip install --no-deps -e .`) against the actual `pyproject.toml`/`uv.lock` in the `deps` stage to confirm correct dep resolution without project source files present — finalise Dockerfile syntax after spike passes
- [ ] Read `SLICE-14-DOCKER-COMPOSE.md` acceptance criteria — ensure none are broken by the Dockerfile changes

---

## TDD Execution

This slice has no pytest-testable units (pure Dockerfile/CI YAML changes). Verification is build-evidence-based:

1. **Red**: Note current `docker build` output (no CACHED for torch after source change — reproduce the problem once to confirm).
2. **Green**: Apply Must changes; verify GWT Must-1, Must-2, Must-3 with actual `docker build` output showing CACHED layers.
3. **Should**: Apply Should changes; verify GWT Should-4 through Should-9.
4. **Regress**: Run `./scripts/quality-gates.sh`; run `./start-services.sh && ./scripts/health-check.sh`.

---

## After-Checks

- [ ] **GWT Must-1**: Build after `server/main.py` change → torch layer shows `CACHED`
- [ ] **GWT Must-2**: Build after `README.md` change → torch layer shows `CACHED`
- [ ] **GWT Must-3**: Build after `frontend/src/App.tsx` change → `npm ci` shows `CACHED`
- [ ] **GWT Should-4**: `docker run --rm <server-image> which gcc` exits non-zero
- [ ] **GWT Should-5**: Frontend runtime image has no `node_modules`; `docker images` shows size reduction
- [ ] **GWT Should-6**: `./start-services.sh && ./scripts/health-check.sh` pass; all SLICE-14 ACs unmodified
- [ ] **GWT Should-7**: Docs-only PR → `docker-build` job absent from CI run
- [ ] **GWT Should-8**: Docker-touching PR → `docker-build` job passes
- [ ] **GWT Should-9**: Second CI run on same branch → measurably faster (GHA cache hit logged)
- [ ] `./scripts/quality-gates.sh` passes (no regressions)
- [ ] `docker compose config` validates (no broken references in compose files after Dockerfile restructure)
- [ ] Specification coverage: every GWT clause above has ≥1 verification step documented

---

## Doc Audit

| Doc | Change needed? |
|-----|---------------|
| `docs/contributor-guide/development.md` | Could: add short "Docker build architecture" section explaining deps/runtime stage split |
| `docs/contributor-guide/architecture.md` | No change (Docker internals not covered there) |
| `CLAUDE.md` Docker section | No change (start-services.sh commands unchanged) |
| `CHANGELOG.md` | Add entry under `## [Unreleased]` when slice ships |

---

## Risks

| Risk | Mitigation |
|------|------------|
| `uv` editable install (`-e .`) may not carry over cleanly to a copy-based runtime stage | Before-Check spike verifies `uv sync --frozen --no-install-project` or equivalent; runtime stage uses `COPY --from=deps /opt/venv` + plain `PYTHONPATH` if editable semantics not needed in prod |
| BuildKit cache mounts require Buildx | Already default for Docker Desktop / modern Docker Engine; `setup-buildx-action` added in CI job |
| nginx:alpine swap changes prod frontend runtime | Dev overlay (`frontend.dev.Dockerfile`) is unaffected; prod is static-asset serving only, behaviour identical |
| CI job adds runner minutes | Path-scoped — only runs on Docker-relevant changes; non-blocking at first landing |
| Postgres Docker profile (Slice 37) adds services later | Layering changes are additive; new Postgres service entry in `docker-compose.yml` requires no change to these Dockerfiles |

---

## Gate Status

📋 PLANNED — not yet branched. Branch when Slice 41A closes or user prioritises this ahead of Supabase migration slices.
