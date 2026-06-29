#!/bin/bash
# Start rag-params-finder server + dashboard via Docker Compose (prod stack)
# Usage: ./start-services.sh [--force-build]
#   Rebuilds images only when build context changed, images are missing, or --force-build.
#   Env: RAG_FORCE_BUILD=1 (same as --force-build), RAG_DEV_STACK=1, NONINTERACTIVE=1
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/docker-cleanup.sh
source ./scripts/docker-cleanup.sh
# shellcheck source=scripts/docker-build-context.sh
source ./scripts/docker-build-context.sh

FORCE_BUILD=0

usage() {
  cat <<EOF
Usage: ./start-services.sh [OPTIONS]

Start server + dashboard via Docker Compose.

Options:
  --force-build, --build, -b   Rebuild images even when build context is unchanged
  -h, --help                   Show this help

Environment:
  RAG_FORCE_BUILD=1            Same as --force-build
  RAG_DEV_STACK=1              Dev overlay (HMR + uvicorn --reload)
  NONINTERACTIVE=1             Fail fast on missing .env / port conflicts
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
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
  export FORCE_BUILD
}

parse_args "$@"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. See https://docs.docker.com/get-docker/" >&2
  exit 1
fi

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
  echo "Dev stack enabled (RAG_DEV_STACK=1) — HMR + uvicorn --reload"
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

  if [[ -z "${MONGODB_URI:-}" ]] || [[ "$MONGODB_URI" == *"your_mongodb_atlas_uri_here"* ]]; then
    echo "Set a real MONGODB_URI in .env (Atlas connection string)." >&2
    exit 1
  fi
}

check_ports() {
  # Ports are chosen to avoid common conflicts:
  #   8001 — backend  (uncommon; not a standard framework default)
  #   5374 — frontend (avoids 5173 which is Vite's own default, shared by every Vite project)
  #   8720 — SIE      (avoids 8080 used by Jenkins, Tomcat, Hadoop, Spark, etc.)
  local ports=(8001 5374)
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
  echo "Common Atlas fixes (TLS/SSL errors affect host and Docker alike):"
  echo "  • Network Access → allow your IP (curl https://api.ipify.org) or 0.0.0.0/0 for dev"
  echo "  • Database Access → user/password in .env must match Atlas"
  echo "  • Cluster must not be paused"
  echo "Docs: docs/user-guide/troubleshooting.md (Docker section)"
}

mkdir -p input_data/pdfs configs

ensure_env
docker_cleanup standard
check_ports

UP_ARGS=(-d)
if docker_compose_needs_build "$SCRIPT_DIR"; then
  echo "Building and starting containers..."
  UP_ARGS=(--build -d)
else
  echo "Starting containers (reusing existing images)..."
fi
if ! "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" up "${UP_ARGS[@]}"; then
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
echo "  CLI:       rag-params-finder run --config configs/example-mongodb-local.yaml"
echo ""
echo "SIE (BGE-M3): not started — opt-in only (SIE_ENABLED=false by default)."
echo "  To enable: docs/user-guide/sie-setup.md"
echo "  CLI sweep: rag-params-finder run --config configs/example-mongodb-sie.yaml"
echo ""
echo "Aim UI:      ./scripts/aim-ui.sh  → http://localhost:43800 (experiment runs in ./.aim)"
echo ""
echo "Dev stack:   RAG_DEV_STACK=1 ./start-services.sh"
echo "Force build: ./start-services.sh --force-build"
echo "             or: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
