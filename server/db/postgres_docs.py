"""Document ↔ row mapping for the Postgres adapter.

The StorageBackend port passes whole documents around. Postgres stores the
queryable fields as columns and the remainder as JSONB, so every read has to
re-materialise the original document shape — including real ``datetime``
objects, which JSONB can only hold as ISO strings.

Keeping the mapping here means ``postgres_store`` reads as CRUD and nothing else.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from psycopg.types.json import Jsonb

# Columns promoted out of the JSONB blob, per table. They are the single source
# of truth on read, so they are stripped before the blob is written.
EXPERIMENT_COLUMNS = (
    "experiment_id",
    "experiment_name",
    "status",
    "created_at",
    "started_at",
    "completed_at",
)
RUN_COLUMNS = ("run_id", "experiment_id", "phase", "created_at", "updated_at")
RESULT_COLUMNS = ("experiment_id", "run_id", "query_id", "query_text")

# Mongo documents carry `_id`; it is derived from the primary key on read rather
# than stored twice.
_DERIVED_KEYS = ("_id",)

# One nullable vector column per supported embedding dimension.
VECTOR_COLUMNS: dict[int, str] = {384: "embedding_384", 1024: "embedding_1024"}


def _json_default(value: object) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, set | frozenset):
        return sorted(value)
    return str(value)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, default=_json_default)


def to_jsonb(doc: dict, promoted: tuple[str, ...]) -> Jsonb:
    """Wrap the non-promoted part of a document for a JSONB parameter."""
    skip = set(promoted) | set(_DERIVED_KEYS)
    return Jsonb({k: v for k, v in doc.items() if k not in skip}, dumps=_json_dumps)


def experiment_row_to_doc(row: dict, *, include_id: bool = False) -> dict:
    """Rebuild an experiment document from its row.

    ``include_id`` mirrors PyMongo's default projection: readers that use
    ``doc["_id"]`` (boot reconciliation) need it; list endpoints exclude it.
    """
    doc = dict(row["doc"] or {})
    doc.update(
        {
            "experiment_id": row["experiment_id"],
            "experiment_name": row["experiment_name"],
            "status": row["status"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }
    )
    if include_id:
        doc["_id"] = row["experiment_id"]
    return doc


def run_row_to_doc(row: dict) -> dict:
    doc = dict(row["doc"] or {})
    doc.update(
        {
            "run_id": row["run_id"],
            "experiment_id": row["experiment_id"],
            "phase": row["phase"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )
    return doc


def result_row_to_doc(row: dict) -> dict:
    doc = dict(row["doc"] or {})
    doc.update(
        {
            "experiment_id": row["experiment_id"],
            "run_id": row["run_id"],
            "query_id": row["query_id"],
            "query_text": row["query_text"],
        }
    )
    return doc


def vector_column_for(dimensions: int) -> str:
    """Map an embedding dimension to its chunks column.

    Raises for dimensions with no column — notably SPLADE-v3 sparse vectors,
    whose storage is decided in Slice 35.
    """
    column = VECTOR_COLUMNS.get(dimensions)
    if column is None:
        supported = ", ".join(str(d) for d in sorted(VECTOR_COLUMNS))
        raise ValueError(
            f"No Postgres vector column for {dimensions}-dim embeddings "
            f"(supported: {supported}). Sparse/high-dimension models land in Slice 35."
        )
    return column
