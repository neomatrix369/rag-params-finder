"""Elasticsearch index mapping — SSOT is ``index_mapping.json`` beside this module.

Elasticsearch 9 indexes float ``dense_vector`` fields as quantized HNSW
(``int8_hnsw`` / ``bbq_hnsw``) unless ``index_options.type`` is set to
``hnsw``. The shipped mapping states ``hnsw``, ``m=16``, and
``ef_construction=100`` explicitly so a future server default cannot drift.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VECTOR_FIELDS: dict[int, str] = {384: "embedding_384", 1024: "embedding_1024"}
SUPPORTED_DIMS: frozenset[int] = frozenset(VECTOR_FIELDS)
QUANTIZED_INDEX_TYPES: frozenset[str] = frozenset({"bbq_hnsw", "int8_hnsw"})
UNQUANTIZED_HNSW_REQUIRED = (
    "unquantized HNSW required: dense_vector index_options.type must be "
    "'hnsw', not bbq_hnsw or int8_hnsw. Recreate the index from "
    "server/db/elasticsearch/index_mapping.json (explicit hnsw, m=16, "
    "ef_construction=100, similarity=cosine)."
)

_MAPPING_PATH = Path(__file__).with_name("index_mapping.json")


def load_index_body() -> dict[str, Any]:
    """Return the create-index body (settings + mappings)."""
    body: dict[str, Any] = json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))
    return body


def index_name_for(prefix: str) -> str:
    """Single chunks index. Default prefix ``rpf`` → ``rpf-chunks``."""
    cleaned = prefix.strip() or "rpf"
    return f"{cleaned}-chunks"


def field_for_dims(dimensions: int) -> str:
    """Return the dense_vector field for a supported width, or raise."""
    field = VECTOR_FIELDS.get(dimensions)
    if field is None:
        supported = ", ".join(str(dim) for dim in sorted(SUPPORTED_DIMS))
        raise ValueError(
            f"Dimension mismatch: {dimensions}-dim embeddings are not supported "
            f"(capabilities.supported_dims: {supported}). "
            "SPLADE and other widths are rejected before a query is sent."
        )
    return field


def properties_of(mapping_response: dict[str, Any]) -> dict[str, Any]:
    """Read ``properties`` from a get-mapping response or a raw mappings body."""
    if "properties" in mapping_response:
        properties = mapping_response["properties"]
        return properties if isinstance(properties, dict) else {}
    mappings = mapping_response.get("mappings")
    if isinstance(mappings, dict):
        properties = mappings.get("properties")
        if isinstance(properties, dict):
            return properties
    for value in mapping_response.values():
        if isinstance(value, dict):
            nested = properties_of(value)
            if nested:
                return nested
    return {}


def quantized_dense_fields(mapping_response: dict[str, Any]) -> list[str]:
    """Names of dense_vector fields whose index type is quantized HNSW."""
    found: list[str] = []
    for name, spec in properties_of(mapping_response).items():
        if not isinstance(spec, dict) or spec.get("type") != "dense_vector":
            continue
        index_type = str((spec.get("index_options") or {}).get("type") or "")
        if index_type in QUANTIZED_INDEX_TYPES:
            found.append(name)
    return found
