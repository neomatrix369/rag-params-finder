"""GET /api/stores — registry catalog with secrets left on the server.

The CLI and dashboard read capabilities, UI labels, the example config, and
an index-name summary from this payload. Connection strings and API keys are
never copied into it.
"""

from __future__ import annotations

import json
from typing import Protocol, cast

from fastapi import APIRouter

from server.db.ports.registry import (
    example_config_for,
    known_vector_stores,
    resolve_catalog,
    vector_store_can_host_run_state,
)
from server.db.ports.vector_store import VectorCapabilities
from server.settings import normalize_storage_backend, settings

router = APIRouter()


class _CatalogAdapter(Protocol):
    """Class-level catalog surface every registered vector adapter exposes."""

    @classmethod
    def ui_labels(cls) -> dict[str, str]: ...

    @classmethod
    def capabilities(cls) -> VectorCapabilities: ...

    @classmethod
    def index_summary(cls) -> dict[str, object]: ...


def _capabilities_public(caps: VectorCapabilities) -> dict[str, object]:
    return {
        "retrieval_methods": sorted(method.value for method in caps.retrieval_methods),
        "similarity_metrics": sorted(caps.similarity_metrics),
        "index_types": sorted(caps.index_types),
        "supported_embedding_dims": sorted(caps.supported_embedding_dims),
        "supports_metadata_filters": caps.supports_metadata_filters,
        "can_host_run_state": caps.can_host_run_state,
    }


def _configured_secrets() -> list[str]:
    candidates = (
        settings.elasticsearch_api_key,
        settings.mongodb_uri,
        settings.database_url,
        settings.atlas_public_key,
        settings.atlas_private_key,
    )
    return [value.strip() for value in candidates if value and value.strip()]


def build_stores_payload() -> dict[str, object]:
    """Return the public store catalog for the active vector store."""
    active = normalize_storage_backend(settings.vector_store_backend or settings.storage_backend)
    stores: list[dict[str, object]] = []
    for provider in sorted(known_vector_stores()):
        adapter = cast(type[_CatalogAdapter], resolve_catalog(provider))
        stores.append(
            {
                "provider": provider,
                "active": provider == active,
                "example_config": example_config_for(provider),
                "can_host_run_state": vector_store_can_host_run_state(provider),
                "labels": adapter.ui_labels(),
                "capabilities": _capabilities_public(adapter.capabilities()),
                "index_summary": adapter.index_summary(),
            }
        )
    payload: dict[str, object] = {"active": active, "stores": stores}
    dumped = json.dumps(payload)
    for secret in _configured_secrets():
        if len(secret) >= 8 and secret in dumped:
            raise RuntimeError("store catalog included a configured secret")
    return payload


@router.get("/stores")
def list_stores() -> dict[str, object]:
    """List registered vector stores, labels, and the active store."""
    return build_stores_payload()
