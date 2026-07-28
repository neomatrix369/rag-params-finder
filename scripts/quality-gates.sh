#!/usr/bin/env bash
# Compatibility shim — prefer ci/quality-gates.sh
# Deprecated: remove after next minor (Slice 45 scripts theme folders).
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ci/quality-gates.sh" "$@"
