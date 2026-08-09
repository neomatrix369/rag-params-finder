#!/usr/bin/env bash
# Shim — delegates to scripts/ci/complexity-report.sh (canonical location)
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ci/complexity-report.sh" "$@"
