#!/bin/bash
# Repo-wide linters (shell, GitHub Actions, Markdown) — same hooks as pre-commit / CI.
set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

run_precommit_hook() {
  local hook_id="$1"
  if command -v pre-commit >/dev/null 2>&1; then
    pre-commit run "$hook_id" --all-files
  elif uv run pre-commit run "$hook_id" --all-files 2>/dev/null; then
    :
  else
    echo "pre-commit is required for repo lint (uv pip install -e \".[dev]\")" >&2
    exit 1
  fi
}

echo "=== Repo lint (shellcheck, actionlint, markdownlint) ==="

echo ""
echo "Shellcheck (scripts/*.sh)..."
run_precommit_hook shellcheck

echo ""
echo "Actionlint (.github/workflows)..."
run_precommit_hook actionlint

echo ""
echo "Markdownlint (*.md)..."
run_precommit_hook markdownlint

echo ""
echo "✅ Repo lint passed."
