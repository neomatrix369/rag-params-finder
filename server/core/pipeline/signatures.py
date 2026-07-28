"""Sweep parameter signatures for resume/skip logic."""

from __future__ import annotations

from server.db.ports.store_factory import get_storage_backend
from server.models.config import RunParams
from server.settings import settings

ParamSignature = tuple[
    str,
    str,
    str,
    str,
    int,
    int,
    str,
    str,
    str | None,
]


def _params_signature(params: RunParams) -> ParamSignature:
    return (
        params.database_provider,
        params.embedding_provider,
        params.embedding_model,
        params.chunking_method.value,
        params.chunk_size,
        params.overlap,
        params.retrieval_method.value,
        params.retrieval_provider,
        params.retrieval_model,
    )


def _stored_enum_value(value: object | None) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value)


def _run_doc_signature(run: dict) -> ParamSignature:
    return (
        str(run.get("database_provider") or settings.default_database_provider()),
        str(run.get("embedding_provider") or ""),
        str(run.get("embedding_model") or ""),
        _stored_enum_value(run.get("chunking_method")),
        int(run.get("chunk_size") or 0),
        int(run.get("overlap") or 0),
        _stored_enum_value(run.get("retrieval_method")),
        str(run.get("retrieval_provider") or ""),
        run.get("retrieval_model"),
    )


def _completed_param_signatures(experiment_id: str) -> set[ParamSignature]:
    rows = get_storage_backend().find_completed_run_sigs(experiment_id)
    return {_run_doc_signature(run) for run in rows}
