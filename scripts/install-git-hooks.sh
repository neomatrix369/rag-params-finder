#!/bin/bash
# Install pre-commit and pre-push hooks (essential checks on commit and push).
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
echo "   pre-commit  → essential checks on staged files (hygiene, secrets, lint, types, …)"
echo "   pre-push    → same essential checks on entire repo (pre-commit run --all-files)"
echo ""
echo "Full CI mirror (pytest, coverage, audits, build): ./scripts/quality-gates.sh"
echo "Bypass once (emergency only): git push --no-verify"
