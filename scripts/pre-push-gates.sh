#!/bin/bash
# Full gates on git push — runs the complete quality-gates suite (tests, coverage, audits).
# The fast/subset mode is intentionally excluded here: every push must pass all gates.
# See scripts/quality-gates.sh for the full step list.
set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$ROOT/scripts/quality-gates.sh"
