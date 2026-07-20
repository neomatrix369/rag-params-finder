import time
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime

from server.core.aim_logger import AimLogger
from server.core.chunkers import chunk_text
from server.core.data_loader import load_all_files
from server.core.embedder_factory import get_embedder
from server.core.experiment_control import (
    ExperimentCancelledError,
    ExperimentPausedError,
    check_control,
    register_sweep_control,
    unregister_sweep_control,
)
from server.core.query_loader import load_queries
from server.core.reranker import rerank_results
from server.core.retriever import search as retriever_search
from server.core.search_index_guard import validate_experiment_search_indexes
from server.core.search_index_plan import SearchIndexMismatchError
from server.core.sie_guard import SIEUnavailableError, validate_sie_readiness
from server.db.atlas import (
    CHUNKS_COLLECTION,
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.config import ExperimentConfig, RetrieverConfig, RunParams, expand_sweep
from server.models.enums import ExperimentStatus, Phase, RetrievalMethod, RetrieverType
from server.models.results import QueryResult, SearchResult
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


_TRADITIONAL_RETRIEVER_TYPES = {
    RetrieverType.DENSE,
    RetrieverType.SPARSE,
    RetrieverType.HYBRID,
}
_RERANKER_RETRIEVER_TYPES = {RetrieverType.RERANKER, RetrieverType.CROSS_ENCODER}


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

    results = retriever_search(
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

    _update_phase(run_id, Phase.RERANKING)
    return rerank_results(
        query=query_text,
        search_results=candidates,
        model=retriever_cfg.model,
        top_k=top_k_final,
        provider=retriever_cfg.provider,
    )


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
        str(run.get("database_provider") or "mongodb"),
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
            "retrieval_provider": 1,
            "retrieval_model": 1,
        },
    )
    return {_run_doc_signature(run) for run in cursor}


def _experiment_cancelled_in_db(experiment_id: str) -> bool:
    doc = get_collection(EXPERIMENTS_COLLECTION).find_one(
        {"_id": experiment_id},
        {"status": 1},
    )
    return bool(doc and doc.get("status") == ExperimentStatus.CANCELLED.value)


def run_sweep(experiment_id: str, config: ExperimentConfig) -> dict:
    """Execute all sweep runs for a pre-created experiment."""
    return _execute_sweep(experiment_id, config, skip_signatures=set())


def resume_sweep(experiment_id: str, config: ExperimentConfig) -> dict:
    """Continue a paused experiment, skipping parameter sets that already completed."""
    completed = _completed_param_signatures(experiment_id)
    logger.info(
        "resuming sweep — experiment %s, skipping %s completed parameter combination(s)",
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
    register_sweep_control(experiment_id)
    try:
        return _run_sweep_inner(experiment_id, config, skip_signatures)
    except SearchIndexMismatchError as exc:
        return _fail_experiment_preflight(experiment_id, config, str(exc))
    except SIEUnavailableError as exc:
        return _fail_experiment_preflight(experiment_id, config, str(exc))
    finally:
        unregister_sweep_control(experiment_id)


def _fail_experiment_preflight(
    experiment_id: str,
    config: ExperimentConfig,
    error_message: str,
) -> dict:
    """Mark experiment failed before any run starts due to search-index preflight."""
    runs = expand_sweep(config)
    completed_at = datetime.now(UTC)
    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {
            "$set": {
                "status": ExperimentStatus.FAILED,
                "run_count": len(runs),
                "failed_count": 0,
                "completed_at": completed_at,
                "error_message": error_message,
            }
        },
    )
    logger.error(
        "experiment preflight failed — %s: %s",
        experiment_id,
        error_message,
    )
    return {
        "experiment_id": experiment_id,
        "run_ids": [],
        "status": ExperimentStatus.FAILED,
        "error_message": error_message,
    }


