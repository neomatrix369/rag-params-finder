#!/bin/bash
# Poll GET /experiments/{id} until terminal status (for smoke tests and CI).
# Usage: ./scripts/wait-experiment.sh <experiment-id>
set -e
set -o pipefail

EXPERIMENT_ID="${1:?usage: ./scripts/wait-experiment.sh <experiment-id>}"
SERVER_URL="${SERVER_URL:-http://localhost:8001}"
MAX_TRIES="${WAIT_EXPERIMENT_MAX_TRIES:-180}"
INTERVAL_S="${WAIT_EXPERIMENT_INTERVAL_S:-5}"

for ((i = 1; i <= MAX_TRIES; i++)); do
  body="$(curl -sf "${SERVER_URL}/experiments/${EXPERIMENT_ID}" 2>/dev/null || true)"
  if [[ -z "$body" ]]; then
    echo "[$i] status=unreachable"
  else
    status="$(python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" <<<"$body")"
    run_phases="$(python3 -c "
import json, sys
d = json.load(sys.stdin)
print(','.join(f\"pad{r.get('padding','?')}:{r.get('phase','?')}\" for r in d.get('runs', [])))
" <<<"$body")"
    echo "[$i] status=${status} runs=[${run_phases}]"
    case "$status" in
      complete | failed | partial | cancelled)
        exit 0
        ;;
    esac
  fi
  sleep "$INTERVAL_S"
done

echo "Timed out waiting for experiment ${EXPERIMENT_ID}" >&2
exit 1
