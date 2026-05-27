#!/bin/bash
# Run all quality gates — mirrors .github/workflows/ci.yml exactly.
# Usage: ./scripts/quality-gates.sh [--full]
#   default: fast gates (unit tests only)
#   --full:  + pre-commit all-files + pip-audit

set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FULL=0
if [[ "${1:-}" == "--full" ]]; then
  FULL=1
fi

echo "=== Quality Gates (rag-params-finder) ==="

echo ""
echo "1/7 Backend lint (ruff)..."
uv run ruff check .

echo ""
echo "2/7 Backend format (ruff)..."
uv run ruff format --check .

echo ""
echo "3/7 Backend type check (mypy)..."
uv run mypy server/ cli/

echo ""
echo "4/7 Backend tests + coverage..."
uv run pytest --tb=short -q --cov=server.core.search_index_plan \
  --cov=server.core.search_index_guard \
  --cov=server.core.results_analyzer \
  --cov=server.models.config \
  --cov-report=term-missing \
  --cov-fail-under=80

echo ""
echo "5/7 Frontend lint (eslint)..."
npm --prefix frontend run lint

echo ""
echo "6/7 Frontend typecheck + build..."
npm --prefix frontend run typecheck
npm --prefix frontend run build

echo ""
echo "7/7 Frontend security audit..."
npm --prefix frontend audit --audit-level=high

if [[ "$FULL" -eq 1 ]]; then
  echo ""
  echo "8/8 Full: Python dependency audit (pip-audit)..."
  bash scripts/pip-audit.sh

  echo ""
  echo "9/9 Full: pre-commit all files..."
  pre-commit run --all-files
fi

echo ""
echo "✅ All quality gates passed!"
echo "Safe to commit and push."