def _run_sweep_inner(
    experiment_id: str,
    config: ExperimentConfig,
    skip_signatures: set[ParamSignature],
) -> dict:
    if _experiment_cancelled_in_db(experiment_id):
        logger.info("sweep skipped — experiment %s already cancelled", experiment_id)
        return {
            "experiment_id": experiment_id,
            "run_ids": [],
            "status": ExperimentStatus.CANCELLED,
        }

    try:
        check_control(experiment_id)
    except ExperimentCancelledError:
        logger.info("sweep skipped — experiment %s cancel signalled before start", experiment_id)
        return {
            "experiment_id": experiment_id,
            "run_ids": [],
            "status": ExperimentStatus.CANCELLED,
        }

    validate_experiment_search_indexes(config)
    validate_sie_readiness(config)
    all_runs = list(expand_sweep(config))
    runs = [params for params in all_runs if _params_signature(params) not in skip_signatures]
    run_ids: list[str] = []
    logger.info(
        "sweep scheduled — experiment %s, %s runnable run(s) of %s total",
        experiment_id,
        len(runs),
        len(all_runs),
    )

    cancelled = False
    paused = False
    infrastructure_error: str | None = None
    stop_after_failure = False
    max_workers = config.execution.parallelism

    run_iter = iter(runs)
    futures: dict[Future, tuple[str, RunParams]] = {}
    first_run_set = False

    def _submit_next() -> bool:
        """Submit exactly one run if available and control allows execution."""
        nonlocal first_run_set
        nonlocal cancelled
        nonlocal paused
        nonlocal stop_after_failure

        if stop_after_failure:
            return False

        try:
            params = next(run_iter)
        except StopIteration:
            return False

        try:
            check_control(experiment_id)
        except ExperimentCancelledError:
            cancelled = True
            stop_after_failure = True
            return False
        except ExperimentPausedError:
            paused = True
            stop_after_failure = True
            return False

        if not first_run_set:
            get_collection(EXPERIMENTS_COLLECTION).update_one(
                {"_id": experiment_id},
                {"$set": {"started_at": datetime.now(UTC)}},
            )
            first_run_set = True

        run_id = str(uuid.uuid4())
        run_ids.append(run_id)
        logger.info("run submitted — experiment %s, run_id=%s", experiment_id, run_id)
        futures[
            executor.submit(
                _run_single,
                experiment_id,
                run_id,
                params,
                config.execution.parallelism,
            )
        ] = (run_id, params)
        return True

    with ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix=f"sweep-{experiment_id[:8]}"
    ) as executor:
        for _ in range(max_workers):
            if not _submit_next():
                break

        while futures:
            done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
            if not done:
                break

            for future in done:
                run_id, _ = futures.pop(future)
                try:
                    future.result()
                except ExperimentCancelledError:
                    cancelled = True
                    logger.info("experiment cancelled — %s during run %s", experiment_id, run_id)
                except ExperimentPausedError:
                    paused = True
                    logger.info("experiment paused — %s during run %s", experiment_id, run_id)
                except SIEUnavailableError as exc:
                    infrastructure_error = str(exc)
                    stop_after_failure = True
                    logger.error(
                        "SIE unavailable — stopping experiment %s after run %s: %s",
                        experiment_id,
                        run_id,
                        exc,
                    )
                except Exception as e:
                    logger.error("run failed — %s: %s", run_id, e, exc_info=True)
                    if config.execution.on_error == "stop":
                        stop_after_failure = True

                if cancelled or paused:
                    stop_after_failure = True

            if stop_after_failure:
                continue

            try:
                check_control(experiment_id)
            except ExperimentCancelledError:
                cancelled = True
                stop_after_failure = True
                continue
            except ExperimentPausedError:
                paused = True
                stop_after_failure = True
                continue

            submitted = True
            while submitted:
                submitted = _submit_next()

    if cancelled:
        final_status = ExperimentStatus.CANCELLED
        failed_count = _count_failed_runs(experiment_id)
    elif paused:
        final_status = ExperimentStatus.PAUSED
        failed_count = _count_failed_runs(experiment_id)
    else:
        final_status, failed_count = _compute_final_status(experiment_id, len(all_runs))

    completed_at = datetime.now(UTC)
    experiment_update: dict = {
        "status": final_status,
        "run_count": len(all_runs),
        "failed_count": failed_count,
        "completed_at": completed_at,
    }
    if infrastructure_error:
        experiment_update["error_message"] = infrastructure_error
        if final_status not in {ExperimentStatus.CANCELLED, ExperimentStatus.PAUSED}:
            final_status = ExperimentStatus.FAILED
            experiment_update["status"] = final_status

    get_collection(EXPERIMENTS_COLLECTION).update_one(
        {"_id": experiment_id},
        {"$set": experiment_update},
    )
    _log_failed_run_summary(experiment_id, failed_count)
    logger.info("sweep finished — experiment %s, status=%s", experiment_id, final_status)

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
    logger.warning(
        "failed runs summary — experiment %s, %s failure(s)%s",
        experiment_id,
        failed_count,
        extra,
    )


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


