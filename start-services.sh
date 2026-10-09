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

# shellcheck source=scripts/docker/docker-cleanup.sh
source ./scripts/docker/docker-cleanup.sh
# shellcheck source=scripts/docker/docker-build-context.sh
source ./scripts/docker/docker-build-context.sh
# shellcheck source=scripts/lib/compose.sh
source ./scripts/lib/compose.sh
# shellcheck source=scripts/lib/storage_mode.sh
source ./scripts/lib/storage_mode.sh
# shellcheck source=scripts/lib/store_manifest.sh
source ./scripts/lib/store_manifest.sh

FORCE_BUILD=0
LOCAL_ATLAS=0
LOCAL_POSTGRES=0
STACK_DB_TYPE=""
STACK_LOCATION=""
STACK_STORAGE_MODE=""

usage() {
  cat <<EOF
Usage: ./start-services.sh [OPTIONS]
       ./start-services.sh mongodb|postgres|elasticsearch|redis start|stop|reset|status

Start server + dashboard via Docker Compose (default), or manage a local DB container.

Stack options (pick one):
  --mongodb-local              Atlas Local container (no cloud account)
  --mongodb-cloud              Atlas cloud — requires MONGODB_ATLAS_CLOUD_URI
  --postgres-local             Local pgvector — STORAGE_BACKEND=postgres
  --postgres-cloud             Hosted Supabase — requires POSTGRES_CLOUD_URL; no MONGODB_ATLAS_CLOUD_URI
  --elasticsearch-local        Local Elasticsearch 9.5 + run-state store (default mongodb-local)
  --elasticsearch-cloud        Bring-your-own Elasticsearch — requires ELASTICSEARCH_CLOUD_URL
  --redis-local                Local Redis 8 + Query Engine — vector-only, run state on Postgres/MongoDB
  --redis-cloud                Bring-your-own Redis/Valkey — requires REDIS_URL
  --force-build, --build, -b   Rebuild images even when build context is unchanged
  -h, --help                   Show this help

Container-only:
  mongodb start|stop|reset|status          Atlas Local container
  postgres start|stop|reset|status         Local pgvector container
  elasticsearch start|stop|reset|status    Local Elasticsearch container
  redis start|stop|reset|status            Local Redis 8 container

Environment:
  RAG_MONGODB_LOCAL=1          Same as --mongodb-local
  RAG_MONGODB_CLOUD=1          Same as --mongodb-cloud
  RAG_POSTGRES_LOCAL=1         Same as --postgres-local
  RAG_POSTGRES_CLOUD=1         Same as --postgres-cloud
  RAG_ELASTICSEARCH_LOCAL=1    Same as --elasticsearch-local
  RAG_ELASTICSEARCH_CLOUD=1    Same as --elasticsearch-cloud
  RAG_REDIS_LOCAL=1            Same as --redis-local
  RAG_REDIS_CLOUD=1            Same as --redis-cloud
  RAG_LOCAL_ATLAS=1            Deprecated → --mongodb-local
  RAG_LOCAL_POSTGRES=1         Deprecated → --postgres-local
  RAG_FORCE_BUILD=1            Same as --force-build
  RAG_DEV_STACK=1              Dev overlay (HMR + uvicorn --reload)
  NONINTERACTIVE=1             Fail fast on missing .env / port conflicts

Modes (storage_mode = engine × location):
  mongodb-cloud (default bare start): requires MONGODB_ATLAS_CLOUD_URI in .env
  mongodb-local:  Atlas Local container; CLI export MONGODB_ATLAS_LOCAL_URI=$RAG_LOCAL_MONGODB_URI_HOST
  postgres-local: pgvector container; CLI export STORAGE_BACKEND=postgres POSTGRES_LOCAL_URL=$RAG_LOCAL_DATABASE_URL_HOST
  postgres-cloud: hosted Supabase; requires POSTGRES_CLOUD_URL; must not require MONGODB_ATLAS_CLOUD_URI
  elasticsearch-local: Elasticsearch on 127.0.0.1:9200 plus the paired run-state store
  elasticsearch-cloud: ELASTICSEARCH_CLOUD_URL from .env; run state from STORAGE_BACKEND
  redis-local: Redis 8 on 127.0.0.1:6379 (vector-only); VECTOR_STORE_BACKEND=redis
  redis-cloud: REDIS_URL from .env (rediss://...); VECTOR_STORE_BACKEND=redis
EOF
}

_print_ready_mongodb() {
  print_local_atlas_cli_hints "${1:-1}"
}

_print_ready_postgres() {
  print_local_postgres_cli_hints "${1:-1}"
}

_print_ready_elasticsearch() {
  local example
  example="$(store_field elasticsearch example_config)"
  echo ""
  echo "Elasticsearch: ${RAG_LOCAL_ELASTICSEARCH_URL_HOST}"
  echo "  rag-params-finder run --config ${example}"
}

_elasticsearch_health_failed() {
  echo "  On Linux, vm.max_map_count must be at least 262144." >&2
}

print_store_ready_hint() {
  local provider="$1"
  local example
  example="$(store_field "$provider" example_config)"
  echo ""
  echo "${provider} is ready."
  echo "  rag-params-finder run --config ${example}"
}

_print_store_ready() {
  local provider="$1"
  local hint="_print_ready_${provider}"
  if declare -F "$hint" >/dev/null; then
    "$hint" 1
    return 0
  fi
  print_store_ready_hint "$provider"
}

_remove_store_volumes() {
  local provider="$1"
  local volumes var_name vol
  volumes="$(store_field "$provider" volumes)"
  # Volume column is a space-separated list of env var names from stores.tsv.
  # shellcheck disable=SC2086
  for var_name in $volumes; do
    vol="${!var_name:-}"
    if [[ -n "$vol" ]]; then
      docker volume rm "$vol" 2>/dev/null || true
    fi
  done
}

cmd_store_start() {
  local provider="$1"
  local service container hook
  service="$(store_field "$provider" profile)"
  container="$(store_container_name "$provider")"
  echo "Starting ${provider}..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" up -d "$service"
  echo ""
  echo "Waiting for ${provider} to be ready..."
  local wait_fn="wait_for_${provider}_local_healthy"
  if declare -F "$wait_fn" >/dev/null; then
    "$wait_fn"
  else
    hook="_${provider}_health_failed"
    if ! declare -F "$hook" >/dev/null; then
      hook=""
    fi
    wait_for_named_container_healthy "$container" "$provider" "$hook"
  fi
  _print_store_ready "$provider"
}

cmd_store_stop() {
  local provider="$1"
  local service
  service="$(store_field "$provider" profile)"
  echo "Stopping ${provider}..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" stop "$service"
  echo "Stopped."
}

cmd_store_reset() {
  local provider="$1"
  local service
  service="$(store_field "$provider" profile)"
  echo "Stopping and wiping ${provider} data volumes..."
  "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${COMPOSE_PROFILES[@]}" rm -sf "$service"
  _remove_store_volumes "$provider"
  echo "Volumes wiped. Run './start-services.sh ${provider} start' to recreate."
}

cmd_store_status() {
  local provider="$1"
  local container state health
  container="$(store_container_name "$provider")"
  state="$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not found")"
  health="$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "—")"
  echo "Container: $container"
  echo "  State:  $state"
  echo "  Health: $health"
  if [[ "$state" == "running" && "$health" == "healthy" ]]; then
    _print_store_ready "$provider"
  fi
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
  if [[ "${RAG_MONGODB_LOCAL:-}${RAG_MONGODB_CLOUD:-}${RAG_POSTGRES_LOCAL:-}${RAG_POSTGRES_CLOUD:-}${RAG_ELASTICSEARCH_LOCAL:-}${RAG_ELASTICSEARCH_CLOUD:-}${RAG_REDIS_LOCAL:-}${RAG_REDIS_CLOUD:-}${RAG_LOCAL_ATLAS:-}${RAG_LOCAL_POSTGRES:-}" == *"1"* ]] \
    || [[ " $* " == *" --mongodb-"* ]] \
    || [[ " $* " == *" --postgres-"* ]] \
    || [[ " $* " == *" --elasticsearch-"* ]] \
    || [[ " $* " == *" --redis-"* ]]; then
    STACK_MODE_FROM_CLI=1
  fi
  local arg
  for arg in "$@"; do
    case "$arg" in
      --mongodb-local | --mongodb-cloud | --postgres-local | --postgres-cloud | --elasticsearch-local | --elasticsearch-cloud | --redis-local | --redis-cloud)
        STACK_MODE_FROM_CLI=1
        ;;
    esac
  done
  export FORCE_BUILD LOCAL_ATLAS LOCAL_POSTGRES STACK_DB_TYPE STACK_LOCATION STACK_STORAGE_MODE STACK_MODE_FROM_CLI
}

