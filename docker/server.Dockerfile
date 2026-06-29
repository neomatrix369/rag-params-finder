# FastAPI server — Python 3.12 + uv (matches contributor docs)
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY server ./server
COPY cli ./cli

# Linux torch from PyPI pulls ~2GB NVIDIA CUDA wheels; this container has no GPU.
RUN uv pip install --system --no-cache \
    --default-index https://download.pytorch.org/whl/cpu \
    --index https://pypi.org/simple \
    --index-strategy unsafe-best-match \
    "torch==2.11.0" \
    && uv pip install --system --no-cache -e .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
  CMD curl -f http://localhost:8001/healthz || exit 1

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]
