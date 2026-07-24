# FastAPI server — Python 3.12 + uv
# Multi-stage: deps stage installs packages in isolation; runtime stage copies the environment
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS deps

WORKDIR /app

# Install system build dependencies (only needed for compilation)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only dependency files (pyproject.toml and uv.lock)
# This layer is cached as long as dependencies don't change
COPY pyproject.toml uv.lock ./

# Install dependencies into /opt/venv
# The cache mount ensures pip packages are cached between builds
# Using uv sync --frozen --no-install-project means:
# - --frozen: exact versions from uv.lock
# - --no-install-project: don't install the package itself yet (we'll do that in runtime stage with full source)
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-install-project --python ${PYTHON_VERSION} --python-preference=only-system

# Runtime stage — minimal, compiler-free
FROM python:${PYTHON_VERSION}-slim

ARG GIT_COMMIT=unknown
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

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
