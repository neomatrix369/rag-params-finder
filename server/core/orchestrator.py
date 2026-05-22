import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from server.core.chunkers import chunk_text
from server.core.data_loader import load_all_files
from server.core.embedder import embed_documents, embed_query
from server.core.query_loader import load_queries
from server.core.reranker import rerank_results
from server.core.retriever import search as retriever_search
from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.config import ExperimentConfig, RunParams, expand_sweep
from server.models.enums import ExperimentStatus, Phase, RetrievalMethod
from server.models.results import QueryResult
from server.models.status import RunStatus
from server.utils.logger import get_logger

logger = get_logger(__name__)

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


@dataclass
class _SweepControl:
    cancel: threading.Event = field(default_factory=threading.Event)
    pause: threading.Event = field(default_factory=threading.Event)


_sweep_controls: dict[str, _SweepControl] = {}


class ExperimentCancelledError(Exception):
    pass


class ExperimentPausedError(Exception):
    pass


def request_cancel(experiment_id: str) -> bool:
    """Signal a running experiment to stop. Returns True if it was in-flight."""
    control = _sweep_controls.get(experiment_id)
    if control is None:
        return False
    control.cancel.set()
    return True


def request_pause(experiment_id: str) -> bool:
    """Signal a running experiment to pause. Returns True if it was in-flight."""
    control = _sweep_controls.get(experiment_id)
    if control is None:
        return False
    control.pause.set()
    return True


def is_sweep_in_flight(experiment_id: str) -> bool:
    return experiment_id in _sweep_controls


def _params_signature(params: RunParams) -> ParamSignature:
    return (
        params.database_provider,
        params.embedding_provider,
        params.embedding_model,
        params.chunking_method.value,
        params.chunk_size,
        params.overlap,
        params.retrieval_method.value,
        params.rerank_provider,
        params.rerank_model,
    )


def _stored_enum_value(value: object | None) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value)


def _run_doc_signature(run: dict) -> ParamSignature:
    return (
        str(run.get("database_provider") or "mongodb"),
        str(run.get("embedding_provider") or ""),
        str(run.get("embedding_model") or ""),
        _stored_enum_value(run.get("chunking_method")),
        int(run.get("chunk_size") or 0),
        int(run.get("overlap") or 0),
        _stored_enum_value(run.get("retrieval_method")),
        str(run.get("rerank_provider") or ""),
        run.get("rerank_model"),
    )


def _completed_param_signatures(experiment_id: str) -> set[ParamSignature]:
    cursor = get_collection(RUN_STATUS_COLLECTION).find(
        {"experiment_id": experiment_id, "phase": Phase.COMPLETE.value},
        {
            "database_provider": 1,
            "embedding_provider": 1,
            "embedding_model": 1,
            "chunking_method": 1,
            "chunk_size": 1,
            "overlap": 1,
            "retrieval_method": 1,
            "rerank_provider": 1,
            "rerank_model": 1,
        },
    )
    return {_run_doc_signature(run) for run in cursor}


def _check_control(experiment_id: str) -> None:
    """Raise if this experiment was cancelled or paused."""
    control = _sweep_controls.get(experiment_id)
    if control is None:
        return
    if control.cancel.is_set():
        raise ExperimentCancelledError(f"Experiment {experiment_id} was cancelled")
    if control.pause.is_set():
        raise ExperimentPausedError(f"Experiment {experiment_id} was paused")


def run_sweep(experiment_id: str, config: ExperimentConfig) -> dict:
    """Execute all sweep runs for a pre-created experiment."""
    return _execute_sweep(experiment_id, config, skip_signatures=set())


def resume_sweep(experiment_id: str, config: ExperimentConfig) -> dict:
    """Continue a paused experiment, skipping parameter sets that already completed."""
    completed = _completed_param_signatures(experiment_id)
    logger.info(
        "Experiment %s resume: skipping %s completed parameter combination(s)",
        experiment_id,
        len(completed),
    )
    return _execute_sweep(experiment_id, config, skip_signatures=completed)


