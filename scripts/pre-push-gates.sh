#!/bin/bash
# Pre-push gates — only checks that did NOT already run at commit stage.
#
# Commit stage covers: hygiene, gitleaks, ruff lint+format, mypy, bandit,
#   shell/action/markdown lint, eslint, tsc+build, fast tests (testmon).
#
# This script adds what commits cannot provide:
#   - Full test suite + coverage (only when server/|cli/|tests/|pyproject.toml|uv.lock changed)
#   - pip-audit (only when uv.lock or pyproject.toml changed)
#   - vitest + vite build (only when frontend/ files changed)
#   - npm audit (only when frontend/package*.json changed)
#
# Path sets mirror ci.yml dorny/paths-filter definitions (backend / deps / frontend).
set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# pre-commit sets FROM_REF/TO_REF when running as a hook
FROM_REF="${PRE_COMMIT_FROM_REF:-}"
TO_REF="${PRE_COMMIT_TO_REF:-HEAD}"

changed_since_last_push() {
  if [[ -n "$FROM_REF" && "$FROM_REF" != "0000000000000000000000000000000000000000" ]]; then
    git diff --name-only "$FROM_REF" "$TO_REF" 2>/dev/null || echo ""
  else
    git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only --cached 2>/dev/null || echo ""
  fi
}

CHANGED=$(changed_since_last_push)

# Conservative fallback: if change detection fails, run all checks
if [[ -z "$CHANGED" ]]; then
  echo "⚠️  Warning: could not detect changed files — running all checks (conservative fallback)."
  BACKEND_CHANGED=1
  BACKEND_LOCK_CHANGED=1
  FRONTEND_CHANGED=1
  FRONTEND_LOCK_CHANGED=1
else
  # Mirror ci.yml dorny/paths-filter path sets exactly
  BACKEND_CHANGED=$(echo "$CHANGED" | grep -cE "^(server/|cli/|tests/|pyproject\.toml|uv\.lock)" 2>/dev/null || true)
  BACKEND_LOCK_CHANGED=$(echo "$CHANGED" | grep -cE "^(uv\.lock|pyproject\.toml)$" 2>/dev/null || true)
  FRONTEND_CHANGED=$(echo "$CHANGED" | grep -c "^frontend/" 2>/dev/null || true)
  FRONTEND_LOCK_CHANGED=$(echo "$CHANGED" | grep -cE "^frontend/package(-lock)?\.json$" 2>/dev/null || true)
fi

echo "=== Pre-push gates (push-specific checks) ==="

echo ""
echo "1/3 Full test suite + coverage..."
if [[ "$BACKEND_CHANGED" -gt 0 ]]; then
  uv run pytest --tb=short -q \
    --cov=server.core.search_index_plan \
    --cov=server.core.search_index_guard \
    --cov=server.core.results_analyzer \
    --cov=server.models.config \
    --cov-report=term-missing \
    --cov-fail-under=80
else
  echo "   Skipped (no backend changes in this push)"
fi

echo ""
echo "2/3 Python dependency audit (pip-audit)..."
if [[ "$BACKEND_LOCK_CHANGED" -gt 0 ]]; then
  bash scripts/pip-audit.sh
else
  echo "   Skipped (no backend lockfile changes in this push)"
fi

echo ""
echo "3/3 Frontend build + tests + audit..."
if [[ "$FRONTEND_CHANGED" -gt 0 ]]; then
  npm --prefix frontend run build
  npm --prefix frontend run test
  if [[ "$FRONTEND_LOCK_CHANGED" -gt 0 ]]; then
    npm --prefix frontend audit --audit-level=high
  else
    echo "   npm audit: skipped (no frontend lockfile changes)"
  fi
else
  echo "   Skipped (no frontend/ changes in this push)"
fi

echo ""
echo "✅ Pre-push gates passed."
