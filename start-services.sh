#!/bin/bash
# Start rag-params-finder server + dashboard via Docker Compose (prod stack)
# Usage:
#   ./start-services.sh [--mongodb-local|--mongodb-cloud|--postgres-local|--postgres-cloud]
#   ./start-services.sh mongodb|postgres start|stop|reset|status
#   Env: RAG_MONGODB_LOCAL=1, RAG_POSTGRES_CLOUD=1, RAG_FORCE_BUILD=1, RAG_DEV_STACK=1, NONINTERACTIVE=1
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
# shellcheck source=scripts/lib/storage_mode.sh
source ./scripts/lib/storage_mode.sh

FORCE_BUILD=0
LOCAL_ATLAS=0
LOCAL_POSTGRES=0
STACK_DB_TYPE=""
STACK_LOCATION=""
STACK_STORAGE_MODE=""

usage() {
  cat <<EOF
Usage: ./start-services.sh [OPTIONS]
       ./start-services.sh mongodb|postgres start|stop|reset|status

Start server + dashboard via Docker Compose (default), or manage a local DB container.

Stack options (pick one):
  --mongodb-local              Atlas Local container (no cloud account)
  --mongodb-cloud              Atlas cloud — requires MONGODB_URI
  --postgres-local             Local pgvector — STORAGE_BACKEND=postgres
  --postgres-cloud             Hosted Supabase — requires DATABASE_URL; no MONGODB_URI
  --local, -l                  Deprecated alias for --mongodb-local
  --postgres, -p               Deprecated alias for --postgres-local
  --force-build, --build, -b   Rebuild images even when build context is unchanged
  -h, --help                   Show this help

Container-only:
  mongodb start|stop|reset|status    Atlas Local container
  postgres start|stop|reset|status   Local pgvector container

Environment:
  RAG_MONGODB_LOCAL=1          Same as --mongodb-local
  RAG_MONGODB_CLOUD=1          Same as --mongodb-cloud
  RAG_POSTGRES_LOCAL=1         Same as --postgres-local
  RAG_POSTGRES_CLOUD=1         Same as --postgres-cloud
  RAG_LOCAL_ATLAS=1            Deprecated → --mongodb-local
  RAG_LOCAL_POSTGRES=1         Deprecated → --postgres-local
  RAG_FORCE_BUILD=1            Same as --force-build
  RAG_DEV_STACK=1              Dev overlay (HMR + uvicorn --reload)
  NONINTERACTIVE=1             Fail fast on missing .env / port conflicts

Modes (storage_mode = engine × location):
  mongodb-cloud (default bare start): requires MONGODB_URI in .env
  mongodb-local:  Atlas Local container; CLI export MONGODB_URI=$RAG_LOCAL_MONGODB_URI_HOST
  postgres-local: pgvector container; CLI export STORAGE_BACKEND=postgres DATABASE_URL=$RAG_LOCAL_DATABASE_URL_HOST
  postgres-cloud: hosted Supabase; requires DATABASE_URL; must not require MONGODB_URI
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
  echo "Stopping and wiping MongoDB Atlas Local data volumes..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" rm -sf mongodb-local
  for vol in "${RAG_MONGODB_LOCAL_VOLUMES[@]}"; do
    docker volume rm "$vol" 2>/dev/null || true
  done
  echo "Volumes wiped. Run './start-services.sh mongodb start' to recreate."
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
  compose_require_docker_daemon || exit 1
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

cmd_postgres_start() {
  echo "Starting local Postgres + pgvector..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" up -d postgres-local
  echo ""
  echo "Waiting for Postgres to be ready..."
  local tries=0
  local health=""
  while true; do
    health="$(docker inspect --format='{{.State.Health.Status}}' "$RAG_POSTGRES_LOCAL_CONTAINER" 2>/dev/null || echo "")"
    if [[ "$health" == "healthy" ]]; then
      echo ""
      print_local_postgres_cli_hints
      return 0
    fi
    if [[ "$health" == "unhealthy" || $tries -ge 60 ]]; then
      echo ""
      echo "Postgres did not become healthy." >&2
      echo "  docker logs $RAG_POSTGRES_LOCAL_CONTAINER 2>&1 | tail -20" >&2
      return 1
    fi
    tries=$((tries + 1))
    printf "."
    sleep 2
  done
}

cmd_postgres_stop() {
  echo "Stopping local Postgres..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" stop postgres-local
  echo "Stopped."
}

cmd_postgres_reset() {
  echo "Stopping and wiping local Postgres data volume..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" rm -sf postgres-local
  docker volume rm "$RAG_POSTGRES_LOCAL_VOLUME" 2>/dev/null || true
  echo "Volume wiped. Run './start-services.sh postgres start' to recreate."
}

cmd_postgres_status() {
  local state
  state="$(docker inspect --format='{{.State.Status}}' "$RAG_POSTGRES_LOCAL_CONTAINER" 2>/dev/null || echo "not found")"
  local health
  health="$(docker inspect --format='{{.State.Health.Status}}' "$RAG_POSTGRES_LOCAL_CONTAINER" 2>/dev/null || echo "—")"
  echo "Container: $RAG_POSTGRES_LOCAL_CONTAINER"
  echo "  State:  $state"
  echo "  Health: $health"
  if [[ "$state" == "running" && "$health" == "healthy" ]]; then
    print_local_postgres_cli_hints
  fi
}

run_postgres_subcommand() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. See https://docs.docker.com/get-docker/" >&2
    exit 1
  fi
  compose_require_docker_daemon || exit 1
  compose_detect
  compose_files
  compose_local_postgres_profiles

  local cmd="${1:-start}"
  case "$cmd" in
    start)  cmd_postgres_start ;;
    stop)   cmd_postgres_stop ;;
    reset)  cmd_postgres_reset ;;
    status) cmd_postgres_status ;;
    *)
      echo "Unknown postgres command: $cmd" >&2
      echo "Usage: ./start-services.sh postgres [start|stop|reset|status]" >&2
      exit 1
      ;;
  esac
}

