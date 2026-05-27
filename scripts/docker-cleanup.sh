#!/bin/bash
# Shared Docker prune helpers for start-services.sh and stop-services.sh
set -e
set -o pipefail

docker_cleanup() {
  local mode="${1:-standard}"

  case "$mode" in
    silent)
      docker container prune -f >/dev/null 2>&1 || true
      ;;
    standard)
      echo "Cleaning exited containers..."
      docker container prune -f
      ;;
    aggressive)
      echo "Aggressive cleanup: containers, dangling images, unused networks..."
      docker container prune -f
      docker image prune -f
      docker network prune -f
      ;;
    *)
      echo "Unknown docker_cleanup mode: $mode" >&2
      return 1
      ;;
  esac
}
