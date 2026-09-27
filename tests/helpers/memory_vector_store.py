"""In-memory ``VectorStore`` double — Slice 49B split-store test infrastructure.

Author: Claude (Stream 1)
Created: 2026-09-27
Scope: Implements the 49A ``VectorStore`` Protocol (``server/db/ports/vector_store.py``)
       entirely in Python-process memory, so acceptance tests can prove the
       split-store data path (chunks routed to the vector store, never the
       run-state store) without Elasticsearch/Redis existing yet (Slice 50/53).

Registered under the provider name ``"memory"`` for tests only — production
code never references this module. A test registers it into
``server.db.ports.registry._VECTOR_STORE_REGISTRY`` (a plain dict) via
monkeypatch, and constructs settings with ``VECTOR_STORE_BACKEND=memory``
with the 49A equality-lock validator lifted for that one test file. See
``tests/server/test_split_store_e2e.py`` for the wiring.

Honours (per SLICE-49B "Test infrastructure"):
  - the three mandatory filters: experiment_id, embedding_model, run_id
    (the same filter triple ``retriever_mongo.dense_search`` /
    ``retriever_postgres._dense_query`` apply — see those modules' ``$eq``
    filter / ``WHERE`` clause);
  - top_k;
  - the ``(1 + cosine_similarity) / 2`` dense score scale (matches Atlas
    ``$vectorSearch`` / pgvector's documented scaling — see
    ``retriever_postgres._dense_query`` docstring);
  - delete counts (``delete_chunks_for_experiment`` returns the number removed);
  - a simple term-overlap sparse score, and an RRF-style hybrid fusion of the
    dense/sparse rankings (mirrors the RRF fusion in both real retrievers,
    without pulling their SQL/aggregation-pipeline machinery into a test double).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from server.core.guards.search_index_plan import SearchIndexAssessment, preflight_not_applicable
from server.db.ports.retriever_backend import RetrieverBackend
from server.db.ports.vector_store import VectorCapabilities
from server.models.config import ExperimentConfig
from server.models.enums import RetrievalMethod
from server.models.results import Chunk, SearchResult

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_CAPABILITIES = VectorCapabilities(
    retrieval_methods=frozenset(
        {RetrievalMethod.DENSE, RetrievalMethod.SPARSE, RetrievalMethod.HYBRID}
    ),
    similarity_metrics=frozenset({"cosine"}),
    index_types=frozenset({"memory"}),
    supported_embedding_dims=frozenset(),  # bag-of-words vectors vary in width — no fixed set
    supports_metadata_filters=True,
    can_host_run_state=False,
    labels=frozenset({"memory"}),
)

_RRF_K = 60  # matches retriever_mongo._RRF_K / retriever_postgres._DEFAULT_RRF_K


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _sparse_overlap_score(query_text: str, chunk_text: str) -> float:
    """Term-overlap score — count of query tokens present in the chunk, divided
    by the query token count. Simple stand-in for BM25/ts_rank_cd."""
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return 0.0
    chunk_tokens = set(_tokenize(chunk_text))
    overlap = sum(1 for tok in query_tokens if tok in chunk_tokens)
    return overlap / len(query_tokens)


def _matches_filters(doc: dict, *, experiment_id: str, embedding_model: str, run_id: str) -> bool:
    """The three mandatory filters every real retriever applies (never optional)."""
    return (
        doc.get("experiment_id") == experiment_id
        and doc.get("embedding_model") == embedding_model
        and doc.get("run_id") == run_id
    )


def _to_search_result(
    doc: dict, *, score: float, method: RetrievalMethod, rank: int
) -> SearchResult:
    return SearchResult(
        chunk=Chunk(
            id=doc["chunk_id"],
            text=doc["text"],
            index=doc["index"],
            embedding_model=doc["embedding_model"],
            chunk_method=doc["chunk_method"],
        ),
        dense_score=score,
        rerank_score=None,
        retrieval_method=method.value,
        rank=rank,
    )


@dataclass
class MemoryRetrieverBackend:
    """RetrieverBackend over an in-memory chunk list — see ``MemoryVectorStore``."""

    _store: MemoryVectorStore

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
        candidates = [
            doc
            for doc in self._store.chunks
            if _matches_filters(
                doc, experiment_id=experiment_id, embedding_model=embedding_model, run_id=run_id
            )
        ]
        if not candidates:
            return []

        if method == RetrievalMethod.DENSE:
            scored = [
                (doc, (1.0 + _cosine(query_embedding or [], doc["embedding"])) / 2.0)
                for doc in candidates
            ]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            top = scored[:top_k]
            return [
                _to_search_result(doc, score=score, method=method, rank=i + 1)
                for i, (doc, score) in enumerate(top)
            ]

        if method == RetrievalMethod.SPARSE:
            scored = [(doc, _sparse_overlap_score(query_text, doc["text"])) for doc in candidates]
            scored.sort(key=lambda pair: pair[1], reverse=True)
            top = scored[:top_k]
            return [
                _to_search_result(doc, score=score, method=method, rank=i + 1)
                for i, (doc, score) in enumerate(top)
            ]

        # HYBRID — Reciprocal Rank Fusion of the dense and sparse rankings,
        # mirroring both real retrievers' RRF constant (_RRF_K = 60).
        dense_ranked = sorted(
            candidates,
            key=lambda doc: _cosine(query_embedding or [], doc["embedding"]),
            reverse=True,
        )
        sparse_ranked = sorted(
            candidates,
            key=lambda doc: _sparse_overlap_score(query_text, doc["text"]),
            reverse=True,
        )
        rrf_scores: dict[str, float] = {}
        for rank, doc in enumerate(dense_ranked, start=1):
            rrf_scores[doc["chunk_id"]] = rrf_scores.get(doc["chunk_id"], 0.0) + 1.0 / (
                rank + _RRF_K
            )
        for rank, doc in enumerate(sparse_ranked, start=1):
            rrf_scores[doc["chunk_id"]] = rrf_scores.get(doc["chunk_id"], 0.0) + 1.0 / (
                rank + _RRF_K
            )
        by_id = {doc["chunk_id"]: doc for doc in candidates}
        ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]
        return [
            _to_search_result(by_id[cid], score=rrf_scores[cid], method=method, rank=i + 1)
            for i, cid in enumerate(ranked_ids)
        ]


@dataclass
class MemoryVectorStore:
    """VectorStore Protocol implementation backed by a plain Python list.

    ``can_host_run_state`` is False — this double exists only to prove the
    chunk data path; it is never a candidate run-state store under pairing
    rule (ii) (SLICE-49B).
    """

    chunks: list[dict] = field(default_factory=list)

    # ── Chunks ────────────────────────────────────────────────────────────────

    def insert_chunks(self, docs: list[dict]) -> None:
        self.chunks.extend(docs)

    def delete_chunks_for_experiment(self, experiment_id: str) -> int:
        before = len(self.chunks)
        self.chunks = [doc for doc in self.chunks if doc.get("experiment_id") != experiment_id]
        return before - len(self.chunks)

    def get_experiment_db_stats(self, experiment_id: str) -> dict:
        experiment_chunks = [
            doc for doc in self.chunks if doc.get("experiment_id") == experiment_id
        ]
        embedding_models = sorted({doc["embedding_model"] for doc in experiment_chunks})
        chunking_methods = sorted({doc["chunk_method"] for doc in experiment_chunks})
        chunking_breakdown: dict[str, int] = {}
        for doc in experiment_chunks:
            chunking_breakdown[doc["chunk_method"]] = (
                chunking_breakdown.get(doc["chunk_method"], 0) + 1
            )
        run_ids = {doc["run_id"] for doc in experiment_chunks}
        total = len(experiment_chunks)
        return {
            "database_provider": "memory",
            "collection_name": "memory-chunks",
            "cluster_host": "in-process",
            "total_chunks": total,
            "unique_documents": len({doc.get("index") for doc in experiment_chunks}),
            "embedding_models": embedding_models,
            "embedding_dimensions": sorted({len(doc["embedding"]) for doc in experiment_chunks}),
            "index_names": ["memory-index"],
            "retrieval_methods": ["dense", "sparse", "hybrid"],
            "chunking_methods": chunking_methods,
            "chunking_breakdown": chunking_breakdown,
            "estimated_storage_mb": 0.0,
            "estimated_embedding_mb": 0.0,
            "estimated_metadata_mb": 0.0,
            "runs_with_data": len(run_ids),
            "avg_chunks_per_run": (total / len(run_ids)) if run_ids else 0.0,
            "total_results": 0,
            "unique_queries": 0,
            "run_breakdown": {},
        }

    def get_vector_db_stats_grouped(self) -> dict:
        by_experiment: dict[str, int] = {}
        for doc in self.chunks:
            exp_id = doc.get("experiment_id", "")
            by_experiment[exp_id] = by_experiment.get(exp_id, 0) + 1
        return {
            "groups": [{"database_provider": "memory", "total_chunks": sum(by_experiment.values())}]
        }

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retriever(self) -> RetrieverBackend:
        return MemoryRetrieverBackend(self)

    # ── Index planning ───────────────────────────────────────────────────────

    def plan_indexes(self, config: ExperimentConfig) -> SearchIndexAssessment:
        del config  # the memory double has no index/catalog concept to negotiate
        return preflight_not_applicable()

    def ensure_indexes(self) -> None:
        return None

    # ── Health + identity ─────────────────────────────────────────────────────

    def health_check(self) -> bool:
        return True

    def storage_mode(self) -> str:
        return "memory-test"

    @classmethod
    def capabilities(cls) -> VectorCapabilities:
        return _CAPABILITIES
