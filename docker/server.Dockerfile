# FastAPI server — Python 3.12 + uv
# Multi-stage: deps stage installs packages in isolation; runtime stage copies the environment
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS deps

WORKDIR /app

# Install system build dependencies (only needed for compilation, not in runtime stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only dependency files (pyproject.toml and uv.lock)
# This layer is cached as long as dependencies don't change
COPY pyproject.toml uv.lock ./

# Install all deps from lock file (cached unless pyproject.toml/uv.lock changes).
# On aarch64 (Apple Silicon / ARM CI), torch from PyPI is already CPU-only (~82 MB).
# On x86_64 production hosts, torch from PyPI ships with CUDA; a future slice can
# add the pytorch-cpu index override via [tool.uv.sources] once x86_64 CI is needed.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project --python ${PYTHON_VERSION} --python-preference=only-system

# Runtime stage — minimal, compiler-free
FROM python:${PYTHON_VERSION}-slim

ARG GIT_COMMIT=unknown
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

# curl needed for HEALTHCHECK only (not for build toolchain)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from deps stage
# This brings in all installed packages without the build tools
COPY --from=deps /app/.venv /app/.venv

# Set PATH to use the venv; PYTHONPATH lets uvicorn find server/cli packages directly
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy source code — no install step needed: packages are importable via PYTHONPATH
COPY pyproject.toml README.md ./
COPY server ./server
COPY cli ./cli

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
  CMD curl -f http://localhost:8001/healthz || exit 1

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]
