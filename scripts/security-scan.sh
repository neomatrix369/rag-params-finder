#!/usr/bin/env bash
# Compatibility shim — prefer security/security-scan.sh
# Deprecated: remove after next minor (Slice 45 scripts theme folders).
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/security/security-scan.sh" "$@"