parse_args() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi
  STACK_MODE_FROM_CLI=0
  if ! resolve_stack_mode "$@"; then
    exit 1
  fi
  # resolve_stack_mode leaves STACK_STORAGE_MODE set; treat any explicit
  # flag/env selector as CLI-owned so .env STORAGE_BACKEND cannot override it.
  if [[ "${RAG_MONGODB_LOCAL:-}${RAG_MONGODB_CLOUD:-}${RAG_POSTGRES_LOCAL:-}${RAG_POSTGRES_CLOUD:-}${RAG_LOCAL_ATLAS:-}${RAG_LOCAL_POSTGRES:-}" == *"1"* ]] \
    || [[ " $* " == *" --mongodb-"* ]] \
    || [[ " $* " == *" --postgres-"* ]] \
    || [[ " $* " == *" --local "* ]] \
    || [[ " $* " == *" -l "* ]] \
    || [[ " $* " == *" --postgres "* ]] \
    || [[ " $* " == *" -p "* ]]; then
    STACK_MODE_FROM_CLI=1
  fi
  # Also detect when resolve already left a non-default because of flags:
  # parse argv for known tokens.
  local arg
  for arg in "$@"; do
    case "$arg" in
      --mongodb-local | --mongodb-cloud | --postgres-local | --postgres-cloud | --local | -l | --postgres | -p)
        STACK_MODE_FROM_CLI=1
        ;;
    esac
  done
  export FORCE_BUILD LOCAL_ATLAS LOCAL_POSTGRES STACK_DB_TYPE STACK_LOCATION STACK_STORAGE_MODE STACK_MODE_FROM_CLI
}

if [[ "${1:-}" == "mongodb" ]]; then
  shift
  run_mongodb_subcommand "${1:-start}"
  exit 0
fi

if [[ "${1:-}" == "postgres" ]]; then
  shift
  run_postgres_subcommand "${1:-start}"
  exit 0
fi

parse_args "$@"

