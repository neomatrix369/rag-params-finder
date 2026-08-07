#!/usr/bin/env bash
# Produce language-specific complexity evidence for local gates and pull requests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="$ROOT/.reports/complexity"
PYTHON_PATHS="${COMPLEXITY_PYTHON_PATHS:-server cli}"
NODE_WORKSPACES="${COMPLEXITY_NODE_WORKSPACES:-frontend}"
mkdir -p "$REPORT_DIR"

python_report="$REPORT_DIR/python-radon.json"
cli_report="$REPORT_DIR/node-eslint.json"

if [[ -f "$ROOT/pyproject.toml" ]]; then
  echo "--- Python complexity (Radon) ---"
  # shellcheck disable=SC2086 # project config supplies a deliberate path list
  uv run radon cc --json $PYTHON_PATHS >"$python_report"
else
  printf '{}\n' >"$python_report"
fi

printf '[]\n' >"$cli_report"
for workspace in $NODE_WORKSPACES; do
  workspace_path="$ROOT/$workspace"
  [[ -f "$workspace_path/package.json" ]] || continue
  [[ -f "$workspace_path/eslint.complexity.config.cjs" ]] || {
    echo "Missing $workspace/eslint.complexity.config.cjs" >&2
    exit 2
  }
  echo "--- JavaScript/TypeScript complexity ($workspace) ---"
  workspace_report="$REPORT_DIR/node-${workspace//\//_}.json"
  (
    cd "$workspace_path"
    # Exit code 1 = violations found (expected for reporting); allow it.
    npx eslint --config eslint.complexity.config.cjs --format json . \
      --ignore-pattern node_modules --ignore-pattern dist --ignore-pattern coverage || true
  ) >"$workspace_report"
  python3 - "$cli_report" "$workspace_report" <<'PY'
import json
import sys
from pathlib import Path

combined_path, workspace_path = map(Path, sys.argv[1:])
combined = json.loads(combined_path.read_text(encoding="utf-8"))
workspace = json.loads(workspace_path.read_text(encoding="utf-8"))
combined_path.write_text(json.dumps([*combined, *workspace]), encoding="utf-8")
PY
done

python3 "$(dirname "${BASH_SOURCE[0]}")/write_complexity_summary.py" \
  --python-report "$python_report" \
  --node-report "$cli_report" \
  --output "$REPORT_DIR/pr-body.md"

echo "Complexity report: $REPORT_DIR/pr-body.md"
