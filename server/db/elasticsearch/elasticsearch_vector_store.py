"""ElasticsearchVectorStore — vector-only adapter (cannot host run state)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, cast

from server.core.guards.search_index_plan import SearchIndexAssessment, SearchIndexMismatchError
from server.core.model_registry import get_dimensions
from server.db.elasticsearch.client import (
    ElasticsearchClientMissingError,
    build_client,
    import_elasticsearch_class,
    raise_if_unreachable,
)
from server.db.elasticsearch.elasticsearch_catalog import ElasticsearchCatalog
from server.db.elasticsearch.mapping import (
    SUPPORTED_DIMS,
    UNQUANTIZED_HNSW_REQUIRED,
    field_for_dims,
    index_name_for,
    load_index_body,
    quantized_dense_fields,
)
from server.db.elasticsearch.retriever import search as es_search
from server.db.elasticsearch.uri import cluster_host, elasticsearch_storage_mode
from server.db.ports.retriever_backend import RetrieverBackend
from server.db.ports.stats_common import (
    assemble_experiment_db_stats,
    new_vector_db_group,
    vector_db_group_key,
)
from server.db.ports.vector_store import VectorCapabilities
from server.models.config import ExperimentConfig
from server.models.enums import RetrievalMethod
from server.models.results import SearchResult
from server.settings import settings

log = logging.getLogger(__name__)

_PROVIDER = "elasticsearch"
_BULK_BATCH_SIZE = 500


class ElasticsearchRetrieverBackend:
    """RetrieverBackend over the shared chunks index."""

    def __init__(self, store: ElasticsearchVectorStore) -> None:
        self._store = store

    def search(
        self,
        method: RetrievalMethod,
        query_text: str,
        experiment_id: str,
        embedding_model: str,
        run_id: str,
        top_k: int,
        query_embedding: list[float] | None,
    ) -> list[SearchResult]:
        found = self._store.call(
            lambda: es_search(
                self._store.client(),
                index=self._store.index_name,
                method=method,
                query_text=query_text,
                experiment_id=experiment_id,
                embedding_model=embedding_model,
                run_id=run_id,
                top_k=top_k,
                query_embedding=query_embedding,
            )
        )
        return cast(list[SearchResult], found)


class ElasticsearchVectorStore:
    """VectorStore for one ``{prefix}-chunks`` index. Run state stays elsewhere."""

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            import_elasticsearch_class()
        self._client = client
        self._index = index_name_for(settings.elasticsearch_index_prefix)

    @property
    def index_name(self) -> str:
        return self._index

    @property
    def url(self) -> str:
        return settings.elasticsearch_url.strip()

    def client(self) -> Any:
        """Return the injected client, or open one. Missing extra fails in ``__init__``."""
        if self._client is None:
            self._client = build_client(self.url, settings.elasticsearch_api_key)
        return self._client

    def call(self, action: Callable[[], Any]) -> Any:
        """Run ``action`` and turn connection failures into a clear error."""
        try:
            return action()
        except Exception as exc:
            raise_if_unreachable(exc, self.url)
            raise

    def insert_chunks(self, docs: list[dict]) -> None:
        if not docs:
            return
        run_id: str | None = docs[0].get("run_id") if docs else None
        batches_indexed = 0
        try:
            for start in range(0, len(docs), _BULK_BATCH_SIZE):
                batch = docs[start : start + _BULK_BATCH_SIZE]
                operations = _bulk_operations(self._index, batch)
                response = self.call(
                    lambda: self.client().bulk(
                        operations=operations,
                        refresh="wait_for",
                        request_timeout=60,
                    )
                )
                _raise_on_bulk_errors(response, len(batch))
                batches_indexed += 1
        except Exception:
            if run_id and batches_indexed > 0:
                # Delete partial writes so a retry starts clean.
                try:
                    self.call(
                        lambda: self.client().delete_by_query(
                            index=self._index,
                            query={"term": {"run_id": run_id}},
                            refresh=True,
                        )
                    )
                    log.warning(
                        "ES insert_chunks partial-write cleanup — run_id=%s batches_indexed=%d",
                        run_id,
                        batches_indexed,
                    )
                except Exception as cleanup_exc:
                    log.error(
                        "ES insert_chunks cleanup failed — run_id=%s error=%s",
                        run_id,
                        cleanup_exc,
                    )
            raise

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        response = self.call(
            lambda: self.client().delete_by_query(
                index=self._index,
                query={"term": {"experiment_id": experiment_id}},
                refresh=True,
            )
        )
        return int(_body(response).get("deleted") or 0)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        total = self._count({"term": {"experiment_id": experiment_id}})
        models = list(self._term_counts("embedding_model", experiment_id))
        methods = self._term_counts("chunk_method", experiment_id)
        runs = self._term_counts("run_id", experiment_id)
        breakdown = [
            {"run_id": run_id, "chunks": count, "results": 0}
            for run_id, count in sorted(runs.items())
        ]
        return assemble_experiment_db_stats(
            None,
            database_provider=_PROVIDER,
            collection_name=self._index,
            cluster_host=cluster_host(self.url),
            index_names=[self._index],
            total_chunks=total,
            embedding_models=sorted(models),
            chunking_breakdown=methods,
            total_results=0,
            unique_queries=0,
            runs_with_data=len(runs),
            run_breakdown=breakdown,
        )

    def get_vector_db_stats_grouped(self) -> dict:
        by_experiment = self._term_counts("experiment_id", experiment_id=None)
        if not by_experiment:
            return {"groups": []}
        total_chunks = sum(by_experiment.values())
        stats = self._label_stats(total_chunks)
        group_key = vector_db_group_key(self.storage_mode(), stats["cluster_host"])
        group = new_vector_db_group(group_key, stats)
        group["totals"]["experiment_count"] = len(by_experiment)
        group["totals"]["total_chunks"] = total_chunks
        return {"groups": [group]}

    def retriever(self) -> RetrieverBackend:
        return ElasticsearchRetrieverBackend(self)

    def plan_indexes(self, config: ExperimentConfig) -> SearchIndexAssessment:
        _reject_unsupported_models(config)
        raw = self._mapping_or_none()
        if raw is None:
            return _missing_assessment(self._index)
        _reject_quantized(raw)
        return _ready_assessment(self._index)

    def ensure_indexes(self) -> None:
        raw = self._mapping_or_none()
        if raw is not None:
            _reject_quantized(raw)
            return
        body = load_index_body()
        self.call(
            lambda: self.client().indices.create(
                index=self._index,
                settings=body.get("settings") or {},
                mappings=body.get("mappings") or {},
            )
        )

    def health_check(self) -> bool:
        if not self.url:
            return False
        try:
            return bool(self.client().ping())
        except ElasticsearchClientMissingError:
            return False
        except Exception as exc:
            raise_if_unreachable(exc, self.url)
            log.warning("ES health_check failed: %s", exc)
            return False

    def storage_mode(self) -> str:
        return elasticsearch_storage_mode(self.url)

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return ElasticsearchCatalog.capabilities()

    @classmethod
    def ui_labels(cls) -> dict[str, str]:
        return ElasticsearchCatalog.ui_labels()

    @classmethod
    def index_summary(cls) -> dict[str, object]:
        return ElasticsearchCatalog.index_summary()

    def _label_stats(self, total_chunks: int) -> dict:
        return assemble_experiment_db_stats(
            None,
            database_provider=_PROVIDER,
            collection_name=self._index,
            cluster_host=cluster_host(self.url),
            index_names=[self._index],
            total_chunks=total_chunks,
            embedding_models=[],
            chunking_breakdown={},
            total_results=0,
            unique_queries=0,
            runs_with_data=0,
            run_breakdown=[],
        )

    def _mapping_or_none(self) -> dict[str, Any] | None:
        try:
            response = self.client().indices.get_mapping(index=self._index)
        except Exception as exc:
            if type(exc).__name__ == "NotFoundError":
                return None
            raise_if_unreachable(exc, self.url)
            raise
        return _body(response)

    def _count(self, query: dict[str, Any]) -> int:
        response = self.call(lambda: self.client().count(index=self._index, query=query))
        return int(_body(response).get("count") or 0)

    def _term_counts(self, field: str, experiment_id: str | None) -> dict[str, int]:
        query: dict[str, Any]
        if experiment_id is None:
            query = {"match_all": {}}
        else:
            query = {"term": {"experiment_id": experiment_id}}
        response = self.call(
            lambda: self.client().search(
                index=self._index,
                size=0,
                query=query,
                aggs={"buckets": {"terms": {"field": field, "size": 100}}},
            )
        )
        aggregations = _body(response).get("aggregations") or {}
        buckets = aggregations.get("buckets", {}).get("buckets") or []
        return {str(bucket["key"]): int(bucket["doc_count"]) for bucket in buckets}


def _bulk_operations(index: str, docs: list[dict]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for doc in docs:
        source = _chunk_source(doc)
        operations.append({"index": {"_index": index, "_id": source["chunk_id"]}})
        operations.append(source)
    return operations


def _chunk_source(doc: dict) -> dict[str, Any]:
    embedding = list(doc.get("embedding") or [])
    field = field_for_dims(len(embedding))
    return {
        "chunk_id": doc["chunk_id"],
        "experiment_id": doc["experiment_id"],
        "run_id": doc["run_id"],
        "text": doc.get("text", ""),
        "chunk_index": doc.get("index", 0),
        "embedding_model": doc.get("embedding_model", ""),
        "chunk_method": doc.get("chunk_method", ""),
        "chunk_size": doc.get("chunk_size", 0),
        "overlap": doc.get("overlap", 0),
        "padding": doc.get("padding", 0),
        field: embedding,
    }


def _reject_unsupported_models(config: ExperimentConfig) -> None:
    problems = [
        f"{model} ({get_dimensions(model)}-dim)"
        for model in config.embedding.models
        if get_dimensions(model) not in SUPPORTED_DIMS
    ]
    if not problems:
        return
    supported = ", ".join(str(dim) for dim in sorted(SUPPORTED_DIMS))
    raise SearchIndexMismatchError(
        "Dimension mismatch: "
        f"{', '.join(problems)} not in capabilities.supported_dims ({supported})."
    )


def _reject_quantized(mapping_response: dict[str, Any]) -> None:
    quantized = quantized_dense_fields(mapping_response)
    if quantized:
        raise SearchIndexMismatchError(
            f"{UNQUANTIZED_HNSW_REQUIRED} Quantized fields: {', '.join(quantized)}."
        )


class BulkIndexError(RuntimeError):
    """Raised when one or more documents fail during a bulk index operation."""


def _raise_on_bulk_errors(response: Any, expected: int) -> None:
    body = _body(response)
    if not body.get("errors"):
        return
    items = body.get("items") or []
    failures = []
    for item in items:
        action = item.get("index") or item.get("create") or {}
        error = action.get("error")
        if error:
            failures.append(f"{action.get('_id', '?')}: {error.get('reason', error)}")
    failed_count = len(failures)
    sample = "; ".join(failures[:5])
    raise BulkIndexError(
        f"{failed_count}/{expected} chunks failed to index. First errors: {sample}"
    )


def _body(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    body = getattr(response, "body", None)
    if isinstance(body, dict):
        return body
    return {}


def _missing_assessment(index: str) -> SearchIndexAssessment:
    required = frozenset({index})
    return SearchIndexAssessment(
        required=required,
        present_ready=frozenset(),
        present_building=frozenset(),
        missing=required,
        cluster_total=0,
        cluster_limit=0,
        available_slots=0,
        unknown_count=0,
        is_satisfied=False,
        failure_reason=f"Elasticsearch index {index!r} is missing.",
    )


def _ready_assessment(index: str) -> SearchIndexAssessment:
    required = frozenset({index})
    return SearchIndexAssessment(
        required=required,
        present_ready=required,
        present_building=frozenset(),
        missing=frozenset(),
        cluster_total=1,
        cluster_limit=0,
        available_slots=0,
        unknown_count=0,
        is_satisfied=True,
        failure_reason=None,
    )