ensure_env() {
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      if [[ "${NONINTERACTIVE:-}" == "1" ]]; then
        echo "Missing .env — copy .env.example and set connection URIs." >&2
        exit 1
      fi
      cp .env.example .env
      echo "Created .env from .env.example — edit connection URIs, then re-run."
      exit 1
    fi
    echo "Missing .env file." >&2
    exit 1
  fi

  # shellcheck disable=SC1091
  set -a
  source .env
  set +a

  # Bare start: re-resolve from .env STORAGE_BACKEND / DATABASE_URL after load.
  if [[ "${STACK_MODE_FROM_CLI:-0}" != "1" ]]; then
    if ! resolve_stack_mode; then
      exit 1
    fi
    export FORCE_BUILD LOCAL_ATLAS LOCAL_POSTGRES STACK_DB_TYPE STACK_LOCATION STACK_STORAGE_MODE
  fi

  if ! ensure_stack_mode_env; then
    exit 1
  fi
}

apply_stack_profiles() {
  PROFILES=()
  compose_clear_local_atlas_env
  compose_clear_local_postgres_env

  if [[ "$LOCAL_ATLAS" == "1" ]]; then
    compose_export_local_atlas_env
    compose_local_atlas_profiles
    PROFILES+=("${COMPOSE_PROFILES[@]}")
    echo "Atlas Local enabled — mongodb-atlas-local container, no cloud account needed"
  fi

  if [[ "$LOCAL_POSTGRES" == "1" ]]; then
    compose_export_local_postgres_env
    compose_local_postgres_profiles
    PROFILES+=("${COMPOSE_PROFILES[@]}")
    echo "Local Postgres enabled — pgvector container, STORAGE_BACKEND=postgres"
  elif [[ "$STACK_DB_TYPE" == "postgres" ]]; then
    export STORAGE_BACKEND=postgres
    echo "Hosted Postgres enabled — STORAGE_BACKEND=postgres; requires DATABASE_URL"
  fi
}

# Validate env before requiring Docker so --postgres-cloud missing DATABASE_URL
# fails with the URI remediation instead of a daemon error.
ensure_env

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. See https://docs.docker.com/get-docker/" >&2
  exit 1
fi
compose_require_docker_daemon || exit 1

compose_detect
compose_files
PROFILES=()

if [[ "${RAG_DEV_STACK:-}" == "1" ]]; then
  echo "Dev stack enabled (RAG_DEV_STACK=1) — HMR + uvicorn --reload"
fi

apply_stack_profiles
echo "Resolved storage_mode=${STACK_STORAGE_MODE}"

