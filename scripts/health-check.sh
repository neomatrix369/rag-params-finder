#!/bin/bash
# Post-start smoke check for Docker or manual stack (server :8001, dashboard :5374)
set -e
set -o pipefail

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

echo "=== rag-params-finder health check ==="

health_json="$(curl -sf "${SERVER_URL}/healthz" 2>/dev/null || true)"
if [[ -z "$health_json" ]]; then
  check "server ${SERVER_URL}/healthz" false
else
  check "server ${SERVER_URL}/healthz responds" true
  if command -v python3 >/dev/null 2>&1; then
    ok_flag="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('ok') else 'false')" "$health_json")"
    backend="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('storage_backend') or 'mongo')" "$health_json")"
    if [[ "$ok_flag" != "true" ]]; then
      check "storage backend ready via server (ok=false, backend=${backend})" false
      echo "     Hint: for postgres set DATABASE_URL; for mongo set MONGODB_URI / Atlas Network Access"
    elif [[ "$backend" == "postgres" ]]; then
      postgres_status="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('postgres',''))" "$health_json")"
      if [[ "$postgres_status" == "ok" ]]; then
        check "Postgres ping via server (postgres=ok)" true
      else
        check "Postgres ping via server (postgres=${postgres_status})" false
        echo "     Hint: verify DATABASE_URL and that ./start-services.sh --postgres is up"
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

check "frontend ${FRONTEND_URL}/" curl -sf "${FRONTEND_URL}/"

echo "===================================="
if [[ "$failures" -gt 0 ]]; then
  echo "Health check failed ($failures issue(s))."
  exit 1
fi
echo "All checks passed."
