#!/bin/bash
# Start Aim experiment UI (port 43800) via Docker — shares ./.aim with the server.
#
# Host `aim up` often fails on macOS (cryptography/OpenSSL _BIO_ADDR_free). The Docker
# path uses the same server image where Aim UI is verified to work.
#
# Usage:
#   ./scripts/aim-ui.sh          # start aim-ui container
#   ./scripts/aim-ui.sh --stop   # stop aim-ui container
set -e
set -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/lib/compose.sh
source ./scripts/lib/compose.sh

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for Aim UI. See docs/user-guide/sie-setup.md#aim-experiment-ui." >&2
  exit 1
fi

compose_detect
compose_files

mkdir -p .aim

# One-time migration: copy runs from server container if host repo is empty.
if [[ ! -f .aim/run_metadata.sqlite ]]; then
  server_cname="${SERVER_CONTAINER_NAME:-rag-params-finder-server}"
  if docker ps --format '{{.Names}}' | grep -qx "$server_cname"; then
    if docker exec "$server_cname" test -f /app/.aim/run_metadata.sqlite 2>/dev/null; then
      echo "Migrating existing Aim runs from $server_cname → ./.aim"
      docker cp "${server_cname}:/app/.aim/." .aim/
    fi
  fi
fi

if [[ "${1:-}" == "--stop" ]]; then
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" --profile aim stop aim-ui
  echo "Aim UI stopped."
  exit 0
fi

echo "Starting Aim UI (profile: aim)..."
"${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" --profile aim up -d aim-ui

echo ""
echo "Aim UI:  http://localhost:43800"
echo "Repo:    $ROOT/.aim"
echo "Stop:    ./scripts/aim-ui.sh --stop"
echo ""
echo "Runs appear after POST /api/v1/sweep or experiment pipeline completion."
