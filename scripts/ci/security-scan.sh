#!/usr/bin/env bash
# Compatibility shim — delegates to scripts/security/security-scan.sh
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/security/security-scan.sh" "$@"