def _execute_sweep(
    experiment_id: str,
    config: ExperimentConfig,
    skip_signatures: set[ParamSignature],
) -> dict:
    """Declared sync; scheduled on the dedicated sweep executor (see executors.py)."""
    _sweep_controls[experiment_id] = _SweepControl()
    try:
        return _run_sweep_inner(experiment_id, config, skip_signatures)
    finally:
        _sweep_controls.pop(experiment_id, None)


def _run_sweep_inner(
    experiment_id: str,
    config: ExperimentConfig,
    skip_signatures: set[ParamSignature],
) -> dict:
    runs = expand_sweep(config)
    run_ids: list[str] = []
    logger.info(f"Experiment {experiment_id}: {len(runs)} runs to execute")

    cancelled = False
    paused = False
    first_run = True
    for params in runs:
        if _params_signature(params) in skip_signatures:
            continue

        try:
            _check_control(experiment_id)
        except ExperimentCancelledError:
            cancelled = True
            logger.info(f"Experiment {experiment_id} cancelled before run {len(run_ids) + 1}")
            break
        except ExperimentPausedError:
            paused = True
            logger.info(f"Experiment {experiment_id} paused before run {len(run_ids) + 1}")
            break

        # Set started_at when first run actually begins (not when experiment was created)
        if first_run:
            get_collection(EXPERIMENTS_COLLECTION).update_one(
                {"_id": experiment_id},
                {"$set": {"started_at": datetime.now(UTC)}},
            )
            first_run = False

        run_id = str(uuid.uuid4())
        run_ids.append(run_id)
        try:
            _run_single(experiment_id, run_id, params)
        except ExperimentCancelledError:
            cancelled = True
            logger.info(f"Experiment {experiment_id} cancelled during run {run_id}")
            break
        except ExperimentPausedError:
            paused = True
            logger.info(f"Experiment {experiment_id} paused during run {run_id}")
            break
        except Exception as e:
            logger.error(f"Run {run_id} failed: {e}", exc_info=True)
            if config.execution.on_error == "stop":
                break

    if cancelled:
        final_status = ExperimentStatus.CANCELLED
        failed_count = _count_failed_runs(experiment_id)
    elif paused:
        final_status = ExperimentStatus.PAUSED
        failed_count = _count_failed_runs(experiment_id)
    else:
        final_status, failed_count = _compute_final_status(experiment_id, len(runs))

    completed_at = datetime.now(UTC)
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {
            "$set": {
                "status": final_status,
                "run_count": len(runs),
                "failed_count": failed_count,
                "completed_at": completed_at,
            }
        },
    )
    _log_failed_run_summary(experiment_id, failed_count)
    logger.info(f"Experiment {experiment_id} finished: {final_status}")

    return {"experiment_id": experiment_id, "run_ids": run_ids, "status": final_status}


def _count_failed_runs(experiment_id: str) -> int:
    return int(
        get_collection(RUN_STATUS_COLLECTION).count_documents(
            {"experiment_id": experiment_id, "phase": Phase.FAILED.value}
        )
    )


def _log_failed_run_summary(experiment_id: str, failed_count: int) -> None:
    if failed_count <= 0:
        return
    cursor = get_collection(RUN_STATUS_COLLECTION).find(
        {"experiment_id": experiment_id, "phase": Phase.FAILED.value},
        {
            "run_id": 1,
            "embedding_model": 1,
            "chunking_method": 1,
            "chunk_size": 1,
            "error_message": 1,
        },
    )
    summaries: list[str] = []
    for doc in cursor:
        run_id = str(doc.get("run_id", "?"))
        label = (
            f"{run_id[:8]}… "
            f"({doc.get('embedding_model')}/{doc.get('chunking_method')}/{doc.get('chunk_size')})"
        )
        err = doc.get("error_message")
        if err:
            label = f"{label}: {str(err)[:80]}"
        summaries.append(label)
        if len(summaries) >= 10:
            break
    extra = f" — {'; '.join(summaries)}"
    if failed_count > len(summaries):
        extra += f" (+{failed_count - len(summaries)} more)"
    logger.warning("Experiment %s: %s failed run(s)%s", experiment_id, failed_count, extra)


