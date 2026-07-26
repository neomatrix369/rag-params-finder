#!/bin/bash
# Resolve rag-params-finder stack mode: engine × location → storage_mode compound.
# Source from project root: source ./scripts/lib/storage_mode.sh
#
# Canonical modes: mongodb-local | mongodb-cloud | postgres-local | postgres-cloud
# Exports (when resolve_stack_mode succeeds):
#   STACK_DB_TYPE, STACK_LOCATION, STACK_STORAGE_MODE
#   LOCAL_ATLAS, LOCAL_POSTGRES  (compat for existing compose helpers)

# shellcheck disable=SC2034

_stack_mode_error() {
  echo "$*" >&2
}

_stack_mode_conflict() {
  local left="$1"
  local right="$2"
  _stack_mode_error "ERROR: conflicting mode selectors: ${left} and ${right}"
  _stack_mode_error "Pick one of: --mongodb-local | --mongodb-cloud | --postgres-local | --postgres-cloud"
  return 1
}

# Map a single selector token to STACK_DB_TYPE + STACK_LOCATION.
# Tokens: mongodb-local|mongodb-cloud|postgres-local|postgres-cloud
#         or legacy: local|postgres|mongodb-local aliases already expanded by caller
_stack_mode_apply_token() {
  local token="$1"
  case "$token" in
    mongodb-local)
      STACK_DB_TYPE=mongodb
      STACK_LOCATION=local
      ;;
    mongodb-cloud)
      STACK_DB_TYPE=mongodb
      STACK_LOCATION=cloud
      ;;
    postgres-local)
      STACK_DB_TYPE=postgres
      STACK_LOCATION=local
      ;;
    postgres-cloud)
      STACK_DB_TYPE=postgres
      STACK_LOCATION=cloud
      ;;
    *)
      _stack_mode_error "ERROR: unknown mode token: ${token}"
      return 1
      ;;
  esac
  STACK_STORAGE_MODE="${STACK_DB_TYPE}-${STACK_LOCATION}"
}

