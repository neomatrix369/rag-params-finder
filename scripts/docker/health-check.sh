#!/bin/bash
# Post-start smoke check for Docker or manual stack (server :8001, dashboard :5374).
# Always validates the active storage backend via /healthz, and also probes any
# local MongoDB / Postgres containers that are present (parity for dual-DB laptops).
set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Optional: reuse compose container name constants when available.
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../lib/compose.sh" 2>/dev/null || true
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../lib/store_manifest.sh" 2>/dev/null || true

SERVER_URL="${SERVER_URL:-http://localhost:8001}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5374}"

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

_probe_manifest_row() {
  local provider="$1"
  local _profile="$2"
  local _flag="$3"
  local probe="$4"
  local container
  container="$(store_container_name "$provider")"
  if ! command -v docker >/dev/null 2>&1; then
    echo "SKIP ${provider} (docker not available)"
    return 0
  fi
  if ! _container_present "$container"; then
    echo "SKIP ${provider} container (not present)"
    return 0
  fi
  if [[ "$probe" == http://* || "$probe" == https://* ]]; then
    if curl -sf "$probe" >/dev/null 2>&1; then
      check "${provider} health probe ${probe}" true
    else
      check "${provider} health probe ${probe}" false
      echo "     Hint: ./start-services.sh ${provider} status"
      echo "     For Elasticsearch, vm.max_map_count must be at least 262144."
    fi
    return 0
  fi
  if [[ "$probe" == cmd:* ]]; then
    local command="${probe#cmd:}"
    # shellcheck disable=SC2086
    if docker exec "$container" $command >/dev/null 2>&1; then
      check "${provider} cmd probe in ${container}" true
    else
      check "${provider} cmd probe in ${container}" false
      echo "     Hint: ./start-services.sh ${provider} status"
    fi
    return 0
  fi
  check "${provider} health probe (unsupported ${probe})" false
}

probe_local_db_containers() {
  if ! declare -F each_store >/dev/null; then
    echo "SKIP manifest probes (store_manifest.sh unavailable)"
    return 0
  fi
  each_store _probe_manifest_row
}

run_health_checks() {
echo "=== rag-params-finder health check ==="

health_json="$(curl -sf "${SERVER_URL}/healthz" 2>/dev/null || true)"
if [[ -z "$health_json" ]]; then
  check "server ${SERVER_URL}/healthz" false
else
  check "server ${SERVER_URL}/healthz responds" true
  if command -v python3 >/dev/null 2>&1; then
    ok_flag="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('ok') else 'false')" "$health_json")"
    backend="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('storage_backend') or '')" "$health_json")"
    vector_backend="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('vector_store_backend') or d.get('storage_backend') or '')" "$health_json")"
    storage_mode="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('storage_mode') or '')" "$health_json")"
    vector_ok="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('stores',{}).get('vector',{}).get('ok') else 'false')" "$health_json")"
    run_ok="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('stores',{}).get('run_state',{}).get('ok') else 'false')" "$health_json")"
    if [[ -n "$storage_mode" ]]; then
      echo "INFO storage_mode=${storage_mode} storage_backend=${backend} vector_store_backend=${vector_backend}"
    fi
    if [[ "$vector_ok" == "true" ]]; then
      check "vector store ${vector_backend} via /healthz" true
    else
      check "vector store ${vector_backend} via /healthz" false
      echo "     Hint: ./start-services.sh ${vector_backend} status"
    fi
    if [[ "$run_ok" == "true" ]]; then
      check "run-state store ${backend} via /healthz" true
    else
      check "run-state store ${backend} via /healthz" false
      echo "     Hint: confirm STORAGE_BACKEND and its URI, then re-run ./start-services.sh"
    fi
    if [[ "$ok_flag" != "true" ]]; then
      check "storage backend ready via server (ok=false)" false
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
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  run_health_checks
fi
