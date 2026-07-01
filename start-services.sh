#!/bin/bash
# Start rag-params-finder server + dashboard via Docker Compose (prod stack)
# Usage:
#   ./start-services.sh [--force-build] [--local]     Start full stack
#   ./start-services.sh mongodb start|stop|reset|status   MongoDB Atlas Local container only
#   Env: RAG_FORCE_BUILD=1, RAG_DEV_STACK=1, RAG_LOCAL_ATLAS=1, NONINTERACTIVE=1
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/docker-cleanup.sh
source ./scripts/docker-cleanup.sh
# shellcheck source=scripts/docker-build-context.sh
source ./scripts/docker-build-context.sh
# shellcheck source=scripts/lib/compose.sh
source ./scripts/lib/compose.sh

FORCE_BUILD=0
LOCAL_ATLAS=0

usage() {
  cat <<EOF
Usage: ./start-services.sh [OPTIONS]
       ./start-services.sh mongodb start|stop|reset|status

Start server + dashboard via Docker Compose (default), or manage MongoDB Atlas Local only.

Stack options:
  --local, -l                  Use MongoDB Atlas Local (no cloud account needed)
  --force-build, --build, -b   Rebuild images even when build context is unchanged
  -h, --help                   Show this help

MongoDB container only (Atlas Local Docker):
  mongodb start                Start mongodb-local container
  mongodb stop                 Stop container
  mongodb reset                Stop + wipe data volume
  mongodb status               Container state + CLI connection string

Environment:
  RAG_LOCAL_ATLAS=1            Same as --local
  RAG_FORCE_BUILD=1            Same as --force-build
  RAG_DEV_STACK=1              Dev overlay (HMR + uvicorn --reload)
  NONINTERACTIVE=1             Fail fast on missing .env / port conflicts

Backends:
  Cloud (default):  requires MONGODB_URI in .env (mongodb+srv://...)
  Local (--local):  starts mongodb-atlas-local container; no .env MONGODB_URI needed
                    CLI: export MONGODB_URI="$RAG_LOCAL_MONGODB_URI_HOST"
EOF
}

cmd_mongodb_start() {
  echo "Starting MongoDB Atlas Local..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" up -d mongodb-local
  echo ""
  echo "Waiting for MongoDB Atlas Local to be ready..."
  wait_for_mongodb_local_healthy
  print_local_atlas_cli_hints 1
}

cmd_mongodb_stop() {
  echo "Stopping MongoDB Atlas Local..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" stop mongodb-local
  echo "Stopped."
}

cmd_mongodb_reset() {
  echo "Stopping and wiping MongoDB Atlas Local data volume..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" rm -sf mongodb-local
  docker volume rm "$RAG_MONGODB_LOCAL_VOLUME" 2>/dev/null || true
  echo "Volume wiped. Run './start-services.sh mongodb start' to recreate."
}

cmd_mongodb_status() {
  local state
  state="$(docker inspect --format='{{.State.Status}}' "$RAG_MONGODB_LOCAL_CONTAINER" 2>/dev/null || echo "not found")"
  local health
  health="$(docker inspect --format='{{.State.Health.Status}}' "$RAG_MONGODB_LOCAL_CONTAINER" 2>/dev/null || echo "—")"
  echo "Container: $RAG_MONGODB_LOCAL_CONTAINER"
  echo "  State:  $state"
  echo "  Health: $health"
  if [[ "$state" == "running" && "$health" == "healthy" ]]; then
    print_local_atlas_cli_hints 1
  fi
}

run_mongodb_subcommand() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. See https://docs.docker.com/get-docker/" >&2
    exit 1
  fi
  compose_detect
  compose_files
  compose_local_atlas_profiles

  local cmd="${1:-start}"
  case "$cmd" in
    start)  cmd_mongodb_start ;;
    stop)   cmd_mongodb_stop ;;
    reset)  cmd_mongodb_reset ;;
    status) cmd_mongodb_status ;;
    *)
      echo "Unknown mongodb command: $cmd" >&2
      echo "Usage: ./start-services.sh mongodb [start|stop|reset|status]" >&2
      exit 1
      ;;
  esac
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --local | -l)
        LOCAL_ATLAS=1
        shift
        ;;
      --force-build | --build | -b)
        FORCE_BUILD=1
        shift
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1 (try --help)" >&2
        exit 1
        ;;
    esac
  done
  if [[ "${RAG_FORCE_BUILD:-}" == "1" ]]; then
    FORCE_BUILD=1
  fi
  if [[ "${RAG_LOCAL_ATLAS:-}" == "1" ]]; then
    LOCAL_ATLAS=1
  fi
  export FORCE_BUILD LOCAL_ATLAS
}

