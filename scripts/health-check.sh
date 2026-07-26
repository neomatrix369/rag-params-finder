#!/bin/bash
# Post-start smoke check for Docker or manual stack (server :8001, dashboard :5374).
# Always validates the active storage backend via /healthz, and also probes any
# local MongoDB / Postgres containers that are present (parity for dual-DB laptops).
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Optional: reuse compose container name constants when available.
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/compose.sh" 2>/dev/null || true

SERVER_URL="${SERVER_URL:-http://localhost:8001}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5374}"
MONGODB_LOCAL_CONTAINER="${RAG_MONGODB_LOCAL_CONTAINER:-rag-params-finder-mongodb-local}"
POSTGRES_LOCAL_CONTAINER="${RAG_POSTGRES_LOCAL_CONTAINER:-rag-params-finder-postgres-local}"

failures=0

check() {
  local label="$1"
  if "${@:2}" >/dev/null 2>&1; then
    echo "OK   $label"
  else
    echo "FAIL $label"
    failures=$((failures + 1))
  fi
}

# Returns 0 when the named container is present (any state).
_container_present() {
  local name="$1"
  command -v docker >/dev/null 2>&1 || return 1
  docker inspect --format='{{.Id}}' "$name" >/dev/null 2>&1
}

# Returns 0 when present and Docker health is healthy (or no Health block but running).
_container_healthy() {
  local name="$1"
  local status health
  status="$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "")"
  [[ "$status" == "running" ]] || return 1
  health="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo "")"
  [[ "$health" == "healthy" || "$health" == "none" ]]
}

probe_local_db_containers() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "SKIP local DB containers (docker not available)"
    return 0
  fi

  if _container_present "$MONGODB_LOCAL_CONTAINER"; then
    if _container_healthy "$MONGODB_LOCAL_CONTAINER"; then
      check "Atlas Local container (${MONGODB_LOCAL_CONTAINER}) healthy" true
    else
      check "Atlas Local container (${MONGODB_LOCAL_CONTAINER}) healthy" false
      echo "     Hint: ./start-services.sh mongodb status"
      echo "           ./start-services.sh mongodb reset   # if FCV / keyfile / invalid RS"
    fi
  else
    echo "SKIP Atlas Local container (not present)"
  fi

  if _container_present "$POSTGRES_LOCAL_CONTAINER"; then
    if _container_healthy "$POSTGRES_LOCAL_CONTAINER"; then
      check "Postgres/pgvector container (${POSTGRES_LOCAL_CONTAINER}) healthy" true
    else
      check "Postgres/pgvector container (${POSTGRES_LOCAL_CONTAINER}) healthy" false
      echo "     Hint: ./start-services.sh postgres status"
      echo "           ./start-services.sh postgres reset   # wipe local volume if corrupt"
    fi
  else
    echo "SKIP Postgres/pgvector container (not present)"
  fi
}

echo "=== rag-params-finder health check ==="

health_json="$(curl -sf "${SERVER_URL}/healthz" 2>/dev/null || true)"
if [[ -z "$health_json" ]]; then
  check "server ${SERVER_URL}/healthz" false
else
  check "server ${SERVER_URL}/healthz responds" true
  if command -v python3 >/dev/null 2>&1; then
    ok_flag="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('ok') else 'false')" "$health_json")"
    backend="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('storage_backend') or 'mongodb')" "$health_json")"
    storage_mode="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('storage_mode') or '')" "$health_json")"
    if [[ -n "$storage_mode" ]]; then
      echo "INFO storage_mode=${storage_mode} storage_backend=${backend}"
    fi
    if [[ "$ok_flag" != "true" ]]; then
      check "storage backend ready via server (ok=false, backend=${backend})" false
      echo "     Hint: for postgres set DATABASE_URL; for mongodb set MONGODB_URI / Atlas Network Access"
    elif [[ "$backend" == "postgres" ]]; then
      postgres_status="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('postgres',''))" "$health_json")"
      if [[ "$postgres_status" == "ok" ]]; then
        check "Postgres ping via server (postgres=ok)" true
      else
        check "Postgres ping via server (postgres=${postgres_status})" false
        echo "     Hint: verify DATABASE_URL and that ./start-services.sh --postgres-local is up"
      fi
    else
      mongodb_status="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('mongodb',''))" "$health_json")"
      if [[ "$mongodb_status" == "ok" ]]; then
        check "MongoDB ping via server (mongodb=ok)" true
      elif [[ "$mongodb_status" == "skipped" ]]; then
        check "MongoDB ping via server (mongodb=skipped — set MONGODB_URI)" false
        echo "     Hint: configure MONGODB_URI in .env for sweeps and Docker health gates"
      else
        check "MongoDB ping via server (mongodb=${mongodb_status})" false
        echo "     Hint: verify Atlas URI and Network Access (0.0.0.0/0 for dev)"
      fi
    fi
  else
    echo "WARN python3 not found — skipping JSON field checks"
  fi
fi

# Dual-local parity: probe whichever DB containers exist, not only the active backend.
probe_local_db_containers

check "frontend ${FRONTEND_URL}/" curl -sf "${FRONTEND_URL}/"

echo "===================================="
if [[ "$failures" -gt 0 ]]; then
  echo "Health check failed ($failures issue(s))."
  exit 1
fi
echo "All checks passed."
