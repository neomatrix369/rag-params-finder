"""Reject config engine ↔ server STORAGE_BACKEND mismatches before preflight I/O.

Distinct from catalog/index preflight 422 (``SearchIndexMismatchError``): this
guard only compares YAML ``database_provider`` (after normalize) to the live
process backend and never touches Atlas Admin or Postgres catalogs.
"""

from __future__ import annotations

from server.core.guards.health_check import resolve_storage_mode
from server.models.config import ExperimentConfig, normalize_database_provider
from server.settings import normalize_storage_backend, settings


class ConfigBackendMismatchError(Exception):
    """Config engine does not match the running server's STORAGE_BACKEND."""


def _location_suffix(storage_mode: str) -> str:
    return "cloud" if storage_mode.endswith("-cloud") else "local"


def _example_config_for_engine(engine: str) -> str:
    if engine == "postgres":
        return "configs/supabase/example-local.yaml"
    return "configs/mongodb/example-local.yaml"


def format_config_backend_mismatch(
    *,
    config_engine: str,
    server_backend: str,
    storage_mode: str,
) -> str:
    """Build the canonical 422 detail (Slice 37 template)."""
    location = _location_suffix(storage_mode)
    restart = f"./start-services.sh --{config_engine}-{location}"
    alternate = _example_config_for_engine(server_backend)
    return (
        f"Config engine mismatch: database_provider={config_engine} but "
        f"server storage_backend={server_backend} (storage_mode={storage_mode}).\n"
        f"Restart with matching backend: {restart}\n"
        f"Or submit a {server_backend} config, e.g. {alternate}"
    )


def validate_config_backend_match(config: ExperimentConfig) -> None:
    """Raise ConfigBackendMismatchError when YAML engine ≠ process backend.

    Call **before** search-index / SIE preflight and before experiment persist.
    """
    server_backend = normalize_storage_backend(settings.storage_backend or "mongodb")
    config_engine = normalize_database_provider(config.database_provider)
    if config_engine == server_backend:
        return
    storage_mode = resolve_storage_mode()
    raise ConfigBackendMismatchError(
        format_config_backend_mismatch(
            config_engine=config_engine,
            server_backend=server_backend,
            storage_mode=storage_mode,
        )
    )