run_named_store_command() {
  local provider="$1"
  local cmd="${2:-start}"
  local fn="cmd_store_${cmd}"
  if ! declare -F "$fn" >/dev/null; then
    echo "Unknown ${provider} command: $cmd" >&2
    echo "Usage: ./start-services.sh ${provider} [start|stop|reset|status]" >&2
    exit 1
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. See https://docs.docker.com/get-docker/" >&2
    exit 1
  fi
  compose_require_docker_daemon || exit 1
  compose_detect
  compose_files
  local profile
  profile="$(store_field "$provider" profile)"
  COMPOSE_PROFILES=(--profile "$profile")
  "$fn" "$provider"
}

if store_is_provider "${1:-}"; then
  provider="$1"
  shift
  run_named_store_command "$provider" "${1:-start}"
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

  set -a
  # shellcheck disable=SC1091  # .env is gitignored; absent in CI sandboxes
  source .env
  set +a

  # SUPABASE_URI → DATABASE_URL before mode resolve / ensure_env.
  apply_postgres_uri_aliases

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
  compose_clear_local_elasticsearch_env
  compose_clear_local_redis_env
  export_storage_backend_for_stack

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
    echo "Hosted Postgres enabled — STORAGE_BACKEND=postgres; requires POSTGRES_CLOUD_URL"
  elif [[ "$STACK_DB_TYPE" == "mongodb" ]]; then
    # Symmetric with postgres: override leftover STORAGE_BACKEND=postgres on rollback.
    export STORAGE_BACKEND=mongodb
    echo "MongoDB enabled — STORAGE_BACKEND=mongodb"
  fi

  if [[ "$LOCAL_ELASTICSEARCH" == "1" ]]; then
    compose_export_local_elasticsearch_env
    compose_local_elasticsearch_profiles
    PROFILES+=("${COMPOSE_PROFILES[@]}")
    echo "Local Elasticsearch enabled — 127.0.0.1:9200, VECTOR_STORE_BACKEND=elasticsearch"
  elif [[ "$STACK_DB_TYPE" == "elasticsearch" ]]; then
    export VECTOR_STORE_BACKEND=elasticsearch
    export SERVER_BUILD_TARGET=server-elasticsearch
    echo "Elasticsearch cloud enabled — VECTOR_STORE_BACKEND=elasticsearch; requires ELASTICSEARCH_CLOUD_URL"
  fi

  if [[ "${LOCAL_REDIS:-0}" == "1" ]]; then
    compose_export_local_redis_env
    compose_local_redis_profiles
    PROFILES+=("${COMPOSE_PROFILES[@]}")
    echo "Local Redis enabled — 127.0.0.1:6379, VECTOR_STORE_BACKEND=redis"
  elif [[ "$STACK_DB_TYPE" == "redis" ]]; then
    export VECTOR_STORE_BACKEND=redis
    export SERVER_BUILD_TARGET=server-redis
    echo "Redis cloud enabled — VECTOR_STORE_BACKEND=redis; requires REDIS_URL"
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

