#!/bin/bash
# Start rag-params-finder server + dashboard via Docker Compose (prod stack)
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# shellcheck source=scripts/docker-cleanup.sh
source ./scripts/docker-cleanup.sh

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

mkdir -p input_data/pdfs configs

ensure_env
docker_cleanup standard
check_ports

echo "Building and starting containers..."
"${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" up --build -d

echo "Waiting for services to become healthy..."
sleep 15

if [[ -x ./scripts/health-check.sh ]]; then
  ./scripts/health-check.sh
else
  curl -sf http://localhost:8001/healthz >/dev/null
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
echo ""
echo "Dev stack:   RAG_DEV_STACK=1 ./start-services.sh"
echo "             or: docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d"