# resolve_stack_mode [--flags...]
# Also reads RAG_MONGODB_LOCAL / RAG_MONGODB_CLOUD / RAG_POSTGRES_LOCAL / RAG_POSTGRES_CLOUD
# and legacy RAG_LOCAL_ATLAS / RAG_LOCAL_POSTGRES.
# Prints nothing on success; sets STACK_* and LOCAL_* globals.
resolve_stack_mode() {
  STACK_DB_TYPE=""
  STACK_LOCATION=""
  STACK_STORAGE_MODE=""
  LOCAL_ATLAS=0
  LOCAL_POSTGRES=0

  local selected=()
  local deprecations=()
  local force_build=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mongodb-local)
        selected+=("mongodb-local")
        shift
        ;;
      --mongodb-cloud)
        selected+=("mongodb-cloud")
        shift
        ;;
      --postgres-local)
        selected+=("postgres-local")
        shift
        ;;
      --postgres-cloud)
        selected+=("postgres-cloud")
        shift
        ;;
      --local | -l)
        selected+=("mongodb-local")
        deprecations+=("--local → --mongodb-local")
        shift
        ;;
      --postgres | -p)
        selected+=("postgres-local")
        deprecations+=("--postgres → --postgres-local")
        shift
        ;;
      --force-build | --build | -b)
        force_build=1
        shift
        ;;
      -h | --help)
        # Caller handles help; ignore here
        shift
        ;;
      *)
        _stack_mode_error "Unknown option: $1 (try --help)"
        return 2
        ;;
    esac
  done

  # Env selectors (canonical first, then legacy)
  if [[ "${RAG_MONGODB_LOCAL:-}" == "1" ]]; then
    selected+=("mongodb-local")
  fi
  if [[ "${RAG_MONGODB_CLOUD:-}" == "1" ]]; then
    selected+=("mongodb-cloud")
  fi
  if [[ "${RAG_POSTGRES_LOCAL:-}" == "1" ]]; then
    selected+=("postgres-local")
  fi
  if [[ "${RAG_POSTGRES_CLOUD:-}" == "1" ]]; then
    selected+=("postgres-cloud")
  fi
  if [[ "${RAG_LOCAL_ATLAS:-}" == "1" ]]; then
    selected+=("mongodb-local")
    deprecations+=("RAG_LOCAL_ATLAS=1 → RAG_MONGODB_LOCAL=1 / --mongodb-local")
  fi
  if [[ "${RAG_LOCAL_POSTGRES:-}" == "1" ]]; then
    selected+=("postgres-local")
    deprecations+=("RAG_LOCAL_POSTGRES=1 → RAG_POSTGRES_LOCAL=1 / --postgres-local")
  fi

  # Deduplicate while preserving order
  local unique=()
  local token
  for token in "${selected[@]}"; do
    local seen=0
    local u
    for u in "${unique[@]+"${unique[@]}"}"; do
      if [[ "$u" == "$token" ]]; then
        seen=1
        break
      fi
    done
    if [[ "$seen" == "0" ]]; then
      unique+=("$token")
    fi
  done

  if [[ ${#unique[@]} -gt 1 ]]; then
    _stack_mode_conflict "${unique[0]}" "${unique[1]}"
    return 1
  fi

  if [[ ${#unique[@]} -eq 1 ]]; then
    _stack_mode_apply_token "${unique[0]}" || return 1
  else
    # Bare start: resolve from STORAGE_BACKEND in the environment (caller sources .env first
    # only when needed — here we read already-exported vars).
    local backend
    backend="$(printf '%s' "${STORAGE_BACKEND:-mongodb}" | tr '[:upper:]' '[:lower:]')"
    if [[ "$backend" == "mongo" ]]; then
      backend=mongodb
    fi
    case "$backend" in
      postgres)
        # Host decides location; default cloud when URI looks hosted, else local.
        # Without URI yet, prefer cloud so ensure_env demands DATABASE_URL.
        STACK_DB_TYPE=postgres
        if [[ -n "${DATABASE_URL:-}" ]] && [[ "${DATABASE_URL}" == *"localhost"* || "${DATABASE_URL}" == *"127.0.0.1"* ]]; then
          STACK_LOCATION=local
        else
          STACK_LOCATION=cloud
        fi
        ;;
      mongodb)
        STACK_DB_TYPE=mongodb
        STACK_LOCATION=cloud
        ;;
      *)
        _stack_mode_error "ERROR: unknown STORAGE_BACKEND=${STORAGE_BACKEND:-}"
        _stack_mode_error "Set STORAGE_BACKEND to mongodb or postgres (legacy alias: mongo)."
        return 1
        ;;
    esac
    STACK_STORAGE_MODE="${STACK_DB_TYPE}-${STACK_LOCATION}"
  fi

  if [[ "$STACK_DB_TYPE" == "mongodb" && "$STACK_LOCATION" == "local" ]]; then
    LOCAL_ATLAS=1
  fi
  if [[ "$STACK_DB_TYPE" == "postgres" && "$STACK_LOCATION" == "local" ]]; then
    LOCAL_POSTGRES=1
  fi

  FORCE_BUILD="${FORCE_BUILD:-0}"
  if [[ "$force_build" == "1" || "${RAG_FORCE_BUILD:-}" == "1" ]]; then
    FORCE_BUILD=1
  fi

  local dep
  for dep in "${deprecations[@]+"${deprecations[@]}"}"; do
    echo "Deprecated: ${dep}" >&2
  done

  export STACK_DB_TYPE STACK_LOCATION STACK_STORAGE_MODE LOCAL_ATLAS LOCAL_POSTGRES FORCE_BUILD
  return 0
}

# Mode-aware env requirements. Caller must have sourced .env when present.
# Returns 0 when required URIs are present; 1 with remediation otherwise.
ensure_stack_mode_env() {
  case "${STACK_STORAGE_MODE:-}" in
    mongodb-local)
      return 0
      ;;
    mongodb-cloud)
      if [[ -z "${MONGODB_URI:-}" ]] || [[ "$MONGODB_URI" == *"your_mongodb_atlas_uri_here"* ]]; then
        _stack_mode_error "Set a real MONGODB_URI in .env (Atlas connection string), or use --mongodb-local."
        return 1
      fi
      return 0
      ;;
    postgres-local | postgres-cloud)
      if [[ -z "${DATABASE_URL:-}" ]] && [[ "${STACK_LOCATION}" == "cloud" ]]; then
        _stack_mode_error "Set DATABASE_URL in .env for --postgres-cloud (Supabase Session mode URI)."
        return 1
      fi
      # Local compose exports DATABASE_URL for the server; host CLI still prints hints.
      # Never require MONGODB_URI for postgres modes.
      return 0
      ;;
    *)
      _stack_mode_error "ERROR: STACK_STORAGE_MODE unset — call resolve_stack_mode first"
      return 1
      ;;
  esac
}

example_config_for_stack_mode() {
  case "${STACK_STORAGE_MODE:-}" in
    mongodb-local | mongodb-cloud)
      echo "configs/mongodb/example-local.yaml"
      ;;
    postgres-local | postgres-cloud)
      echo "configs/supabase/example-local.yaml"
      ;;
    *)
      echo "configs/mongodb/example-local.yaml"
      ;;
  esac
}
