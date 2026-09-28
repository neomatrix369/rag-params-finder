#!/bin/bash
# Read scripts/lib/stores.tsv without per-store case branches.
# Bash 3.2 safe: no associative arrays. Callers that expand arrays use the guarded form.
# Source from project root or via this file's directory.

store_manifest_path() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  echo "${here}/stores.tsv"
}

_store_row_skipped() {
  local provider="$1"
  [[ -z "$provider" || "$provider" == \#* || "$provider" == provider ]]
}

store_is_provider() {
  local want="$1"
  local provider rest
  while IFS=$'\t' read -r provider rest; do
    _store_row_skipped "$provider" && continue
    if [[ "$provider" == "$want" ]]; then
      return 0
    fi
  done < "$(store_manifest_path)"
  return 1
}

store_field() {
  local want="$1"
  local column="$2"
  local provider profile local_flag probe required_env can_host example_config volumes
  while IFS=$'\t' read -r provider profile local_flag probe required_env can_host example_config volumes; do
    _store_row_skipped "$provider" && continue
    if [[ "$provider" != "$want" ]]; then
      continue
    fi
    if [[ "$column" == "profile" ]]; then
      echo "$profile"
    elif [[ "$column" == "local_flag" ]]; then
      echo "$local_flag"
    elif [[ "$column" == "health_probe" ]]; then
      echo "$probe"
    elif [[ "$column" == "required_env" ]]; then
      echo "$required_env"
    elif [[ "$column" == "can_host_run_state" ]]; then
      echo "$can_host"
    elif [[ "$column" == "example_config" ]]; then
      echo "$example_config"
    elif [[ "$column" == "volumes" ]]; then
      echo "$volumes"
    fi
    return 0
  done < "$(store_manifest_path)"
  return 1
}

# each_store fn — fn receives provider profile local_flag probe required_env can_host
each_store() {
  local fn="$1"
  local provider profile local_flag probe required_env can_host example_config volumes
  while IFS=$'\t' read -r provider profile local_flag probe required_env can_host example_config volumes; do
    _store_row_skipped "$provider" && continue
    "$fn" "$provider" "$profile" "$local_flag" "$probe" "$required_env" "$can_host"
  done < "$(store_manifest_path)"
}

store_container_name() {
  local provider="$1"
  local env_name
  env_name="RAG_$(printf '%s' "$provider" | tr '[:lower:]' '[:upper:]')_LOCAL_CONTAINER"
  local fallback="rag-params-finder-${provider}-local"
  local configured="${!env_name:-}"
  if [[ -n "$configured" ]]; then
    echo "$configured"
    return 0
  fi
  echo "$fallback"
}

# Compose --profile flags for every registered local store, one token per line.
store_down_profile_flags() {
  local provider profile rest
  while IFS=$'\t' read -r provider profile rest; do
    _store_row_skipped "$provider" && continue
    printf '%s\n' "--profile"
    printf '%s\n' "$profile"
  done < "$(store_manifest_path)"
}