def _run_single(
    experiment_id: str,
    run_id: str,
    params: RunParams,
    embedding_parallelism: int = 1,
) -> None:
    """Execute one run of the pipeline for a single parameter combination."""
    retriever_summary = ", ".join(
        r.type.value
        if r.type in {RetrieverType.DENSE, RetrieverType.SPARSE, RetrieverType.HYBRID}
        else f"{r.type.value}({r.provider}:{r.model})"
        for r in params.retrievers
    )
    logger.info(
        "run pipeline — %s model=%s chunking=%s size=%s+%s retrievers=[%s]",
        run_id,
        params.embedding_model,
        params.chunking_method.value,
        params.chunk_size,
        params.overlap,
        retriever_summary,
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
        padding=params.padding,
        retrievers=params.retrievers,
        retrieval_method=params.retrieval_method,
        retrieval_provider=params.retrieval_provider,
        retrieval_model=params.retrieval_model,
    )
    get_collection(RUN_STATUS_COLLECTION).insert_one(run_status.model_dump())

    try:
        check_control(experiment_id)
        _update_phase(run_id, Phase.PARSING)
        text = load_all_files(params.data_paths)
        if not text.strip():
            logger.warning(
                "parse empty — run %s, 0 chars from %s path(s); check PDF text or input files",
                run_id,
                len(params.data_paths),
            )
        else:
            logger.info(
                "parse OK — run %s, %s chars from %s path(s)",
                run_id,
                len(text),
                len(params.data_paths),
            )

        check_control(experiment_id)
        _update_phase(run_id, Phase.CHUNKING)
        chunks = chunk_text(
            text, params.chunking_method, params.chunk_size, params.overlap, params.padding
        )
        if not chunks:
            logger.warning(
                "chunking empty — run %s, 0 chunks from %s chars; embedding/retrieval empty",
                run_id,
                len(text),
            )
        else:
            logger.info("chunking OK — run %s, %s chunks", run_id, len(chunks))

        check_control(experiment_id)
        _update_phase(run_id, Phase.EMBEDDING)
        embed_docs_fn, embed_query_fn = get_embedder(params.embedding_provider)

        def cancel_check() -> None:
            check_control(experiment_id)

        embed_kwargs: dict[str, object] = {"cancel_check": cancel_check}
        if params.embedding_provider == "local":
            embed_kwargs["parallelism"] = embedding_parallelism

        embeddings = embed_docs_fn(
            chunks,
            params.embedding_model,
            **embed_kwargs,
        )
        logger.info("embed OK — run %s, %s embeddings", run_id, len(embeddings))

        check_control(experiment_id)
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
                "padding": params.padding,
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        get_collection(CHUNKS_COLLECTION).insert_many(chunk_docs)
        logger.info("chunks stored — %s documents", len(chunk_docs))

        check_control(experiment_id)
        _update_phase(run_id, Phase.QUERYING)
        queries = load_queries(params.queries_file)
        logger.info("query phase — run %s, %s queries", run_id, len(queries))

        for i, q in enumerate(queries, start=1):
            check_control(experiment_id)
            query_id = str(uuid.uuid4())
            logger.debug(
                "query trace — run %s query %s/%s persona=%s text=%s",
                run_id,
                i,
                len(queries),
                q.persona_id,
                q.text[:60] + ("..." if len(q.text) > 60 else ""),
            )

            retriever_cfg = _primary_retriever(params)
            query_embedding: list[float] | None = None

            if retriever_cfg.type in _TRADITIONAL_RETRIEVER_TYPES:
                search_results, _ = _search_traditional_retriever(
                    retriever_cfg,
                    run_id=run_id,
                    query_text=q.text,
                    experiment_id=experiment_id,
                    embedding_model=params.embedding_model,
                    embed_query_fn=embed_query_fn,
                    top_k=params.top_k_initial,
                    query_embedding=query_embedding,
                )
                search_results = search_results[: params.top_k_final]
                logger.debug(
                    "retrieval hits — run %s query %s/%s method=%s count=%s",
                    run_id,
                    i,
                    len(queries),
                    retriever_cfg.type.value,
                    len(search_results),
                )
            elif retriever_cfg.type in _RERANKER_RETRIEVER_TYPES:
                search_results = _search_reranker_retriever(
                    retriever_cfg,
                    run_id=run_id,
                    query_text=q.text,
                    experiment_id=experiment_id,
                    embedding_model=params.embedding_model,
                    embed_query_fn=embed_query_fn,
                    top_k_initial=params.top_k_initial,
                    top_k_final=params.top_k_final,
                )
                logger.debug(
                    "rerank OK — run %s query %s/%s type=%s count=%s",
                    run_id,
                    i,
                    len(queries),
                    retriever_cfg.type.value,
                    len(search_results),
                )
            else:
                raise ValueError(f"Unknown retriever type: {retriever_cfg.type}")

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

        logger.info("queries complete — run %s, %s queries", run_id, len(queries))

        AimLogger.log_run(
            {
                "experiment_id": experiment_id,
                "run_id": run_id,
                "model_name": params.embedding_model,
                "model_source": params.embedding_provider,
                "retrieval_method": params.retrieval_method.value,
                "chunking_method": params.chunking_method.value,
                "chunk_size": params.chunk_size,
                "overlap": params.overlap,
                "latency_ms": int(
                    (time.monotonic() - _run_start_times.get(run_id, time.monotonic())) * 1000
                ),
            }
        )
        _update_phase(run_id, Phase.COMPLETE)

    except ExperimentCancelledError:
        logger.info("run interrupted — %s cancelled", run_id)
        _update_phase(run_id, Phase.INTERRUPTED, error_message="Cancelled by user")
        raise
    except ExperimentPausedError:
        logger.info("run interrupted — %s paused", run_id)
        _update_phase(run_id, Phase.INTERRUPTED, error_message="Paused by user")
        raise
    except Exception as e:
        logger.error("run failed — %s: %s", run_id, e, exc_info=True)
        _update_phase(run_id, Phase.FAILED, error_message=str(e))
        raise


_run_start_times: dict[str, float] = {}


def _update_phase(run_id: str, phase: Phase, error_message: str | None = None) -> None:
    """Update run_status phase and elapsed_ms in MongoDB."""
    now = time.monotonic()
    if run_id not in _run_start_times:
        _run_start_times[run_id] = now

    elapsed_ms = int((now - _run_start_times[run_id]) * 1000)
    logger.info("phase updated — run %s, %s (%sms)", run_id, phase.value, elapsed_ms)

    update: dict = {
        "phase": phase.value,
        "updated_at": datetime.now(UTC),
        "elapsed_ms": elapsed_ms,
        "error_message": error_message,
    }
    get_collection(RUN_STATUS_COLLECTION).update_one({"run_id": run_id}, {"$set": update})

    if phase in (Phase.COMPLETE, Phase.FAILED, Phase.INTERRUPTED):
        _run_start_times.pop(run_id, None)