if [[ "${1:-}" == "mongodb" ]]; then
  shift
  run_mongodb_subcommand "${1:-start}"
  exit 0
fi

parse_args "$@"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. See https://docs.docker.com/get-docker/" >&2
  exit 1
fi

compose_detect
compose_files
PROFILES=()

if [[ "${RAG_DEV_STACK:-}" == "1" ]]; then
  echo "Dev stack enabled (RAG_DEV_STACK=1) — HMR + uvicorn --reload"
fi

if [[ "$LOCAL_ATLAS" == "1" ]]; then
  compose_export_local_atlas_env
  compose_local_atlas_profiles
  PROFILES+=("${COMPOSE_PROFILES[@]}")
  echo "Local Atlas enabled (--local) — mongodb-atlas-local container, no cloud account needed"
else
  compose_clear_local_atlas_env
fi

ensure_env() {
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      if [[ "${NONINTERACTIVE:-}" == "1" ]]; then
        echo "Missing .env — copy .env.example and set MONGODB_URI." >&2
        exit 1
      fi
      cp .env.example .env
      echo "Created .env from .env.example — edit MONGODB_URI, then re-run."
      exit 1
    fi
    echo "Missing .env file." >&2
    exit 1
  fi

  # shellcheck disable=SC1091
  set -a
  source .env
  set +a

  # Local Atlas: server MONGODB_URI is set via RAG_SERVER_MONGODB_URI env (compose_export_local_atlas_env).
  # Cloud Atlas: .env MONGODB_URI must be a real connection string.
  if [[ "$LOCAL_ATLAS" == "0" ]]; then
    if [[ -z "${MONGODB_URI:-}" ]] || [[ "$MONGODB_URI" == *"your_mongodb_atlas_uri_here"* ]]; then
      echo "Set a real MONGODB_URI in .env (Atlas connection string), or use --local for local dev." >&2
      exit 1
    fi
  fi
}

