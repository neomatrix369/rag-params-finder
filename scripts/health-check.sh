#!/usr/bin/env bash
# Compatibility shim — prefer docker/health-check.sh
# Deprecated: remove after next minor (Slice 45 scripts theme folders).
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker/health-check.sh" "$@"