def _compute_final_status(
    experiment_id: str,
    expected_run_count: int,
) -> tuple[ExperimentStatus, int]:
    runs = list(get_collection(RUN_STATUS_COLLECTION).find({"experiment_id": experiment_id}))
    complete = sum(1 for run in runs if run.get("phase") == Phase.COMPLETE.value)
    failed = sum(1 for run in runs if run.get("phase") == Phase.FAILED.value)

    if complete == expected_run_count and failed == 0:
        return ExperimentStatus.COMPLETE, failed
    if failed == expected_run_count or (failed > 0 and complete == 0):
        return ExperimentStatus.FAILED, failed
    return ExperimentStatus.PARTIAL, failed


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
        _check_control(experiment_id)
        _update_phase(run_id, Phase.PARSING)
        text = load_all_files(params.data_paths)
        if not text.strip():
            logger.warning(
                f"Run {run_id}: parsed 0 chars from {len(params.data_paths)} path(s) — "
                "check PDF text extraction or input files"
            )
        else:
            logger.info(
                f"Run {run_id}: parsed {len(text)} chars from {len(params.data_paths)} path(s)"
            )

        _check_control(experiment_id)
        _update_phase(run_id, Phase.CHUNKING)
        chunks = chunk_text(text, params.chunking_method, params.chunk_size, params.overlap)
        if not chunks:
            logger.warning(
                f"Run {run_id}: chunking produced 0 chunks from {len(text)} chars — "
                "embedding and retrieval will be empty"
            )
        else:
            logger.info(f"Run {run_id}: chunked into {len(chunks)} chunks")

        _check_control(experiment_id)
        _update_phase(run_id, Phase.EMBEDDING)
        embeddings = embed_documents(chunks, params.embedding_model, params.embedding_provider)
        logger.info(f"Run {run_id}: generated {len(embeddings)} embeddings")

        _check_control(experiment_id)
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

        _check_control(experiment_id)
        _update_phase(run_id, Phase.QUERYING)
        queries = load_queries(params.queries_file)
        logger.info(f"Run {run_id}: querying with {len(queries)} queries")

        for i, q in enumerate(queries, start=1):
            _check_control(experiment_id)
            query_id = str(uuid.uuid4())
            logger.debug(
                f"Run {run_id} query {i}/{len(queries)}: "
                f"persona={q.persona_id}, text='{q.text[:60]}...'"
            )

            needs_embedding = params.retrieval_method in (
                RetrievalMethod.DENSE,
                RetrievalMethod.HYBRID,
            )
            query_embedding = (
                embed_query(q.text, params.embedding_model, params.embedding_provider)
                if needs_embedding
                else None
            )

            search_results = retriever_search(
                method=params.retrieval_method,
                query_text=q.text,
                experiment_id=experiment_id,
                embedding_model=params.embedding_model,
                top_k=params.top_k_initial,
                query_embedding=query_embedding,
            )
            logger.debug(
                f"Run {run_id} query {i}: {params.retrieval_method.value} search "
                f"returned {len(search_results)} results"
            )

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

    except ExperimentCancelledError:
        logger.info(f"Run {run_id} interrupted by cancellation")
        _update_phase(run_id, Phase.INTERRUPTED, error_message="Cancelled by user")
        raise
    except ExperimentPausedError:
        logger.info(f"Run {run_id} interrupted by pause")
        _update_phase(run_id, Phase.INTERRUPTED, error_message="Paused by user")
        raise
    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}", exc_info=True)
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
        "updated_at": datetime.now(UTC),
        "elapsed_ms": elapsed_ms,
        "error_message": error_message,
    }
    get_collection(RUN_STATUS_COLLECTION).update_one({"run_id": run_id}, {"$set": update})

    if phase in (Phase.COMPLETE, Phase.FAILED, Phase.INTERRUPTED):
        _run_start_times.pop(run_id, None)
