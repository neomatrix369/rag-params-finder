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
# aim — no upstream fix available yet (CVE-2025-5321, CVE-2025-51464).
# langchain/langsmith/langgraph — fix requires langsmith>=0.8.18 which needs websockets>=15,
#   but sie-sdk pins websockets<15; blocked on sie-sdk upgrading its websockets constraint.
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
  --ignore-vuln PYSEC-2025-217
  --ignore-vuln CVE-2026-1839
  --ignore-vuln CVE-2025-2148
  --ignore-vuln CVE-2025-2149
  --ignore-vuln CVE-2025-2998
  --ignore-vuln CVE-2025-2999
  --ignore-vuln CVE-2025-3000
  --ignore-vuln CVE-2025-3001
  --ignore-vuln CVE-2025-5321
  --ignore-vuln CVE-2025-51464
  --ignore-vuln GHSA-gr75-jv2w-4656
  --ignore-vuln GHSA-f4xh-w4cj-qxq8
  --ignore-vuln CVE-2026-48775
  --ignore-vuln CVE-2026-48776
  --ignore-vuln PYSEC-2026-597   # nltk — semantic/sentence chunkers; no fix in current pin
  --ignore-vuln CVE-2026-4372    # transformers via sentence-transformers — major upgrade deferred
)

uv run pip-audit --skip-editable "${ML_IGNORE[@]}"
