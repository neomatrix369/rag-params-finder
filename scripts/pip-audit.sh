#!/bin/bash
# Python dependency audit — ignores transitive ML stack vulns tracked for upgrade.
# Fixable direct deps are upgraded via [tool.uv] override-dependencies in pyproject.toml.
#
# SCA waiver parity (same congruent-lock blockers):
#   .trivyignore  — Trivy container/image scan
#   .meterian     — Meterian nightly + local security-scan.sh
#   this script   — pip-audit in quality-gates / CI dependency-audit
# Unblock conditions: docs/plan/TRAIL.md § Deferred Work.
#
# Usage: ./scripts/pip-audit.sh

set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# torch/transformers via sentence-transformers — major upgrade deferred (see pyproject.toml comment).
# Model IDs are validated against server/core/model_registry.py; arbitrary model repositories are rejected.
# PYSEC-2026-2286: patched torch has no macOS x86_64 wheel; retain the last supported wheel only there.
# PYSEC-2026-2290: LightGlue-only path is unused; patched transformers requires the deferred ST 4+ upgrade.
# aim — no installable fixed release (CVE-2025-5321, CVE-2025-51464; PyPI aim 4.0.x yanked).
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
  --ignore-vuln CVE-2026-4372    # transformers via sentence-transformers — major upgrade deferred
  --ignore-vuln PYSEC-2026-2286  # torch — no patched macOS x86_64 wheel; allowlisted models only
  --ignore-vuln CVE-2025-32434   # torch 2.2.2 RCE via torch.load — blocked on ST<4 + macOS x86_64 wheel; allowlisted models only
  --ignore-vuln PYSEC-2026-2290  # transformers — unused LightGlue path; ST major upgrade required
)

# Prefer the project venv whenever it exists. A bare `command -v python` is unsafe
# under pyenv: with VIRTUAL_ENV set, `pip-audit` may resolve to `.venv/bin/pip-audit`
# while `python` still resolves to the pyenv shim — auditing the wrong environment
# and producing a flood of false positives. CI without a local `.venv` falls through
# to the hosted interpreter that supplied pip-audit.
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  AUDIT_PYTHON="$ROOT/.venv/bin/python"
  if [[ -x "$ROOT/.venv/bin/pip-audit" ]]; then
    AUDIT_COMMAND=("$ROOT/.venv/bin/pip-audit")
  else
    AUDIT_COMMAND=(uv run pip-audit)
  fi
elif command -v pip-audit >/dev/null 2>&1; then
  AUDIT_PYTHON="$(command -v python)"
  AUDIT_COMMAND=(pip-audit)
else
  echo "error: project .venv missing and pip-audit not on PATH" >&2
  exit 1
fi

PIPAPI_PYTHON_LOCATION="$AUDIT_PYTHON" "${AUDIT_COMMAND[@]}" --skip-editable "${ML_IGNORE[@]}"
