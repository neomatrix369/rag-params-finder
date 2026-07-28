#!/usr/bin/env bash
# Compatibility shim — prefer docker/wait-experiment.sh
# Deprecated: remove after next minor (Slice 45 scripts theme folders).
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker/wait-experiment.sh" "$@"
