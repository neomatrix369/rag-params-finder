"""
Tests for server.db.elasticsearch retrieval and adapter behaviour.

Author: swami
Created: 2026-09-27
Scope: dense/sparse/hybrid filters, score scale, top_k, dims, refresh, delete,
       quantized preflight, missing client, unreachable cluster, stats label
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from server.core.retrieval.fusion import CANDIDATES_MULTIPLIER, cosine_to_unit_score, rrf_fuse
from server.db.elasticsearch.client import (
    ElasticsearchClientMissingError,
    ElasticsearchUnreachableError,
)
from server.db.elasticsearch.elasticsearch_vector_store import ElasticsearchVectorStore
from server.db.elasticsearch.mapping import (
    UNQUANTIZED_HNSW_REQUIRED,
    load_index_body,
    quantized_dense_fields,
)
from server.db.elasticsearch.retriever import search
from server.models.config import (
    ChunkingConfig,
    ChunkParams,
    EmbeddingConfig,
    ExecutionConfig,
    ExperimentConfig,
    RetrievalConfig,
    RetrieverConfig,
    normalize_stats_database_provider,
)
from server.models.enums import ChunkingMethod, RetrievalMethod, RetrieverType
from server.models.results import Chunk, SearchResult
from server.models.status import RunStatus


def _config(model: str = "all-MiniLM-L6-v2", provider: str = "local") -> ExperimentConfig:
    return ExperimentConfig(
        experiment_name="es-unit",
        data_paths=["."],
        queries_file="queries.json",
        database_provider="elasticsearch",
        embedding=EmbeddingConfig(provider=provider, models=[model]),  # type: ignore[arg-type]
        chunking=ChunkingConfig(
            methods=[ChunkingMethod.RECURSIVE],
            params=ChunkParams(chunk_sizes=[128], overlaps=[0], paddings=[0]),
        ),
        retrieval=RetrievalConfig(retrievers=[RetrieverConfig(type=RetrieverType.DENSE)]),
        execution=ExecutionConfig(),
    )


def _hit(
    chunk_id: str,
    score: float,
    *,
    model: str = "all-MiniLM-L6-v2",
    run_id: str = "run-a",
) -> dict:
    return {
        "_id": chunk_id,
        "_score": score,
        "_source": {
            "chunk_id": chunk_id,
            "text": chunk_id,
            "chunk_index": 0,
            "embedding_model": model,
            "chunk_method": "recursive",
            "experiment_id": "exp-1",
            "run_id": run_id,
        },
    }


class _FakeElasticsearch:
    """Records search/bulk/delete calls and returns scripted responses."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        *,
        error: BaseException | None = None,
    ) -> None:
        self.response = response or {"hits": {"hits": []}}
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.indices = SimpleNamespace(
            get_mapping=self._get_mapping,
            create=self._create,
            exists=lambda **_kwargs: True,
        )
        self._mapping: dict[str, Any] | None = {"mappings": load_index_body()["mappings"]}

    def search(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("search", kwargs))
        if self.error:
            raise self.error
        return self.response

    def bulk(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("bulk", kwargs))
        return {"errors": False}

    def delete_by_query(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("delete_by_query", kwargs))
        return {"deleted": 2}

    def count(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("count", kwargs))
        return {"count": 2}

    def ping(self) -> bool:
        self.calls.append(("ping", {}))
        if self.error:
            raise self.error
        return True

    def _get_mapping(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_mapping", kwargs))
        if self._mapping is None:
            raise type("NotFoundError", (Exception,), {})("missing")
        return self._mapping

    def _create(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("create", kwargs))
        self._mapping = {"mappings": kwargs.get("mappings")}
        return {"acknowledged": True}


def _store(client: _FakeElasticsearch) -> ElasticsearchVectorStore:
    return ElasticsearchVectorStore(client=client)


class TestElasticsearchSearchShould:
    def test_given_cosine_score_when_dense_search_runs_then_score_is_unchanged(self) -> None:
        """
        Scenario: Dense score is on the shared (1+cos)/2 scale.
        Slice: 50

        Given Elasticsearch already returned (1+cosine)/2 as _score,
        When dense search maps the hit,
        Then the adapter returns that score with no second conversion.
        """
        ### Given
        cosine = 1.0
        engine_score = cosine_to_unit_score(cosine)
        client = _FakeElasticsearch({"hits": {"hits": [_hit("c1", engine_score)]}})

        ### When
        actual = search(
            client,
            index="rpf-chunks",
            method=RetrievalMethod.DENSE,
            query_text="q",
            experiment_id="exp-1",
            embedding_model="all-MiniLM-L6-v2",
            run_id="run-a",
            top_k=1,
            query_embedding=[0.0] * 384,
        )

        ### Then
        assert actual[0].dense_score == engine_score, "do not convert cosine _score again"
        knn = client.calls[0][1]["knn"]
        assert knn["num_candidates"] == 1 * CANDIDATES_MULTIPLIER
        model_filter = {"term": {"embedding_model": "all-MiniLM-L6-v2"}}
        assert knn["filter"]["bool"]["filter"][1] == model_filter

    def test_given_two_models_when_filtered_then_query_names_only_model_a(self) -> None:
        """
        Scenario: embedding_model isolation.
        Slice: 50

        Given a dense query for model A,
        When search builds the knn filter,
        Then embedding_model, experiment_id, and run_id are all pre-filters.
        """
        ### Given
        client = _FakeElasticsearch()

        ### When
        search(
            client,
            index="rpf-chunks",
            method=RetrievalMethod.DENSE,
            query_text="q",
            experiment_id="exp-1",
            embedding_model="model-a",
            run_id="run-a",
            top_k=2,
            query_embedding=[0.1] * 384,
        )

        ### Then
        filters = client.calls[0][1]["knn"]["filter"]["bool"]["filter"]
        assert {"term": {"embedding_model": "model-a"}} in filters
        assert {"term": {"experiment_id": "exp-1"}} in filters
        assert {"term": {"run_id": "run-a"}} in filters

    def test_given_more_hits_than_top_k_when_search_runs_then_size_is_top_k(self) -> None:
        """
        Scenario: top_k bound and score ordering.
        Slice: 50

        Given the engine returns hits already ordered by score,
        When search maps them,
        Then the request size is top_k and ranks follow that order.
        """
        ### Given
        client = _FakeElasticsearch({"hits": {"hits": [_hit("high", 0.9), _hit("low", 0.1)]}})

        ### When
        actual = search(
            client,
            index="rpf-chunks",
            method=RetrievalMethod.SPARSE,
            query_text="grant",
            experiment_id="exp-1",
            embedding_model="model-a",
            run_id="run-a",
            top_k=2,
            query_embedding=None,
        )

        ### Then
        assert client.calls[0][1]["size"] == 2
        assert [hit.chunk.id for hit in actual] == ["high", "low"]
        assert actual[0].dense_score > actual[1].dense_score

    def test_given_dense_and_sparse_hits_when_hybrid_runs_then_rrf_matches_helper(self) -> None:
        """
        Scenario: Hybrid RRF parity with Mongo on a fixed fixture.
        Slice: 50

        Given one shared chunk and one sparse-only chunk,
        When hybrid search fuses the two engine responses,
        Then the ranking matches rrf_fuse.
        """
        ### Given
        dense_hit = _hit("shared", 0.99)
        sparse_hits = [_hit("shared", 0.4), _hit("only-sparse", 0.2)]
        client = _FakeElasticsearch()
        responses = [{"hits": {"hits": [dense_hit]}}, {"hits": {"hits": sparse_hits}}]

        def _search(**_kwargs: Any) -> dict[str, Any]:
            client.calls.append(("search", _kwargs))
            return responses.pop(0)

        client.search = _search  # type: ignore[method-assign]

        ### When
        actual = search(
            client,
            index="rpf-chunks",
            method=RetrievalMethod.HYBRID,
            query_text="grant",
            experiment_id="exp-1",
            embedding_model="model-a",
            run_id="run-a",
            top_k=2,
            query_embedding=[0.2] * 384,
        )
        dense_results = [
            SearchResult(
                chunk=Chunk(
                    id="shared",
                    text="shared",
                    index=0,
                    embedding_model="model-a",
                    chunk_method="recursive",
                ),
                dense_score=0.99,
                retrieval_method="dense",
                rank=1,
            )
        ]
        sparse_results = [
            SearchResult(
                chunk=Chunk(
                    id="shared",
                    text="shared",
                    index=0,
                    embedding_model="model-a",
                    chunk_method="recursive",
                ),
                dense_score=0.4,
                retrieval_method="sparse",
                rank=1,
            ),
            SearchResult(
                chunk=Chunk(
                    id="only-sparse",
                    text="only-sparse",
                    index=0,
                    embedding_model="model-a",
                    chunk_method="recursive",
                ),
                dense_score=0.2,
                retrieval_method="sparse",
                rank=2,
            ),
        ]
        expected_ids = [hit.chunk.id for hit in rrf_fuse(dense_results, sparse_results, top_k=2)]

        ### Then
        assert [hit.chunk.id for hit in actual] == expected_ids

    def test_given_non_positive_top_k_when_search_runs_then_no_call(self) -> None:
        """
        Scenario: Invalid top_k is rejected.
        Slice: 50

        Given top_k is 0,
        When search runs,
        Then it fails before any Elasticsearch call.
        """
        ### Given
        client = _FakeElasticsearch()

        ### When / Then
        with pytest.raises(ValueError, match="top_k"):
            search(
                client,
                index="rpf-chunks",
                method=RetrievalMethod.DENSE,
                query_text="q",
                experiment_id="exp-1",
                embedding_model="model-a",
                run_id="run-a",
                top_k=0,
                query_embedding=[0.0] * 384,
            )
        assert client.calls == []

    def test_given_unsupported_width_when_dense_search_runs_then_dims_rejected(self) -> None:
        """
        Scenario: Dimension mismatch is rejected.
        Slice: 50

        Given a 3-dim query vector,
        When dense search runs,
        Then it fails naming supported_dims and does not call Elasticsearch.
        """
        ### Given
        client = _FakeElasticsearch()

        ### When / Then
        with pytest.raises(ValueError, match="supported_dims"):
            search(
                client,
                index="rpf-chunks",
                method=RetrievalMethod.DENSE,
                query_text="q",
                experiment_id="exp-1",
                embedding_model="model-a",
                run_id="run-a",
                top_k=1,
                query_embedding=[0.0, 0.0, 0.0],
            )
        assert client.calls == []


class TestElasticsearchStoreShould:
    def test_given_chunks_when_inserted_then_refresh_wait_for(self) -> None:
        """
        Scenario: Insert-then-immediately-search returns hits (refresh regression).
        Slice: 50

        Given a chunk document,
        When upsert returns,
        Then the bulk call uses refresh=wait_for.
        """
        ### Given
        client = _FakeElasticsearch()
        store = _store(client)
        docs = [
            {
                "chunk_id": "c1",
                "experiment_id": "exp-1",
                "run_id": "run-a",
                "text": "pell grant",
                "index": 0,
                "embedding": [0.1] * 384,
                "embedding_model": "all-MiniLM-L6-v2",
                "chunk_method": "recursive",
            }
        ]

        ### When
        store.insert_chunks(docs)

        ### Then
        kind, kwargs = client.calls[0]
        assert kind == "bulk"
        assert kwargs["refresh"] == "wait_for"
        assert kwargs["operations"][1]["embedding_384"][0] == 0.1

    def test_given_existing_mapping_when_ensure_indexes_again_then_no_create(self) -> None:
        """
        Scenario: ensure_indexes is idempotent.
        Slice: 50

        Given the index mapping is already present and unquantized,
        When ensure_indexes runs,
        Then create is not called.
        """
        ### Given
        client = _FakeElasticsearch()
        store = _store(client)

        ### When
        store.ensure_indexes()

        ### Then
        assert "create" not in [name for name, _kwargs in client.calls]

    def test_given_quantized_mapping_when_preflight_runs_then_rejected(self) -> None:
        """
        Scenario: Quantized mapping is rejected at preflight.
        Slice: 50

        Given a dense_vector field indexed as bbq_hnsw,
        When plan_indexes runs,
        Then it fails with the unquantized HNSW remediation.
        """
        ### Given
        client = _FakeElasticsearch()
        body = load_index_body()
        body["mappings"]["properties"]["embedding_384"]["index_options"]["type"] = "bbq_hnsw"
        client._mapping = body
        store = _store(client)

        ### When / Then
        with pytest.raises(Exception, match="unquantized HNSW required") as excinfo:
            store.plan_indexes(_config())
        assert UNQUANTIZED_HNSW_REQUIRED.split(":")[0] in str(excinfo.value)

    @pytest.mark.parametrize("index_type", ["bbq_hnsw", "int8_hnsw"])
    def test_given_quantized_type_when_detected_then_field_is_listed(self, index_type: str) -> None:
        """
        Scenario: Quantized mapping is rejected at preflight.
        Slice: 50

        Given index_options.type is a quantized HNSW variant,
        When the mapping is inspected,
        Then that dense_vector field is reported.
        """
        ### Given
        mapping = {
            "properties": {
                "embedding_384": {
                    "type": "dense_vector",
                    "index_options": {"type": index_type},
                }
            }
        }

        ### When
        actual = quantized_dense_fields(mapping)

        ### Then
        assert actual == ["embedding_384"]

    def test_given_two_experiments_when_delete_one_then_query_is_scoped(self) -> None:
        """
        Scenario: delete_experiment removes only that experiment's chunks.
        Slice: 50

        Given a delete for one experiment id,
        When delete_chunks_for_experiment runs,
        Then the delete-by-query filters that id and returns the deleted count.
        """
        ### Given
        client = _FakeElasticsearch()
        store = _store(client)

        ### When
        actual_deleted = store.delete_chunks_for_experiment("exp-1")

        ### Then
        assert actual_deleted == 2
        assert client.calls[0][1]["query"] == {"term": {"experiment_id": "exp-1"}}
        assert client.calls[0][1]["refresh"] is True

    def test_given_splade_model_when_preflight_runs_then_dims_rejected(self) -> None:
        """
        Scenario: Dimension mismatch is rejected.
        Slice: 50

        Given a config whose model is 30522-dim SPLADE,
        When plan_indexes runs,
        Then it fails naming capabilities.supported_dims before reading a mapping.
        """
        ### Given
        client = _FakeElasticsearch()
        store = _store(client)

        ### When / Then
        with pytest.raises(Exception, match="supported_dims"):
            store.plan_indexes(_config("splade-v3", "sie"))
        assert client.calls == []

    def test_given_connection_error_when_search_runs_then_clear_error(self) -> None:
        """
        Scenario: Elasticsearch unreachable surfaces a clear error.
        Slice: 50

        Given the client raises ConnectionError,
        When search runs through the store,
        Then ElasticsearchUnreachableError is raised, not an empty list.
        """
        ### Given
        client = _FakeElasticsearch(error=ConnectionError("timed out"))
        store = _store(client)

        ### When / Then
        with pytest.raises(ElasticsearchUnreachableError, match="unreachable"):
            store.retriever().search(
                RetrievalMethod.SPARSE,
                "q",
                "exp-1",
                "model-a",
                "run-a",
                1,
                None,
            )

    def test_given_chunks_when_stats_read_then_label_is_elasticsearch(self) -> None:
        """
        Scenario: A vector-only store's label appears on db-stats.
        Slice: 50 — CF-49B-2

        Given indexed chunks,
        When experiment db-stats are read,
        Then database_provider is elasticsearch.
        """
        ### Given
        client = _FakeElasticsearch()

        def _search(**kwargs: Any) -> dict[str, Any]:
            client.calls.append(("search", kwargs))
            return {
                "aggregations": {
                    "buckets": {"buckets": [{"key": "all-MiniLM-L6-v2", "doc_count": 2}]}
                }
            }

        client.search = _search  # type: ignore[method-assign]
        store = _store(client)

        ### When
        actual = store.get_experiment_db_stats("exp-1")

        ### Then
        assert actual["database_provider"] == "elasticsearch"
        assert actual["total_chunks"] == 2

    def test_given_no_client_extra_when_store_constructed_then_install_guidance(self) -> None:
        """
        Scenario: ES client missing raises install guidance.
        Slice: 50

        Given the elasticsearch module cannot be imported,
        When the adapter is constructed without an injected client,
        Then the error names the optional extra.
        """
        ### Given
        real_import = __import__

        def _blocked(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "elasticsearch":
                raise ImportError("blocked for test")
            return real_import(name, *args, **kwargs)

        ### When / Then
        with pytest.raises(ElasticsearchClientMissingError, match=r"\[elasticsearch\]"):
            with pytest.MonkeyPatch.context() as patcher:
                patcher.setattr("builtins.__import__", _blocked)
                sys.modules.pop("elasticsearch", None)
                ElasticsearchVectorStore()


class TestElasticsearchLabelShould:
    def test_given_elasticsearch_provider_when_models_validate_then_label_survives(self) -> None:
        """
        Scenario: A vector-only store's label appears on every run surface.
        Slice: 50 — CF-49B-2

        Given database_provider elasticsearch,
        When ExperimentConfig, RunStatus, and stats normalisation run,
        Then the label stays elasticsearch.
        """
        ### Given
        ### When
        config = _config()
        status = RunStatus(
            run_id="run-a",
            experiment_id="exp-1",
            phase="queued",
            database_provider="elasticsearch",
            embedding_provider="local",
            embedding_model="all-MiniLM-L6-v2",
            chunking_method="fixed",
            chunk_size=128,
            overlap=0,
            retrieval_method="dense",
            retrieval_provider="local",
        )
        actual_stats = normalize_stats_database_provider("elasticsearch", fallback="mongodb")

        ### Then
        assert config.database_provider == "elasticsearch"
        assert status.database_provider == "elasticsearch"
        assert actual_stats == "elasticsearch", "stats must not fall back to mongodb"


def test_shipped_mapping_is_unquantized_hnsw() -> None:
    """
    Scenario: ensure_indexes is idempotent — shipped mapping is the HNSW contract.
    Slice: 50

    Given index_mapping.json,
    When it is loaded,
    Then both dense fields are explicit unquantized HNSW.
    """
    ### Given / When
    properties = load_index_body()["mappings"]["properties"]

    ### Then
    for field in ("embedding_384", "embedding_1024"):
        options = properties[field]["index_options"]
        assert options["type"] == "hnsw", field
        assert options["m"] == 16
        assert options["ef_construction"] == 100
        assert properties[field]["similarity"] == "cosine"
    assert properties["text"]["analyzer"] == "english"
    assert quantized_dense_fields(load_index_body()) == []


def test_capabilities_declare_vector_only_hnsw() -> None:
    """
    Scenario: capabilities() matches the data-eng contract.
    Slice: 50

    Given the Elasticsearch adapter,
    When capabilities() is read,
    Then it is cosine HNSW, dims 384 and 1024, and cannot host run state.
    """
    ### Given / When
    actual = ElasticsearchVectorStore.capabilities()

    ### Then
    assert actual.can_host_run_state is False
    assert actual.supported_embedding_dims == frozenset({384, 1024})
    assert actual.similarity_metrics == frozenset({"cosine"})
    assert actual.index_types == frozenset({"hnsw"})
    assert RetrievalMethod.HYBRID in actual.retrieval_methods
