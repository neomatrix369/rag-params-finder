#!/bin/bash
# Setup router — Docker-first when available, else manual dev instructions
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${1:-}" == "--manual" ]]; then
  echo "Manual setup:"
  echo "  uv venv && source .venv/bin/activate"
  echo "  uv pip install -e \".[dev]\""
  echo "  bash scripts/install-git-hooks.sh"
  echo "  cd frontend && npm install && cd .."
  echo "  cp .env.example .env   # set MONGODB_URI"
  echo ""
  echo "Run:"
  echo "  uvicorn server.main:app --reload --port 8001"
  echo "  cd frontend && npm run dev"
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  exec ./start-services.sh "$@"
fi

echo "Docker not found — use manual setup:"
exec "$0" --manual
