# FastAPI server — Python 3.12 + uv
# Multi-stage layered build:
#   base-builder          — uv + build tools (shared cache stage)
#     ├── core-deps        — .venv with no extras (mongodb / postgres / sqlite)
#     ├── elasticsearch-deps — .venv with --extra elasticsearch
#     └── redis-deps       — .venv with --extra redis
#   runtime-base          — minimal Python image, source code, ENV, HEALTHCHECK, CMD
#     ├── server           — runtime-base + core-deps .venv  (default target)
#     ├── server-elasticsearch — runtime-base + elasticsearch-deps .venv
#     └── server-redis     — runtime-base + redis-deps .venv
#
# Select the final image at build time with --target (or build.target in docker-compose.yml).
# Default: server (no VDB-specific extras).

ARG PYTHON_VERSION=3.12

# ── base-builder ──────────────────────────────────────────────────────────────
# uv binary + system build tools. Nothing VDB-specific lives here.
FROM python:${PYTHON_VERSION}-slim AS base-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependency files only — this layer is cached as long as they don't change.
COPY pyproject.toml uv.lock ./

# ── core-deps ─────────────────────────────────────────────────────────────────
# Default .venv: mongodb, postgres, sqlite clients — no VDB-specific extras.
FROM base-builder AS core-deps

ARG PYTHON_VERSION=3.12
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project --python ${PYTHON_VERSION} --python-preference=only-system

# ── elasticsearch-deps ────────────────────────────────────────────────────────
FROM base-builder AS elasticsearch-deps

ARG PYTHON_VERSION=3.12
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project --extra elasticsearch \
        --python ${PYTHON_VERSION} --python-preference=only-system

# ── redis-deps ────────────────────────────────────────────────────────────────
FROM base-builder AS redis-deps

ARG PYTHON_VERSION=3.12
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project --extra redis \
        --python ${PYTHON_VERSION} --python-preference=only-system

# ── runtime-base ──────────────────────────────────────────────────────────────
# Minimal runtime image: curl (HEALTHCHECK only), ENV vars, source code.
# No .venv yet — each derived target layers its own.
FROM python:${PYTHON_VERSION}-slim AS runtime-base

ARG GIT_COMMIT=unknown
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

# curl needed for HEALTHCHECK only
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy source code — packages are importable via PYTHONPATH; no install step needed.
COPY pyproject.toml README.md ./
COPY server ./server
COPY cli ./cli

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
  CMD curl -f http://localhost:8001/healthz || exit 1

# Runs as root today (writes the ./.aim bind mount and the HuggingFace cache). Non-root switch is an owner decision tracked in
# CHANGELOG (Unreleased/Security) — needs a Docker smoke test before changing.
# nosemgrep: dockerfile.security.missing-user.missing-user
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]

# ── server (default) ──────────────────────────────────────────────────────────
# Core deps only — suitable for mongodb-local, postgres-local, sqlite, and cloud modes.
FROM runtime-base AS server

COPY --from=core-deps /app/.venv /app/.venv

# ── server-elasticsearch ──────────────────────────────────────────────────────
FROM runtime-base AS server-elasticsearch

COPY --from=elasticsearch-deps /app/.venv /app/.venv

# ── server-redis ──────────────────────────────────────────────────────────────
FROM runtime-base AS server-redis

COPY --from=redis-deps /app/.venv /app/.venv