# Scan upward from $1 until a free port is found.
# If $2 (container name) is provided and is currently running on that port, reuse it.
# Ports 8001/5374 are chosen to avoid common conflicts:
#   8001 — backend  (uncommon; not a standard framework default)
#   5374 — frontend (avoids 5173 which is Vite's own default, shared by every Vite project)
#   8720 — SIE      (avoids 8080 used by Jenkins, Tomcat, Hadoop, Spark, etc.)
#   27017 — MongoDB (local Atlas only)
#   5433  — Postgres (local pgvector only; 5432 left free for a developer's own Postgres)
_resolve_one_port() {
  local desired=$1
  local own_container="${2:-}"
  local port=$desired
  local max=20
  local i=0
  while lsof -ti:"$port" >/dev/null 2>&1; do
    # Our own container already holds this port — safe to reuse without incrementing
    if [[ -n "$own_container" ]] && \
       docker inspect --format='{{.State.Status}}' "$own_container" 2>/dev/null | grep -q running; then
      break
    fi
    ((port++)) || true
    ((i++)) || true
    if [[ $i -ge $max ]]; then
      echo "ERROR: no free port found starting from $desired (tried $max consecutive ports)" >&2
      exit 1
    fi
  done
  echo "$port"
}

resolve_ports() {
  SERVER_PORT=$(_resolve_one_port 8001 "${SERVER_CONTAINER_NAME:-rag-params-finder-server}")
  FRONTEND_PORT=$(_resolve_one_port 5374 "${FRONTEND_CONTAINER_NAME:-rag-params-finder-frontend}")

  if [[ "$LOCAL_ATLAS" == "1" ]]; then
    MONGODB_PORT=$(_resolve_one_port 27017 "$RAG_MONGODB_LOCAL_CONTAINER")
  else
    MONGODB_PORT=27017
  fi
  if [[ "$LOCAL_POSTGRES" == "1" ]]; then
    POSTGRES_PORT=$(_resolve_one_port 5433 "$RAG_POSTGRES_LOCAL_CONTAINER")
  else
    POSTGRES_PORT=5433
  fi
  if [[ "$LOCAL_ELASTICSEARCH" == "1" ]]; then
    ELASTICSEARCH_PORT=$(_resolve_one_port 9200 "$RAG_ELASTICSEARCH_LOCAL_CONTAINER")
  else
    ELASTICSEARCH_PORT=9200
  fi
  if [[ "${LOCAL_REDIS:-0}" == "1" ]]; then
    REDIS_PORT=$(_resolve_one_port 6379 "${RAG_REDIS_LOCAL_CONTAINER:-rag-params-finder-redis-local}")
  else
    REDIS_PORT=6379
  fi

  export SERVER_PORT FRONTEND_PORT MONGODB_PORT POSTGRES_PORT ELASTICSEARCH_PORT REDIS_PORT

  # Announce any bumps so the operator knows what changed
  [[ "$SERVER_PORT"        != "8001"  ]] && echo "Port 8001 in use — server will bind on $SERVER_PORT"
  [[ "$FRONTEND_PORT"      != "5374"  ]] && echo "Port 5374 in use — frontend will bind on $FRONTEND_PORT"
  [[ "$LOCAL_ATLAS"  == "1" && "$MONGODB_PORT"       != "27017" ]] && echo "Port 27017 in use — MongoDB will bind on $MONGODB_PORT"
  [[ "$LOCAL_POSTGRES" == "1" && "$POSTGRES_PORT"    != "5433"  ]] && echo "Port 5433 in use — Postgres will bind on $POSTGRES_PORT"
  [[ "$LOCAL_ELASTICSEARCH" == "1" && "$ELASTICSEARCH_PORT" != "9200" ]] && echo "Port 9200 in use — Elasticsearch will bind on $ELASTICSEARCH_PORT"
  [[ "${LOCAL_REDIS:-0}" == "1" && "$REDIS_PORT" != "6379" ]] && echo "Port 6379 in use — Redis will bind on $REDIS_PORT"
  return 0  # bash 3.2: [[ false ]] && echo exits 1; guard callers from set -e
}

