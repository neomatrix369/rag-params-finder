#!/bin/bash
# Detect whether Docker Compose images need rebuilding (used by start-services.sh).
set -e
set -o pipefail

stat_mtime_epoch() {
  local target="$1"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    stat -f %m "$target"
  else
    stat -c %Y "$target"
  fi
}

docker_image_created_epoch() {
  local image="$1"
  local created
  created=$(docker image inspect -f '{{.Created}}' "$image" 2>/dev/null) || return 1
  CREATED="$created" python3 - <<'PY'
import datetime
import os

created = os.environ["CREATED"]
print(int(datetime.datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()))
PY
}

docker_newest_mtime_epoch() {
  local newest=0
  local path file epoch
  for path in "$@"; do
    [[ -e "$path" ]] || continue
    if [[ -f "$path" ]]; then
      epoch=$(stat_mtime_epoch "$path")
      if (( epoch > newest )); then
        newest=$epoch
      fi
    elif [[ -d "$path" ]]; then
      while IFS= read -r -d '' file; do
        epoch=$(stat_mtime_epoch "$file")
        if (( epoch > newest )); then
          newest=$epoch
        fi
      done < <(
        find "$path" -type f \
          \( -path '*/node_modules/*' -o -path '*/.venv/*' -o -path '*/__pycache__/*' \
          -o -path '*/.git/*' -o -path '*/dist/*' -o -path '*/.pytest_cache/*' \) -prune \
          -o -type f -print0 2>/dev/null
      )
    fi
  done
  echo "$newest"
}

docker_service_needs_build() {
  local image="$1"
  shift
  local image_epoch source_epoch

  if ! image_epoch=$(docker_image_created_epoch "$image"); then
    echo "  missing image: ${image}" >&2
    return 0
  fi

  source_epoch=$(docker_newest_mtime_epoch "$@")
  if (( source_epoch == 0 )); then
    echo "  no build context files found for ${image}" >&2
    return 0
  fi

  if (( source_epoch > image_epoch )); then
    echo "  stale image: ${image} (source newer than image)" >&2
    return 0
  fi

  return 1
}

# Exit 0 when compose should run `up --build`, 1 when `up -d` is enough.
docker_compose_needs_build() {
  local repo_root="${1:?repo root required}"

  if [[ "${FORCE_BUILD:-0}" == "1" ]]; then
    echo "Force rebuild requested (--force-build or RAG_FORCE_BUILD=1)." >&2
    return 0
  fi

  local server_image="${SERVER_IMAGE_NAME:-rag-params-finder-server}"
  local frontend_image="${FRONTEND_IMAGE_NAME:-rag-params-finder-frontend}"
  local frontend_dockerfile="docker/frontend.Dockerfile"
  if [[ "${RAG_DEV_STACK:-}" == "1" ]]; then
    frontend_dockerfile="docker/frontend.dev.Dockerfile"
  fi

  if docker_service_needs_build "$server_image" \
    "${repo_root}/docker/server.Dockerfile" \
    "${repo_root}/pyproject.toml" \
    "${repo_root}/uv.lock" \
    "${repo_root}/README.md" \
    "${repo_root}/server" \
    "${repo_root}/cli" \
    "${repo_root}/docker-compose.yml"; then
    return 0
  fi

  if docker_service_needs_build "$frontend_image" \
    "${repo_root}/${frontend_dockerfile}" \
    "${repo_root}/frontend" \
    "${repo_root}/docker-compose.yml" \
    "${repo_root}/docker-compose.dev.yml"; then
    return 0
  fi

  echo "Build context unchanged — reusing existing images." >&2
  return 1
}
