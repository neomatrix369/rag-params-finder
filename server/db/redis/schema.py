"""Redis index schema — SSOT for FT.CREATE field definitions.

Two VECTOR fields per index (D4): ``embedding_384`` and ``embedding_1024``.
TAG fields for the three mandatory isolation filters: ``embedding_model``,
``experiment_id``, ``run_id``.
HNSW with COSINE distance (score = 1 − d/2 where d ∈ [0,2] is the raw
COSINE distance Redis returns for a pair; equivalent to (1 + cosine) / 2).
"""

from __future__ import annotations

INDEX_PREFIX = "rpf:chunk:"
CHUNK_KEY_TEMPLATE = "rpf:chunk:{experiment_id}:{run_id}:{chunk_id}"

VECTOR_FIELDS: dict[int, str] = {384: "embedding_384", 1024: "embedding_1024"}
SUPPORTED_DIMS: frozenset[int] = frozenset(VECTOR_FIELDS)

# HNSW index parameters (match ES defaults for comparability).
_HNSW_M = 16
_HNSW_EF_CONSTRUCTION = 200

# Eviction policies that cannot silently delete vector data.
# allkeys-* policies evict ANY key (including our vectors) → reject.
ACCEPTED_EVICTION_POLICIES: frozenset[str] = frozenset(
    {
        "noeviction",
        "volatile-lru",
        "volatile-lfu",
        "volatile-random",
        "volatile-ttl",
    }
)


def index_name_for(prefix: str) -> str:
    """Single chunks index. Default prefix ``rpf`` → ``rpf:chunks``."""
    cleaned = prefix.strip() or "rpf"
    return f"{cleaned}:chunks"


def field_for_dims(dimensions: int) -> str:
    """Return the VECTOR field name for a supported width, or raise."""
    field = VECTOR_FIELDS.get(dimensions)
    if field is None:
        supported = ", ".join(str(dim) for dim in sorted(SUPPORTED_DIMS))
        raise ValueError(
            f"Dimension mismatch: {dimensions}-dim embeddings are not supported "
            f"(capabilities.supported_dims: {supported}). "
            "SPLADE and other widths are rejected before a query is sent."
        )
    return field


def build_schema_fields() -> list[object]:
    """Return the field list for FT.CREATE (requires redis-py imports)."""
    from redis.commands.search.field import (  # type: ignore[import-not-found]
        NumericField,
        TagField,
        TextField,
        VectorField,
    )

    hnsw_attrs_384 = {
        "TYPE": "FLOAT32",
        "DIM": 384,
        "DISTANCE_METRIC": "COSINE",
        "M": _HNSW_M,
        "EF_CONSTRUCTION": _HNSW_EF_CONSTRUCTION,
    }
    hnsw_attrs_1024 = {**hnsw_attrs_384, "DIM": 1024}
    return [
        TextField("text"),
        TagField("embedding_model"),
        TagField("experiment_id"),
        TagField("run_id"),
        TagField("chunking_method"),
        NumericField("chunk_size"),
        NumericField("overlap"),
        VectorField("embedding_384", "HNSW", hnsw_attrs_384),
        VectorField("embedding_1024", "HNSW", hnsw_attrs_1024),
    ]


def chunk_key(experiment_id: str, run_id: str, chunk_id: str) -> str:
    """Canonical HASH key for a chunk. No TTL is ever set on these keys."""
    return CHUNK_KEY_TEMPLATE.format(
        experiment_id=experiment_id,
        run_id=run_id,
        chunk_id=chunk_id,
    )
