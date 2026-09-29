"""Document ↔ row mapping for the SQLite adapter.

The StorageBackend port passes whole documents around. SQLite stores promoted,
queryable fields as columns and the remainder as a TEXT JSON blob, mirroring the
Postgres adapter's promoted-columns-plus-JSON-blob pattern.

SQLite has no native JSONB; all round-trips go through json.dumps / json.loads.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

# Columns promoted out of the JSON blob, per table. They are the single source
# of truth on read, so they are stripped before the blob is written.
EXPERIMENT_COLUMNS = (
    "experiment_id",
    "experiment_name",
    "status",
    "created_at",
    "started_at",
    "completed_at",
    "vector_store_snapshot",
)
RUN_COLUMNS = (
    "run_id",
    "experiment_id",
    "phase",
    "created_at",
    "updated_at",
    "embedding_dimensions",
)
RESULT_COLUMNS = ("experiment_id", "run_id", "query_id", "query_text")

_DERIVED_KEYS = ("_id",)


def _json_default(value: object) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, set | frozenset):
        return sorted(value)
    return str(value)


def to_json(doc: dict, promoted: tuple[str, ...]) -> str:
    """Serialize the non-promoted part of a document to a JSON string."""
    skip = set(promoted) | set(_DERIVED_KEYS)
    return json.dumps({k: v for k, v in doc.items() if k not in skip}, default=_json_default)


def _parse_doc(text: str | None) -> dict:
    if not text:
        return {}
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def experiment_row_to_doc(row: dict, *, include_id: bool = False) -> dict:
    """Rebuild an experiment document from its SQLite row."""
    doc = _parse_doc(row.get("doc"))
    doc.update(
        {
            "experiment_id": row["experiment_id"],
            "experiment_name": row["experiment_name"],
            "status": row["status"],
            "created_at": _parse_datetime(row.get("created_at")),
            "started_at": _parse_datetime(row.get("started_at")),
            "completed_at": _parse_datetime(row.get("completed_at")),
        }
    )
    # Decode vector_store_snapshot JSON blob if present
    snapshot_raw = row.get("vector_store_snapshot")
    if snapshot_raw:
        try:
            doc["vector_store_snapshot"] = json.loads(snapshot_raw)
        except (json.JSONDecodeError, TypeError):
            doc["vector_store_snapshot"] = None
    else:
        doc["vector_store_snapshot"] = None
    if include_id:
        doc["_id"] = row["experiment_id"]
    return doc


def run_row_to_doc(row: dict) -> dict:
    """Rebuild a run_status document from its SQLite row."""
    doc = _parse_doc(row.get("doc"))
    doc.update(
        {
            "run_id": row["run_id"],
            "experiment_id": row["experiment_id"],
            "phase": row["phase"],
            "created_at": _parse_datetime(row.get("created_at")),
            "updated_at": _parse_datetime(row.get("updated_at")),
        }
    )
    dims = row.get("embedding_dimensions")
    if dims is not None:
        doc["embedding_dimensions"] = int(dims)
    else:
        doc["embedding_dimensions"] = None
    return doc


def result_row_to_doc(row: dict) -> dict:
    """Rebuild a result document from its SQLite row."""
    doc = _parse_doc(row.get("doc"))
    doc.update(
        {
            "experiment_id": row["experiment_id"],
            "run_id": row["run_id"],
            "query_id": row["query_id"],
            "query_text": row["query_text"],
        }
    )
    return doc


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse ISO string or pass through datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def serialize_datetime(value: datetime | None) -> str | None:
    """Serialize datetime to ISO string for SQLite storage."""
    if value is None:
        return None
    return value.isoformat()
