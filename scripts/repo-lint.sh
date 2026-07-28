#!/usr/bin/env bash
# Compatibility shim — prefer ci/repo-lint.sh
# Deprecated: remove after next minor (Slice 45 scripts theme folders).
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ci/repo-lint.sh" "$@"
