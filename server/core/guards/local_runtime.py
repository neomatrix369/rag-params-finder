"""Compose-local store identity for /healthz. Cloud modes omit these fields.

Image tags and container names mirror docker-compose.yml defaults. An operator
override of the container env var is not visible to the server process.
"""

from __future__ import annotations

LOCAL_STORE_IMAGES: dict[str, str] = {
    "mongodb": "mongodb/mongodb-atlas-local:8.3.3",
    "postgres": "pgvector/pgvector:0.8.5-pg16",
    "elasticsearch": "docker.elastic.co/elasticsearch/elasticsearch:9.5.0",
}


def local_container_name(provider: str) -> str:
    """Default Compose container name for a local store profile."""
    return f"rag-params-finder-{provider}-local"


def local_runtime_fields(provider: str, mode: str) -> dict[str, str]:
    """Container and image for a ``*-local`` mode. Empty for cloud modes."""
    if not mode.endswith("-local"):
        return {}
    fields = {"container": local_container_name(provider)}
    image = LOCAL_STORE_IMAGES.get(provider)
    if image is not None:
        fields["image"] = image
    return fields
