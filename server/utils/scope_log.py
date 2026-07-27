"""Option A log scope tags: ``[rag-params-finder] [Scope] operation — details``."""

from __future__ import annotations

import logging

PRODUCT_PREFIX = "rag-params-finder"

_SCOPE_OVERRIDES: dict[str, str] = {
    "server.main": "Server",
    "server.settings": "settings",
    "server.api.experiments": "experimentsAPI",
    "server.api.experiments_shared": "experimentsShared",
    "server.api.runs": "runsAPI",
    "server.core.orchestrator": "Orchestrator",
    "server.core.executors": "executors",
    "server.core.startup_reconciliation": "startupReconciliation",
    "server.core.embedding.embedder": "Embedder",
    "server.core.embedding.local_embedder": "localEmbedder",
    "server.core.embedding.rate_limiter": "rateLimiter",
    "server.core.retrieval.retriever_mongo": "Retriever",
    "server.core.retrieval.retriever_postgres": "RetrieverPostgres",
    "server.core.rerank.reranker": "Reranker",
    "server.core.rerank.local_reranker": "localReranker",
    # Deprecated shim paths (Slice 45 — keep until shims removed)
    "server.core.reranker": "Reranker",
    "server.core.local_reranker": "localReranker",
    # Deprecated shim paths (Slice 45 — keep until shims removed)
    "server.core.embedder": "Embedder",
    "server.core.local_embedder": "localEmbedder",
    "server.core.retriever_mongo": "Retriever",
    "server.core.retriever_postgres": "RetrieverPostgres",
    "server.core.rate_limiter": "rateLimiter",
    "server.core.data_loader": "dataLoader",
    "server.core.query_loader": "queryLoader",
    "server.core.atlas_storage": "atlasStorage",
    "server.core.results_analyzer": "resultsAnalyzer",
    "server.core.model_registry": "modelRegistry",
    "server.db.mongo.atlas": "atlasDB",
    "server.db.mongo.indexes": "indexes",
    "server.db.atlas": "atlasDB",
    "server.db.indexes": "indexes",
    "server.utils.metadata": "metadata",
    "cli.main": "CLI",
    "cli.api_client": "apiClient",
    "cli.config_loader": "configLoader",
}


def resolve_scope(logger_name: str) -> str:
    """Map ``logging`` logger name to an Option A scope tag."""
    if logger_name in _SCOPE_OVERRIDES:
        return _SCOPE_OVERRIDES[logger_name]
    if logger_name.startswith("server.core.chunkers"):
        return f"chunkers/{logger_name.split('.')[-1]}"
    parts = logger_name.split(".")
    return parts[-1] if parts else logger_name


class ScopeFilter(logging.Filter):
    """Attach ``log_scope`` to each record for Option A formatting."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.log_scope = resolve_scope(record.name)  # type: ignore[attr-defined]
        return True
