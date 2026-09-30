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
# Back-compat alias (db volume only). Reset walks the volume names in stores.tsv.
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

# ── Elasticsearch (vector-only; run state is a separate store) ────────────────
RAG_LOCAL_ELASTICSEARCH_URL_HOST="${RAG_LOCAL_ELASTICSEARCH_URL_HOST:-http://127.0.0.1:9200}"
RAG_LOCAL_ELASTICSEARCH_URL_DOCKER="${RAG_LOCAL_ELASTICSEARCH_URL_DOCKER:-http://elasticsearch-local:9200}"
RAG_ELASTICSEARCH_LOCAL_CONTAINER="${ELASTICSEARCH_LOCAL_CONTAINER_NAME:-rag-params-finder-elasticsearch-local}"
RAG_ELASTICSEARCH_LOCAL_VOLUME="${COMPOSE_PROJECT_NAME:-rag-params-finder}_elasticsearch_local_data"

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
  # Canonical profile matches storage_mode=mongodb-local (local-atlas remains an alias).
  COMPOSE_PROFILES=(--profile mongodb-local)
}

compose_local_postgres_active() {
  [[ "${RAG_LOCAL_POSTGRES:-}" == "1" || "${LOCAL_POSTGRES:-}" == "1" ]]
}

compose_local_postgres_profiles() {
  # Canonical profile matches storage_mode=postgres-local (local-postgres remains an alias).
  COMPOSE_PROFILES=(--profile postgres-local)
}

compose_local_elasticsearch_profiles() {
  COMPOSE_PROFILES=(--profile elasticsearch-local)
}

compose_export_local_elasticsearch_env() {
  export RAG_SERVER_ELASTICSEARCH_LOCAL_URL="$RAG_LOCAL_ELASTICSEARCH_URL_DOCKER"
  export VECTOR_STORE_BACKEND=elasticsearch
  export SERVER_EXTRAS=elasticsearch
}

compose_clear_local_elasticsearch_env() {
  unset RAG_SERVER_ELASTICSEARCH_LOCAL_URL SERVER_EXTRAS
}

compose_export_local_postgres_env() {
  export RAG_SERVER_POSTGRES_LOCAL_URL="$RAG_LOCAL_DATABASE_URL_DOCKER"
  export STORAGE_BACKEND=postgres
}

compose_clear_local_postgres_env() {
  unset RAG_SERVER_POSTGRES_LOCAL_URL STORAGE_BACKEND
}

print_local_postgres_cli_hints() {
  local include_full_stack="${1:-0}"
  echo ""
  echo "Local Postgres + pgvector is ready."
  echo ""
  echo "  Connection string (CLI / host server):"
  echo "    export STORAGE_BACKEND=postgres"
  echo "    export POSTGRES_LOCAL_URL=\"$RAG_LOCAL_DATABASE_URL_HOST\""
  echo ""
  echo "  Quick sweep:"
  echo "    STORAGE_BACKEND=postgres POSTGRES_LOCAL_URL=\"$RAG_LOCAL_DATABASE_URL_HOST\" \\"
  echo "      rag-params-finder run --config configs/supabase/example-local.yaml"
  if [[ "$include_full_stack" == "1" ]]; then
    echo ""
    echo "  Full stack with local Postgres:"
    echo "    ./start-services.sh --postgres-local"
  fi
  echo ""
  echo "  Reset data:"
  echo "    ./start-services.sh postgres reset"
}

compose_export_local_atlas_env() {
  export RAG_SERVER_MONGODB_ATLAS_LOCAL_URI="$RAG_LOCAL_MONGODB_URI_DOCKER"
  export RAG_MONGODB_STORAGE_LIMIT_MB=0
  export STORAGE_BACKEND=mongodb
}

compose_clear_local_atlas_env() {
  unset RAG_SERVER_MONGODB_ATLAS_LOCAL_URI RAG_MONGODB_STORAGE_LIMIT_MB
}

print_local_atlas_cli_hints() {
  local include_full_stack="${1:-0}"
  echo ""
  echo "MongoDB Atlas Local is ready."
  echo ""
  echo "  Connection string (CLI / host server):"
  echo "    export MONGODB_ATLAS_LOCAL_URI=\"$RAG_LOCAL_MONGODB_URI_HOST\""
  echo ""
  echo "  Quick sweep:"
  echo "    MONGODB_ATLAS_LOCAL_URI=\"$RAG_LOCAL_MONGODB_URI_HOST\" rag-params-finder run --config configs/mongodb/example-local.yaml"
  if [[ "$include_full_stack" == "1" ]]; then
    echo ""
    echo "  Full stack with Atlas Local:"
    echo "    ./start-services.sh --mongodb-local"
  fi
  echo ""
  echo "  Reset data:"
  echo "    ./start-services.sh mongodb reset"
}

print_mongodb_local_reset_hint() {
  echo "If logs mention 'keyfile' or 'Unable to acquire security key', reset stale volumes:" >&2
  echo "  ./start-services.sh mongodb reset && ./start-services.sh --mongodb-local" >&2
  echo "If logs mention NodeNotFound, RSGhost, or a set name that differs from the hostname," >&2
  echo "  the volume was initialized under another container hostname. Set MONGODB_LOCAL_HOSTNAME" >&2
  echo "  to that replica set name and recreate the container. Do not reset the volume." >&2
}

print_postgres_local_reset_hint() {
  echo "If the volume is corrupt or the container stays unhealthy, reset and recreate:" >&2
  echo "  ./start-services.sh postgres reset && ./start-services.sh --postgres-local" >&2
}

# Shared docker-health wait. on_fail is an optional function name; it receives the container.
wait_for_named_container_healthy() {
  local container="$1"
  local label="$2"
  local on_fail="${3:-}"
  local tries=0
  local health=""
  while true; do
    health="$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "")"
    if [[ "$health" == "healthy" ]]; then
      echo ""
      return 0
    fi
    tries=$((tries + 1))
    if [[ "$health" == "unhealthy" || $tries -ge 90 ]]; then
      echo ""
      if [[ "$health" == "unhealthy" ]]; then
        echo "${label} is unhealthy." >&2
      else
        echo "Timed out waiting for ${container} to become healthy." >&2
      fi
      echo "  docker logs ${container} 2>&1 | tail -20" >&2
      if [[ -n "$on_fail" ]] && declare -F "$on_fail" >/dev/null; then
        "$on_fail" "$container"
      fi
      return 1
    fi
    printf "."
    sleep 2
  done
}

_mongodb_health_failed() {
  local container="$1"
  if docker logs "$container" 2>&1 | grep -q "Wrong mongod version\|featureCompatibilityVersion"; then
    echo "Detected featureCompatibilityVersion / image mismatch (e.g. volumes from a newer" >&2
    echo "Atlas Local image than the compose pin). Reset volumes, then restart:" >&2
  fi
  print_mongodb_local_reset_hint
}

_postgres_health_failed() {
  print_postgres_local_reset_hint
}

wait_for_mongodb_local_healthy() {
  wait_for_named_container_healthy "$RAG_MONGODB_LOCAL_CONTAINER" "MongoDB Atlas Local" _mongodb_health_failed
}

wait_for_postgres_local_healthy() {
  wait_for_named_container_healthy "$RAG_POSTGRES_LOCAL_CONTAINER" "Local Postgres + pgvector" _postgres_health_failed
}
