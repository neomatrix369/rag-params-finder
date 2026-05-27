#!/bin/bash
# Install pre-commit and pre-push hooks (commit checks + quality-gates --quick on push).
set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v pre-commit >/dev/null 2>&1; then
  echo "pre-commit not found. Run: uv pip install -e \".[dev]\"" >&2
  exit 1
fi

pre-commit install --hook-type pre-commit --hook-type pre-push

echo "✅ Git hooks installed:"
echo "   pre-commit  → lint/format on commit (staged files)"
echo "   pre-push    → ./scripts/quality-gates.sh --quick on every push"
echo ""
echo "Bypass once (emergency only): git push --no-verify"
