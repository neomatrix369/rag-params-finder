#!/bin/bash
# shellcheck disable=SC2034
# Shared Docker Compose helpers and MongoDB backend constants.
# Globals (DOCKER_COMPOSE, COMPOSE_*, RAG_*) are set for scripts that source this file.
# Source from project root: source ./scripts/lib/compose.sh

# Host CLI / native server (localhost)
RAG_LOCAL_MONGODB_URI_HOST="${RAG_LOCAL_MONGODB_URI_HOST:-mongodb://localhost:27017/rag_params_finder?directConnection=true}"
# Server container on the compose network
RAG_LOCAL_MONGODB_URI_DOCKER="${RAG_LOCAL_MONGODB_URI_DOCKER:-mongodb://mongodb-local:27017/rag_params_finder?directConnection=true}"
RAG_MONGODB_LOCAL_CONTAINER="${MONGODB_LOCAL_CONTAINER_NAME:-rag-params-finder-mongodb-local}"
RAG_MONGODB_LOCAL_DB_VOLUME="${COMPOSE_PROJECT_NAME:-rag-params-finder}_mongodb_local_data"
RAG_MONGODB_LOCAL_CONFIGDB_VOLUME="${COMPOSE_PROJECT_NAME:-rag-params-finder}_mongodb_local_configdb"
RAG_MONGODB_LOCAL_MONGOT_VOLUME="${COMPOSE_PROJECT_NAME:-rag-params-finder}_mongodb_local_mongot"
RAG_MONGODB_LOCAL_VOLUMES=(
  "$RAG_MONGODB_LOCAL_DB_VOLUME"
  "$RAG_MONGODB_LOCAL_CONFIGDB_VOLUME"
  "$RAG_MONGODB_LOCAL_MONGOT_VOLUME"
)
# Back-compat alias (db volume only)
RAG_MONGODB_LOCAL_VOLUME="$RAG_MONGODB_LOCAL_DB_VOLUME"

# ── Postgres / pgvector (Supabase stand-in) ───────────────────────────────────
# Host port is 5433 so a developer's own Postgres on 5432 keeps working.
RAG_POSTGRES_USER="${POSTGRES_USER:-rag}"
RAG_POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-rag}"
RAG_POSTGRES_DB="${POSTGRES_DB:-rag_params_finder}"
RAG_LOCAL_DATABASE_URL_HOST="${RAG_LOCAL_DATABASE_URL_HOST:-postgresql://${RAG_POSTGRES_USER}:${RAG_POSTGRES_PASSWORD}@localhost:5433/${RAG_POSTGRES_DB}}"
RAG_LOCAL_DATABASE_URL_DOCKER="${RAG_LOCAL_DATABASE_URL_DOCKER:-postgresql://${RAG_POSTGRES_USER}:${RAG_POSTGRES_PASSWORD}@postgres-local:5432/${RAG_POSTGRES_DB}}"
RAG_POSTGRES_LOCAL_CONTAINER="${POSTGRES_LOCAL_CONTAINER_NAME:-rag-params-finder-postgres-local}"
RAG_POSTGRES_LOCAL_VOLUME="${COMPOSE_PROJECT_NAME:-rag-params-finder}_postgres_local_data"

compose_require_docker_daemon() {
  if ! docker info >/dev/null 2>&1; then
    echo "Cannot connect to the Docker daemon. Is Docker Desktop running?" >&2
    echo "  macOS: open Docker Desktop and wait until it shows 'Running'." >&2
    return 1
  fi
}

compose_detect() {
  if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE=(docker-compose)
  else
    echo "Docker Compose is not available." >&2
    return 1
  fi
}

compose_files() {
  COMPOSE_FILES=(-f docker-compose.yml)
  if [[ "${RAG_DEV_STACK:-}" == "1" ]]; then
    COMPOSE_FILES+=(-f docker-compose.dev.yml)
  fi
}

