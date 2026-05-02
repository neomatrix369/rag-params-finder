import threading
import time
import uuid
from datetime import datetime

from server.core.chunkers import chunk_text
from server.core.embedder import embed_documents, embed_query
from server.core.data_loader import load_all_files
from server.core.query_loader import load_queries
from server.core.reranker import rerank_results
from server.core.retriever import dense_search
from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.config import ExperimentConfig, RunParams, expand_sweep
from server.models.enums import Phase
from server.models.results import QueryResult
from server.models.status import RunStatus
from server.utils.logger import get_logger

logger = get_logger(__name__)

_cancel_events: dict[str, threading.Event] = {}


class ExperimentCancelled(Exception):
    pass


def request_cancel(experiment_id: str) -> bool:
    """Signal a running experiment to stop. Returns True if it was in-flight."""
    event = _cancel_events.get(experiment_id)
    if event is None:
        return False
    event.set()
    return True


def _check_cancelled(experiment_id: str) -> None:
    """Raise ExperimentCancelled if this experiment has been cancelled."""
    event = _cancel_events.get(experiment_id)
    if event and event.is_set():
        raise ExperimentCancelled(f"Experiment {experiment_id} was cancelled")


def run_sweep(experiment_id: str, config: ExperimentConfig) -> dict:
    """Execute all sweep runs for a pre-created experiment.

    Declared as a sync function so FastAPI's BackgroundTasks runs it in a
    threadpool instead of on the event loop (all callees are blocking I/O).
    """
    _cancel_events[experiment_id] = threading.Event()

    try:
        return _run_sweep_inner(experiment_id, config)
    finally:
        _cancel_events.pop(experiment_id, None)


def _run_sweep_inner(experiment_id: str, config: ExperimentConfig) -> dict:
    runs = expand_sweep(config)
    run_ids: list[str] = []
    logger.info(f"Experiment {experiment_id}: {len(runs)} runs to execute")

    failed = 0
    cancelled = False
    for params in runs:
        try:
            _check_cancelled(experiment_id)
        except ExperimentCancelled:
            cancelled = True
            logger.info(f"Experiment {experiment_id} cancelled before run {len(run_ids) + 1}")
            break

        run_id = str(uuid.uuid4())
        run_ids.append(run_id)
        try:
            _run_single(experiment_id, run_id, params)
        except ExperimentCancelled:
            cancelled = True
            logger.info(f"Experiment {experiment_id} cancelled during run {run_id}")
            break
        except Exception as e:
            failed += 1
            logger.error(f"Run {run_id} failed: {e}")
            if config.execution.on_error == "stop":
                break

    if cancelled:
        final_status = "cancelled"
    elif failed == 0:
        final_status = "complete"
    elif failed < len(runs):
        final_status = "partial"
    else:
        final_status = "failed"

    completed_at = datetime.utcnow()
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {"$set": {
            "status": final_status,
            "run_count": len(runs),
            "failed_count": failed,
            "completed_at": completed_at,
        }},
    )
    logger.info(f"Experiment {experiment_id} finished: {final_status}")

    return {"experiment_id": experiment_id, "run_ids": run_ids, "status": final_status}


