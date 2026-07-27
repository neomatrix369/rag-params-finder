"""Retriever search helpers used by a single pipeline run."""

from __future__ import annotations

from server.core.rerank.reranker import rerank_results
from server.db.ports.store_factory import get_retriever_backend
from server.models.config import RetrieverConfig, RunParams
from server.models.enums import Phase, RetrievalMethod, RetrieverType
from server.models.results import SearchResult
from server.utils.logger import get_logger

logger = get_logger(__name__)

_TRADITIONAL_RETRIEVER_TYPES = {
    RetrieverType.DENSE,
    RetrieverType.SPARSE,
    RetrieverType.HYBRID,
}
_RERANKER_RETRIEVER_TYPES = {RetrieverType.RERANKER, RetrieverType.CROSS_ENCODER}


def _update_phase_proxy(run_id: str, phase: Phase, error_message: str | None = None) -> None:
    """Delegate to orchestrator so phase patches on that module still apply."""
    from server.core.pipeline import orchestrator as orch

    orch._update_phase(run_id, phase, error_message=error_message)


def _primary_retriever(params: RunParams) -> RetrieverConfig:
    if not params.retrievers:
        raise ValueError(f"Run {params} has no retriever configured")
    return params.retrievers[0]


def _search_traditional_retriever(
    retriever_cfg: RetrieverConfig,
    *,
    run_id: str,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    embed_query_fn,  # Callable[[str, str], list[float]] from embedder_factory
    top_k: int,
    query_embedding: list[float] | None,
) -> tuple[list[SearchResult], list[float] | None]:
    needs_embedding = retriever_cfg.type in {RetrieverType.DENSE, RetrieverType.HYBRID}
    if needs_embedding and query_embedding is None:
        query_embedding = embed_query_fn(query_text, embedding_model)

    results = get_retriever_backend().search(
        method=RetrievalMethod(retriever_cfg.type.value),
        query_text=query_text,
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        run_id=run_id,
        top_k=top_k,
        query_embedding=query_embedding,
    )
    return results, query_embedding


def _search_reranker_retriever(
    retriever_cfg: RetrieverConfig,
    *,
    run_id: str,
    query_text: str,
    experiment_id: str,
    embedding_model: str,
    embed_query_fn,  # Callable[[str, str], list[float]] from embedder_factory
    top_k_initial: int,
    top_k_final: int,
) -> list[SearchResult]:
    if not retriever_cfg.provider or not retriever_cfg.model:
        raise ValueError(f"Reranker {retriever_cfg.type} missing provider or model")

    candidates, _ = _search_traditional_retriever(
        RetrieverConfig(type=RetrieverType.DENSE),
        run_id=run_id,
        query_text=query_text,
        experiment_id=experiment_id,
        embedding_model=embedding_model,
        embed_query_fn=embed_query_fn,
        top_k=top_k_initial,
        query_embedding=None,
    )
    if not candidates:
        logger.warning(
            "reranker has no dense candidates — run %s query %r",
            run_id,
            query_text[:60],
        )
        return []

    _update_phase_proxy(run_id, Phase.RERANKING)
    return rerank_results(
        query=query_text,
        search_results=candidates,
        model=retriever_cfg.model,
        top_k=top_k_final,
        provider=retriever_cfg.provider,
    )
