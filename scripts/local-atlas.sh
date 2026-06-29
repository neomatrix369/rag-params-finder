#!/bin/bash
# Manage the mongodb-atlas-local Docker container for local development.
#
# Usage:
#   ./scripts/local-atlas.sh            # start (default)
#   ./scripts/local-atlas.sh start      # start mongodb-local only
#   ./scripts/local-atlas.sh stop       # stop container
#   ./scripts/local-atlas.sh reset      # stop + wipe volume (fresh start)
#   ./scripts/local-atlas.sh status     # show container + connection info
#
# To start the full stack (server + dashboard + local Atlas) in one command:
#   ./start-services.sh --local
#
# CLI connection string (copy/paste or source):
#   export MONGODB_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

LOCAL_URI="mongodb://localhost:27017/rag_params_finder?directConnection=true"
CONTAINER_NAME="${MONGODB_LOCAL_CONTAINER_NAME:-rag-params-finder-mongodb-local}"
COMPOSE_FILES=(-f docker-compose.yml)
PROFILES=(--profile local-atlas)

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
else
  echo "Docker Compose not available." >&2
  exit 1
fi

_start() {
  echo "Starting MongoDB Atlas Local..."
  "${DC[@]}" "${COMPOSE_FILES[@]}" "${PROFILES[@]}" up -d mongodb-local
  echo ""
  echo "Waiting for MongoDB Atlas Local to be ready..."
  local tries=0
  until docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "healthy"; do
    tries=$((tries + 1))
    if [[ $tries -ge 30 ]]; then
      echo "Timed out waiting for $CONTAINER_NAME to become healthy." >&2
      echo "  docker logs $CONTAINER_NAME" >&2
      exit 1
    fi
    sleep 2
  done
  _print_connection_info
}

_stop() {
  echo "Stopping MongoDB Atlas Local..."
  "${DC[@]}" "${COMPOSE_FILES[@]}" "${PROFILES[@]}" stop mongodb-local
  echo "Stopped."
}

_reset() {
  echo "Stopping and wiping MongoDB Atlas Local data volume..."
  "${DC[@]}" "${COMPOSE_FILES[@]}" "${PROFILES[@]}" rm -sf mongodb-local
  docker volume rm "${COMPOSE_PROJECT_NAME:-rag-params-finder}_mongodb_local_data" 2>/dev/null || true
  echo "Volume wiped. Run './scripts/local-atlas.sh start' to recreate."
}

_status() {
  local state
  state="$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not found")"
  local health
  health="$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "—")"
  echo "Container: $CONTAINER_NAME"
  echo "  State:  $state"
  echo "  Health: $health"
  if [[ "$state" == "running" && "$health" == "healthy" ]]; then
    _print_connection_info
  fi
}

_print_connection_info() {
  echo ""
  echo "MongoDB Atlas Local is ready."
  echo ""
  echo "  Connection string (CLI / host server):"
  echo "    export MONGODB_URI=\"$LOCAL_URI\""
  echo ""
  echo "  Quick sweep:"
  echo "    MONGODB_URI=\"$LOCAL_URI\" rag-params-finder run --config configs/example-mongodb-local.yaml"
  echo ""
  echo "  Full stack with local Atlas:"
  echo "    ./start-services.sh --local"
  echo ""
  echo "  Reset data:"
  echo "    ./scripts/local-atlas.sh reset"
}

CMD="${1:-start}"
case "$CMD" in
  start)   _start ;;
  stop)    _stop ;;
  reset)   _reset ;;
  status)  _status ;;
  *)
    echo "Unknown command: $CMD" >&2
    echo "Usage: $0 [start|stop|reset|status]" >&2
    exit 1
    ;;
esac