def _run_single(experiment_id: str, run_id: str, params: RunParams) -> None:
    """Execute one run of the pipeline for a single parameter combination."""
    logger.info(
        f"Run {run_id}: {params.embedding_model} / {params.chunking_method.value} "
        f"/ {params.chunk_size}+{params.overlap} / {params.retrieval_method.value}"
    )

    run_status = RunStatus(
        run_id=run_id,
        experiment_id=experiment_id,
        phase=Phase.QUEUED,
        database_provider=params.database_provider,
        embedding_provider=params.embedding_provider,
        embedding_model=params.embedding_model,
        chunking_method=params.chunking_method,
        chunk_size=params.chunk_size,
        overlap=params.overlap,
        retrieval_method=params.retrieval_method,
        rerank_provider=params.rerank_provider,
        rerank_model=params.rerank_model,
    )
    get_collection(RUN_STATUS_COLLECTION).insert_one(run_status.model_dump())

    try:
        _check_cancelled(experiment_id)
        _update_phase(run_id, Phase.PARSING)
        text = load_all_files(params.data_paths)
        logger.info(f"Run {run_id}: parsed {len(text)} chars from {len(params.data_paths)} path(s)")

        _check_cancelled(experiment_id)
        _update_phase(run_id, Phase.CHUNKING)
        chunks = chunk_text(text, params.chunking_method, params.chunk_size, params.overlap)
        logger.info(f"Run {run_id}: chunked into {len(chunks)} chunks")

        _check_cancelled(experiment_id)
        _update_phase(run_id, Phase.EMBEDDING)
        embeddings = embed_documents(chunks, params.embedding_model, params.embedding_provider)
        logger.info(f"Run {run_id}: generated {len(embeddings)} embeddings")

        _check_cancelled(experiment_id)
        _update_phase(run_id, Phase.STORING)
        chunk_docs = [
            {
                "chunk_id": f"{run_id}_{i}",
                "experiment_id": experiment_id,
                "run_id": run_id,
                "text": chunk,
                "index": i,
                "embedding": emb,
                "embedding_model": params.embedding_model,
                "chunk_method": params.chunking_method.value,
                "chunk_size": params.chunk_size,
                "overlap": params.overlap,
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        get_collection(CHUNKS_COLLECTION).insert_many(chunk_docs)
        logger.info(f"Stored {len(chunk_docs)} chunks")

        _check_cancelled(experiment_id)
        _update_phase(run_id, Phase.QUERYING)
        queries = load_queries(params.queries_file)
        logger.info(f"Run {run_id}: querying with {len(queries)} queries")

        for i, q in enumerate(queries, start=1):
            _check_cancelled(experiment_id)
            query_id = str(uuid.uuid4())
            logger.debug(
                f"Run {run_id} query {i}/{len(queries)}: "
                f"persona={q.persona_id}, text='{q.text[:60]}...'"
            )
            query_embedding = embed_query(q.text, params.embedding_model, params.embedding_provider)
            search_results = dense_search(
                query_embedding,
                experiment_id,
                params.embedding_model,
                top_k=params.top_k_initial,
            )
            logger.debug(f"Run {run_id} query {i}: dense search returned {len(search_results)} results")

            if params.rerank_model:
                _update_phase(run_id, Phase.RERANKING)
                search_results = rerank_results(
                    query=q.text,
                    search_results=search_results,
                    model=params.rerank_model,
                    top_k=params.top_k_final,
                    provider=params.rerank_provider,
                )
                logger.debug(f"Run {run_id} query {i}: reranked to {len(search_results)} results")
            else:
                search_results = search_results[: params.top_k_final]

            query_result = QueryResult(
                query_id=query_id,
                experiment_id=experiment_id,
                run_id=run_id,
                query_text=q.text,
                persona_id=q.persona_id,
                focus=q.focus,
                results=search_results,
                top_k=len(search_results),
            )
            get_collection(RESULTS_COLLECTION).insert_one(query_result.model_dump())

        logger.info(f"Run {run_id}: processed {len(queries)} queries")

        _update_phase(run_id, Phase.COMPLETE)

    except ExperimentCancelled:
        logger.info(f"Run {run_id} interrupted by cancellation")
        _update_phase(run_id, Phase.INTERRUPTED, error_message="Cancelled by user")
        raise
    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")
        _update_phase(run_id, Phase.FAILED, error_message=str(e))
        raise


_run_start_times: dict[str, float] = {}


def _update_phase(run_id: str, phase: Phase, error_message: str | None = None) -> None:
    """Update run_status phase and elapsed_ms in MongoDB."""
    now = time.monotonic()
    if run_id not in _run_start_times:
        _run_start_times[run_id] = now

    elapsed_ms = int((now - _run_start_times[run_id]) * 1000)
    logger.info(f"Run {run_id} → {phase.value} ({elapsed_ms}ms)")

    update: dict = {
        "phase": phase.value,
        "updated_at": datetime.utcnow(),
        "elapsed_ms": elapsed_ms,
        "error_message": error_message,
    }
    get_collection(RUN_STATUS_COLLECTION).update_one(
        {"run_id": run_id}, {"$set": update}
    )

    if phase in (Phase.COMPLETE, Phase.FAILED, Phase.INTERRUPTED):
        _run_start_times.pop(run_id, None)
