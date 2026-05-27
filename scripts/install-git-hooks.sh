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

HOOKS_DIR="$ROOT/.git/hooks"
missing=()
for hook in pre-commit pre-push; do
  if [[ ! -x "$HOOKS_DIR/$hook" ]]; then
    missing+=("$hook")
  fi
done
if ((${#missing[@]} > 0)); then
  echo "ERROR: expected executable hooks missing: ${missing[*]}" >&2
  echo "Re-run from repo root with: bash scripts/install-git-hooks.sh" >&2
  exit 1
fi

echo "✅ Git hooks installed:"
echo "   pre-commit  → essential checks on staged files (hygiene, secrets, lint, types, …)"
echo "   pre-push    → fast gates (./scripts/pre-push-gates.sh — lint, tests, build, gitleaks)"
echo ""
echo "Full CI mirror before PR (coverage, pip-audit, npm audit): ./scripts/quality-gates.sh"
echo "Bypass once (emergency only): git push --no-verify"