print_unhealthy_server_hint() {
  echo ""
  echo "Server did not become healthy (frontend waits on server healthcheck)."
  echo "Diagnose:"
  echo "  curl -s http://localhost:${SERVER_PORT:-8001}/healthz"
  echo "  docker logs rag-params-finder-server 2>&1 | tail -30"
  echo ""
  if [[ "$LOCAL_POSTGRES" == "1" ]]; then
    echo "Local Postgres / pgvector hints:"
    echo "  docker logs rag-params-finder-postgres-local 2>&1 | tail -20"
    echo "  Confirm STORAGE_BACKEND=postgres and POSTGRES_CLOUD_URL or POSTGRES_LOCAL_URL in the server env"
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
  GIT_COMMIT="$(git rev-parse --short HEAD)"
  GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  export GIT_COMMIT GIT_BRANCH
fi
docker_cleanup standard
resolve_ports

# Update host-side connection strings to reflect any remapped ports
if [[ "${MONGODB_PORT}" != "27017" ]]; then
  RAG_LOCAL_MONGODB_URI_HOST="mongodb://localhost:${MONGODB_PORT}/rag_params_finder?directConnection=true"
fi
if [[ "${POSTGRES_PORT}" != "5433" ]]; then
  RAG_LOCAL_DATABASE_URL_HOST="postgresql://${RAG_POSTGRES_USER}:${RAG_POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${RAG_POSTGRES_DB}"
fi
if [[ "${ELASTICSEARCH_PORT}" != "9200" ]]; then
  RAG_LOCAL_ELASTICSEARCH_URL_HOST="http://127.0.0.1:${ELASTICSEARCH_PORT}"
fi
if [[ "${REDIS_PORT}" != "6379" ]]; then
  RAG_LOCAL_REDIS_URL_HOST="redis://127.0.0.1:${REDIS_PORT}"
fi

UP_ARGS=(-d)
if docker_compose_needs_build "$SCRIPT_DIR"; then
  echo "Building and starting containers..."
  UP_ARGS=(--build -d)
else
  echo "Starting containers (reusing existing images)..."
fi
if [[ -n "${SERVER_BUILD_TARGET:-}" ]]; then
  echo "Rebuilding the server image for target=${SERVER_BUILD_TARGET}"
  UP_ARGS=(--build -d)
fi
# VITE_API_URL is baked into the frontend image at build time — force rebuild when server port shifts
if [[ "${SERVER_PORT}" != "8001" ]]; then
  echo "Server port shifted to ${SERVER_PORT} — rebuilding frontend image to update VITE_API_URL"
  UP_ARGS=(--build -d)
fi

if ! "${DOCKER_COMPOSE[@]}" "${COMPOSE_FILES[@]}" "${PROFILES[@]}" up "${UP_ARGS[@]}"; then
  print_unhealthy_server_hint
  exit 1
fi

echo "Waiting for services to become healthy..."
sleep 15

if [[ -x ./scripts/docker/health-check.sh ]]; then
  if ! SERVER_URL="http://localhost:${SERVER_PORT}" FRONTEND_URL="http://localhost:${FRONTEND_PORT}" \
       ./scripts/docker/health-check.sh; then
    print_unhealthy_server_hint
    exit 1
  fi
else
  if ! curl -sf "http://localhost:${SERVER_PORT}/healthz" >/dev/null; then
    print_unhealthy_server_hint
    exit 1
  fi
  curl -sf "http://localhost:${FRONTEND_PORT}/" >/dev/null
fi

echo ""
echo "Services ready:"
echo "  Server:    http://localhost:${SERVER_PORT}  (docs: /docs)"
echo "  Dashboard: http://localhost:${FRONTEND_PORT}"
echo ""
echo "storage_mode=${STACK_STORAGE_MODE}"
echo "STORAGE_BACKEND=${STORAGE_BACKEND:-}"
echo "VECTOR_STORE_BACKEND=${VECTOR_STORE_BACKEND:-}"
echo "Suggested: rag-params-finder run --config $(example_config_for_stack_mode)"
if [[ "$LOCAL_ELASTICSEARCH" == "1" ]]; then
  echo "Elasticsearch: ${RAG_LOCAL_ELASTICSEARCH_URL_HOST}"
  echo "Manage Elasticsearch only: ./start-services.sh elasticsearch [start|stop|reset|status]"
fi

echo ""
echo "SIE (BGE-M3): not started — opt-in only (SIE_ENABLED=false by default)."
echo "  To enable: docs/user-guide/sie-setup.md"
if [[ "${STACK_DB_TYPE:-}" == "postgres" ]]; then
  echo "  CLI sweep: rag-params-finder run --config configs/supabase/example-sie.yaml"
else
  echo "  CLI sweep: rag-params-finder run --config configs/mongodb/example-sie.yaml"
fi
echo ""
echo "Aim UI:      ./scripts/docker/aim-ui.sh  → http://localhost:43800 (experiment runs in ./.aim)"
echo ""
echo "Dev stack:   RAG_DEV_STACK=1 ./start-services.sh [--mongodb-local|--postgres-local]"
echo "Force build: ./start-services.sh --force-build [--mongodb-local|--postgres-local]"
