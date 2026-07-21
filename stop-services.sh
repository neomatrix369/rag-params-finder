#!/bin/bash
# Stop rag-params-finder Docker stack
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/docker-cleanup.sh
source ./scripts/docker-cleanup.sh
# shellcheck source=scripts/lib/compose.sh
source ./scripts/lib/compose.sh

compose_detect
compose_files
if compose_local_atlas_active; then
  compose_local_atlas_profiles
  COMPOSE_DOWN_PROFILES=("${COMPOSE_PROFILES[@]}")
else
  COMPOSE_DOWN_PROFILES=()
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
    "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_DOWN_PROFILES[@]}" down
    docker_cleanup silent
    ;;
  2)
    "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_DOWN_PROFILES[@]}" stop
    ;;
  3)
    if [[ "${NONINTERACTIVE:-}" != "1" ]]; then
      echo "Type DELETE HF CACHE to remove HuggingFace model cache volume (cloud Atlas data unaffected)."
      read -r confirm
      if [[ "$confirm" == "DELETE HF CACHE" ]]; then
        "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_DOWN_PROFILES[@]}" down -v
      else
        "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_DOWN_PROFILES[@]}" down
      fi
    else
      "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_DOWN_PROFILES[@]}" down
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
