#!/bin/bash
# Stop rag-params-finder Docker stack
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/docker-cleanup.sh
source ./scripts/docker-cleanup.sh

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Docker Compose is not available." >&2
  exit 1
fi

COMPOSE_FILES=(-f docker-compose.yml)
if [[ "${RAG_DEV_STACK:-}" == "1" ]]; then
  COMPOSE_FILES+=(-f docker-compose.dev.yml)
fi

echo "=== Stop rag-params-finder services ==="
"${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" ps 2>/dev/null || true
echo ""
echo "1) Standard stop (compose down, keep hf_cache volume) [default]"
echo "2) Quick pause (compose stop only)"
echo "3) Deep cleanup (down + prune images; optional hf_cache removal)"
echo ""

if [[ "${NONINTERACTIVE:-}" == "1" ]]; then
  choice=1
else
  read -r -p "Choice [1-3]: " choice
  choice="${choice:-1}"
fi

case "$choice" in
  1)
    "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" down
    docker_cleanup silent
    ;;
  2)
    "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" stop
    ;;
  3)
    if [[ "${NONINTERACTIVE:-}" != "1" ]]; then
      echo "Type DELETE HF CACHE to remove HuggingFace model cache volume (Atlas data unaffected):"
      read -r confirm
      if [[ "$confirm" == "DELETE HF CACHE" ]]; then
        "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" down -v
      else
        "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" down
      fi
    else
      "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" down
    fi
    docker_cleanup aggressive
    ;;
  *)
    echo "Invalid choice." >&2
    exit 1
    ;;
esac

echo "Done."
"${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" ps 2>/dev/null || true
