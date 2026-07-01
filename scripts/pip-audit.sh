#!/bin/bash
# Python dependency audit — ignores transitive ML stack vulns tracked for upgrade.
# Fixable direct deps are upgraded via [tool.uv] override-dependencies in pyproject.toml.
#
# Usage: ./scripts/pip-audit.sh

set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# torch/transformers via sentence-transformers — major upgrade deferred (see pyproject.toml comment).
# pip tool itself — PYSEC-2026-196 fix is 26.1.2; upgrade with: uv pip install --upgrade pip
ML_IGNORE=(
  --ignore-vuln PYSEC-2025-41
  --ignore-vuln PYSEC-2024-259
  --ignore-vuln PYSEC-2025-205
  --ignore-vuln PYSEC-2025-206
  --ignore-vuln PYSEC-2025-207
  --ignore-vuln PYSEC-2025-204
  --ignore-vuln PYSEC-2026-139
  --ignore-vuln PYSEC-2025-209
  --ignore-vuln PYSEC-2025-208
  --ignore-vuln PYSEC-2025-191
  --ignore-vuln PYSEC-2025-198
  --ignore-vuln PYSEC-2025-203
  --ignore-vuln CVE-2025-3730
  --ignore-vuln CVE-2025-2148
  --ignore-vuln PYSEC-2025-217
  --ignore-vuln CVE-2026-1839
  --ignore-vuln PYSEC-2026-196
)

uv run pip-audit --skip-editable "${ML_IGNORE[@]}"