check_ports() {
  # Ports are chosen to avoid common conflicts:
  #   8001 — backend  (uncommon; not a standard framework default)
  #   5374 — frontend (avoids 5173 which is Vite's own default, shared by every Vite project)
  #   8720 — SIE      (avoids 8080 used by Jenkins, Tomcat, Hadoop, Spark, etc.)
  #   27017 — MongoDB (local Atlas only)
  local ports=(8001 5374)
  if [[ "$LOCAL_ATLAS" == "1" ]]; then
    ports+=(27017)
  fi
  local conflicts=()
  for port in "${ports[@]}"; do
    if lsof -ti:"$port" >/dev/null 2>&1; then
      conflicts+=("$port")
    fi
  done
  if [[ ${#conflicts[@]} -eq 0 ]]; then
    return 0
  fi
  echo "Port conflict on: ${conflicts[*]}"
  if [[ "${NONINTERACTIVE:-}" == "1" ]]; then
    echo "Stop processes on those ports or set NONINTERACTIVE=0 for interactive menu." >&2
    exit 1
  fi
  echo "1) Try to free ports (kill listeners)  2) Exit"
  read -r -p "Choice [1/2]: " choice
  case "$choice" in
    1)
      # First try a clean docker compose down — avoids killing Docker's own port proxies on macOS
      if "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" down 2>/dev/null; then
        echo "Stopped existing containers."
      fi
      # Kill any remaining non-Docker processes still holding the ports
      for port in "${conflicts[@]}"; do
        if lsof -ti:"$port" >/dev/null 2>&1; then
          lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
        fi
      done
      ;;
    *)
      exit 1
      ;;
  esac
}

print_unhealthy_server_hint() {
  echo ""
  echo "Server did not become healthy (frontend waits on server healthcheck)."
  echo "Diagnose:"
  echo "  curl -s http://localhost:8001/healthz"
  echo "  docker logs rag-params-finder-server 2>&1 | tail -30"
  echo ""
  if [[ "$LOCAL_ATLAS" == "1" ]]; then
    echo "Local Atlas hints:"
    echo "  docker logs rag-params-finder-mongodb-local 2>&1 | tail -20"
    echo "  ./start-services.sh mongodb status"
  else
    echo "Common Atlas fixes (TLS/SSL errors affect host and Docker alike):"
    echo "  • Network Access → allow your IP (curl https://api.ipify.org) or 0.0.0.0/0 for dev"
    echo "  • Database Access → user/password in .env must match Atlas"
    echo "  • Cluster must not be paused"
    echo "Docs: docs/user-guide/troubleshooting.md (Docker section)"
  fi
}

mkdir -p input_data/pdfs configs

ensure_env
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  export GIT_COMMIT="$(git rev-parse --short HEAD)"
  export GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi
docker_cleanup standard
check_ports

UP_ARGS=(-d)
if docker_compose_needs_build "$SCRIPT_DIR"; then
  echo "Building and starting containers..."
  UP_ARGS=(--build -d)
else
  echo "Starting containers (reusing existing images)..."
fi
if ! "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${PROFILES[@]}" up "${UP_ARGS[@]}"; then
  print_unhealthy_server_hint
  exit 1
fi

echo "Waiting for services to become healthy..."
sleep 15

if [[ -x ./scripts/health-check.sh ]]; then
  if ! ./scripts/health-check.sh; then
    print_unhealthy_server_hint
    exit 1
  fi
else
  if ! curl -sf http://localhost:8001/healthz >/dev/null; then
    print_unhealthy_server_hint
    exit 1
  fi
  curl -sf http://localhost:5374/ >/dev/null
fi

echo ""
echo "Services ready:"
echo "  Server:    http://localhost:8001  (docs: /docs)"
echo "  Dashboard: http://localhost:5374"

if [[ "$LOCAL_ATLAS" == "1" ]]; then
  echo "  MongoDB:   localhost:27017  (Atlas Local — no cloud quota)"
  echo ""
  echo "CLI (local Atlas — set URI for host commands):"
  echo "  export MONGODB_URI=\"$RAG_LOCAL_MONGODB_URI_HOST\""
  echo "  rag-params-finder run --config configs/example-mongodb-local.yaml"
  echo ""
  echo "Switch back to cloud:  ./start-services.sh  (no --local flag)"
  echo "Manage MongoDB only:   ./start-services.sh mongodb [start|stop|reset|status]"
  echo "Reset all data:        docker compose --profile local-atlas down -v"
else
  echo ""
  echo "CLI:       rag-params-finder run --config configs/example-mongodb-local.yaml"
  echo ""
  echo "Switch to local Atlas: ./start-services.sh --local  (no cloud account needed)"
fi

echo ""
echo "SIE (BGE-M3): not started — opt-in only (SIE_ENABLED=false by default)."
echo "  To enable: docs/user-guide/sie-setup.md"
echo "  CLI sweep: rag-params-finder run --config configs/example-mongodb-sie.yaml"
echo ""
echo "Aim UI:      ./scripts/aim-ui.sh  → http://localhost:43800 (experiment runs in ./.aim)"
echo ""
echo "Dev stack:   RAG_DEV_STACK=1 ./start-services.sh [--local]"
echo "Force build: ./start-services.sh --force-build [--local]"