compose_local_atlas_active() {
  [[ "${RAG_LOCAL_ATLAS:-}" == "1" || "${LOCAL_ATLAS:-}" == "1" ]]
}

compose_local_atlas_profiles() {
  COMPOSE_PROFILES=(--profile local-atlas)
}

compose_local_postgres_active() {
  [[ "${RAG_LOCAL_POSTGRES:-}" == "1" || "${LOCAL_POSTGRES:-}" == "1" ]]
}

compose_local_postgres_profiles() {
  COMPOSE_PROFILES=(--profile local-postgres)
}

compose_export_local_postgres_env() {
  export RAG_SERVER_DATABASE_URL="$RAG_LOCAL_DATABASE_URL_DOCKER"
  export STORAGE_BACKEND=postgres
}

compose_clear_local_postgres_env() {
  unset RAG_SERVER_DATABASE_URL STORAGE_BACKEND
}

print_local_postgres_cli_hints() {
  echo ""
  echo "Local Postgres + pgvector is ready."
  echo ""
  echo "  Connection string (CLI / host server):"
  echo "    export STORAGE_BACKEND=postgres"
  echo "    export DATABASE_URL=\"$RAG_LOCAL_DATABASE_URL_HOST\""
  echo ""
  echo "  Reset data:"
  echo "    docker rm -f $RAG_POSTGRES_LOCAL_CONTAINER && docker volume rm $RAG_POSTGRES_LOCAL_VOLUME"
}

compose_export_local_atlas_env() {
  export RAG_SERVER_MONGODB_URI="$RAG_LOCAL_MONGODB_URI_DOCKER"
  export RAG_MONGODB_STORAGE_LIMIT_MB=0
}

compose_clear_local_atlas_env() {
  unset RAG_SERVER_MONGODB_URI RAG_MONGODB_STORAGE_LIMIT_MB
}

print_local_atlas_cli_hints() {
  local include_full_stack="${1:-0}"
  echo ""
  echo "MongoDB Atlas Local is ready."
  echo ""
  echo "  Connection string (CLI / host server):"
  echo "    export MONGODB_URI=\"$RAG_LOCAL_MONGODB_URI_HOST\""
  echo ""
  echo "  Quick sweep:"
  echo "    MONGODB_URI=\"$RAG_LOCAL_MONGODB_URI_HOST\" rag-params-finder run --config configs/mongodb/example-local.yaml"
  if [[ "$include_full_stack" == "1" ]]; then
    echo ""
    echo "  Full stack with local Atlas:"
    echo "    ./start-services.sh --local"
  fi
  echo ""
  echo "  Reset data:"
  echo "    ./start-services.sh mongodb reset"
}

print_mongodb_local_reset_hint() {
  echo "If logs mention 'keyfile' or 'Unable to acquire security key', reset stale volumes:" >&2
  echo "  ./start-services.sh mongodb reset && ./start-services.sh --local" >&2
}

wait_for_mongodb_local_healthy() {
  local tries=0
  local health=""
  while true; do
    health="$(docker inspect --format='{{.State.Health.Status}}' "$RAG_MONGODB_LOCAL_CONTAINER" 2>/dev/null || echo "")"
    if [[ "$health" == "healthy" ]]; then
      echo ""
      return 0
    fi
    if [[ "$health" == "unhealthy" ]]; then
      echo ""
      echo "MongoDB Atlas Local is unhealthy." >&2
      echo "  docker logs $RAG_MONGODB_LOCAL_CONTAINER 2>&1 | tail -20" >&2
      print_mongodb_local_reset_hint
      return 1
    fi
    tries=$((tries + 1))
    if [[ $tries -ge 90 ]]; then
      echo ""
      echo "Timed out waiting for $RAG_MONGODB_LOCAL_CONTAINER to become healthy." >&2
      echo "  docker logs $RAG_MONGODB_LOCAL_CONTAINER 2>&1 | tail -20" >&2
      print_mongodb_local_reset_hint
      return 1
    fi
    printf "."
    sleep 2
  done
}
