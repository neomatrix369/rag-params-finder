#!/bin/bash
# Fast gates on git push — mirrors pre-rag-explorer-dashboard Husky → npm run test:all.
# See scripts/quality-gates.sh --quick for the step list.
set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$ROOT/scripts/quality-gates.sh" --quick
