#!/bin/bash
# Run all quality gates — mirrors .github/workflows/ci.yml (repo-lint + backend + frontend + audits).
# Usage:
#   ./scripts/quality-gates.sh          # full CI mirror (default)
#   ./scripts/quality-gates.sh --quick  # fast gates (git push via scripts/pre-push-gates.sh)
#   ./scripts/quality-gates.sh --full   # CI mirror + local gitleaks + pre-commit all-files

set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="default"
if [[ "${1:-}" == "--quick" ]]; then
  MODE="quick"
elif [[ "${1:-}" == "--full" ]]; then
  MODE="full"
fi

echo "=== Quality Gates (rag-params-finder) ==="

echo ""
echo "1/11 Repo lint (shellcheck, actionlint, markdownlint)..."
bash scripts/repo-lint.sh

echo ""
echo "2/11 Backend lint (ruff)..."
uv run ruff check .

echo ""
echo "3/11 Backend format (ruff)..."
uv run ruff format --check .

echo ""
echo "4/11 Backend type check (mypy)..."
uv run mypy server/ cli/

echo ""
echo "5/11 Backend SAST (bandit, medium+ severity)..."
uv run bandit -c pyproject.toml -r server/ cli/ -q -ll

if [[ "${MODE}" == "quick" ]]; then
  echo ""
  echo "6/9 Backend unit tests (no coverage)..."
  uv run pytest --tb=short -q -m "not integration"
  echo ""
  echo "7/9 Frontend lint (eslint)..."
  npm --prefix frontend run lint
  echo ""
  echo "8/9 Frontend verify (tsc + production build)..."
  npm --prefix frontend run verify
  echo ""
  echo "9/9 Secrets scan (gitleaks)..."
  if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --config .gitleaks.toml --verbose
  else
    echo "⚠️  gitleaks not installed — skip (brew install gitleaks)"
  fi
  echo ""
  echo "✅ Quick quality gates passed."
  echo "   (repo lint, ruff, mypy, bandit, pytest, frontend lint+verify, gitleaks)"
  echo "   Skipped: coverage, pip-audit, npm audit — run ./scripts/quality-gates.sh before a PR."
  exit 0
fi

echo ""
echo "6/11 Backend tests + coverage..."
uv run pytest --tb=short -q --cov=server.core.search_index_plan \
  --cov=server.core.search_index_guard \
  --cov=server.core.results_analyzer \
  --cov=server.models.config \
  --cov-report=term-missing \
  --cov-fail-under=80

echo ""
echo "7/11 Python dependency audit (pip-audit)..."
bash scripts/pip-audit.sh

echo ""
echo "8/11 Frontend lint + typecheck + build..."
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build

echo ""
echo "9/11 Frontend security audit..."
npm --prefix frontend audit --audit-level=high

if [[ "${MODE}" == "full" ]]; then
  echo ""
  echo "10/11 Full: gitleaks (with .gitleaks.toml)..."
  if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --config .gitleaks.toml --verbose
  else
    echo "⚠️  gitleaks not installed — skip (brew install gitleaks)"
  fi

  echo ""
  echo "11/11 Full: pre-commit all files..."
  if command -v pre-commit >/dev/null 2>&1; then
    pre-commit run --all-files
  else
    echo "⚠️  pre-commit not installed — skip (uv pip install pre-commit)"
  fi
fi

echo ""
echo "✅ All quality gates passed!"
echo "Safe to commit and push."