check_ports() {
  # Ports are chosen to avoid common conflicts:
  #   8001 — backend  (uncommon; not a standard framework default)
  #   5374 — frontend (avoids 5173 which is Vite's own default, shared by every Vite project)
  #   8720 — SIE      (avoids 8080 used by Jenkins, Tomcat, Hadoop, Spark, etc.)
  #   27017 — MongoDB (local Atlas only)
  #   5433  — Postgres (local pgvector only; 5432 left free for a developer's own Postgres)
  local ports=(8001 5374)
  if [[ "$LOCAL_ATLAS" == "1" ]]; then
    ports+=(27017)
  fi
  if [[ "$LOCAL_POSTGRES" == "1" ]]; then
    ports+=(5433)
  fi
  local conflicts=()
  for port in "${ports[@]}"; do
    if lsof -ti:"$port" >/dev/null 2>&1; then
      # Re-use an already-running Atlas Local container (e.g. after mongodb start)
      if [[ "$port" == "27017" ]] && docker inspect --format='{{.State.Status}}' "$RAG_MONGODB_LOCAL_CONTAINER" 2>/dev/null | grep -q running; then
        continue
      fi
      if [[ "$port" == "5433" ]] && docker inspect --format='{{.State.Status}}' "$RAG_POSTGRES_LOCAL_CONTAINER" 2>/dev/null | grep -q running; then
        continue
      fi
      conflicts+=("$port")
    fi
  done
  if [[ ${#conflicts[@]} -eq 0 ]]; then
    return 0
  fi
  echo "Port conflict on: ${conflicts[*]}"
  if [[ "${NONINTERACTIVE:-}" == "1" ]]; then
    if [[ " ${conflicts[*]} " == *" 27017 "* ]]; then
      echo "Port 27017 may be held by another MongoDB or a stale rag-params-finder container." >&2
      echo "  ./start-services.sh mongodb status" >&2
      echo "  ./start-services.sh mongodb reset   # wipe and recreate local Atlas volumes" >&2
    fi
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
  if [[ "$LOCAL_POSTGRES" == "1" ]]; then
    echo "Local Postgres / pgvector hints:"
    echo "  docker logs rag-params-finder-postgres-local 2>&1 | tail -20"
    echo "  Confirm STORAGE_BACKEND=postgres and DATABASE_URL in the server env"
    echo "  Docs: docs/user-guide/postgres-setup.md · docs/user-guide/troubleshooting.md"
  elif [[ "$LOCAL_ATLAS" == "1" ]]; then
    echo "Local Atlas hints:"
    echo "  docker logs rag-params-finder-mongodb-local 2>&1 | tail -20"
    echo "  ./start-services.sh mongodb status"
    echo "  ./start-services.sh mongodb reset   # stale keyfile / unhealthy volume"
  else
    echo "Common Atlas fixes (TLS/SSL errors affect host and Docker alike):"
    echo "  • Network Access → allow your IP (curl https://api.ipify.org) or 0.0.0.0/0 for dev"
    echo "  • Database Access → user/password in .env must match Atlas"
    echo "  • Cluster must not be paused"
    echo "Docs: docs/user-guide/troubleshooting.md (Docker section)"
  fi
}

mkdir -p input_data/pdfs configs

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
echo ""
echo "storage_mode=${STACK_STORAGE_MODE}"

case "$STACK_STORAGE_MODE" in
  mongodb-local)
    echo "STORAGE_BACKEND=mongodb"
    echo "MONGODB_URI=${RAG_LOCAL_MONGODB_URI_HOST}"
    echo "Suggested: rag-params-finder run --config $(example_config_for_stack_mode)"
    echo ""
    echo "  MongoDB:   localhost:27017  (Atlas Local — no cloud quota)"
    echo "Manage MongoDB only:   ./start-services.sh mongodb [start|stop|reset|status]"
    echo "Reset all data:        docker compose --profile mongodb-local down -v"
    ;;
  mongodb-cloud)
    echo "STORAGE_BACKEND=mongodb"
    echo "Suggested: rag-params-finder run --config $(example_config_for_stack_mode)"
    echo ""
    echo "Switch to Atlas Local:       ./start-services.sh --mongodb-local"
    echo "Switch to local Postgres:    ./start-services.sh --postgres-local"
    echo "Switch to hosted Postgres:   ./start-services.sh --postgres-cloud"
    ;;
  postgres-local)
    echo "STORAGE_BACKEND=postgres"
    echo "DATABASE_URL=${RAG_LOCAL_DATABASE_URL_HOST}"
    echo "Suggested: rag-params-finder run --config $(example_config_for_stack_mode)"
    echo ""
    echo "  Postgres:  localhost:5433  (pgvector)"
    echo "Manage Postgres only:  ./start-services.sh postgres [start|stop|reset|status]"
    print_local_postgres_cli_hints
    ;;
  postgres-cloud)
    echo "STORAGE_BACKEND=postgres"
    echo "DATABASE_URL is set from .env (password redacted)"
    echo "Suggested: rag-params-finder run --config $(example_config_for_stack_mode)"
    echo ""
    echo "Switch to local Postgres: ./start-services.sh --postgres-local"
    echo "Switch to Atlas Local:    ./start-services.sh --mongodb-local"
    ;;
esac

echo ""
echo "SIE (BGE-M3): not started — opt-in only (SIE_ENABLED=false by default)."
echo "  To enable: docs/user-guide/sie-setup.md"
echo "  CLI sweep: rag-params-finder run --config configs/mongodb/example-sie.yaml"
echo ""
echo "Aim UI:      ./scripts/aim-ui.sh  → http://localhost:43800 (experiment runs in ./.aim)"
echo ""
echo "Dev stack:   RAG_DEV_STACK=1 ./start-services.sh [--mongodb-local|--postgres-local]"
echo "Force build: ./start-services.sh --force-build [--mongodb-local|--postgres-local]"
