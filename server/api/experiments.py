import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import SupportsInt, cast

from fastapi import APIRouter, HTTPException

from server.api.experiments_shared import (
    mongo_delete_experiment_data,
    mongo_find_experiment_by_id,
    mongo_find_experiment_with_runs,
    mongo_get_experiment_db_stats,
    mongo_get_vector_db_stats_grouped,
    mongo_insert_experiment_doc,
    mongo_list_all_experiment_docs,
    mongo_list_results_for_experiment,
    mongo_load_explore_source,
    mongo_mark_experiment_cancelled_now,
    mongo_mark_experiment_paused_now,
    mongo_mark_experiment_running,
)
from server.core.executors import HEAVY_READ_EXECUTOR, schedule_sweep
from server.core.experiment_control import is_sweep_in_flight, request_cancel, request_pause
from server.core.orchestrator import resume_sweep, run_sweep
from server.core.search_index_guard import validate_experiment_search_indexes
from server.core.search_index_plan import SearchIndexMismatchError
from server.core.sie_guard import SIEUnavailableError, validate_sie_readiness
from server.db.atlas import EXPERIMENTS_COLLECTION, RUN_STATUS_COLLECTION, get_collection
from server.models.config import ExperimentConfig, expand_sweep
from server.models.enums import ExperimentStatus, Phase, RetrieverType
from server.utils.log_throttle import info_throttled
from server.utils.logger import get_logger
from server.utils.metadata import collect_experiment_metadata

logger = get_logger(__name__)

router = APIRouter()
_TERMINAL_PHASES = frozenset(
    {
        Phase.COMPLETE.value,
        Phase.FAILED.value,
        Phase.INTERRUPTED.value,
    }
)


def _planned_run_count(config: ExperimentConfig) -> int:
    if config.execution.search_strategy == "bayesian":
        return _resolve_bayesian_n_trials(config)
    return len(expand_sweep(config))


def _resolve_bayesian_n_trials(config: ExperimentConfig) -> int:
    grid_equivalent = len(config.chunking.params.chunk_sizes) * len(config.chunking.params.overlaps)
    configured = config.execution.bayesian.n_trials
    if configured is None:
        logger.info(
            "bayesian n_trials not set; defaulting to grid-equivalent %s",
            grid_equivalent,
        )
        return grid_equivalent
    if configured > grid_equivalent:
        logger.warning(
            "requested bayesian n_trials=%s exceeds grid-equivalent=%s, capping at grid-equivalent",
            configured,
            grid_equivalent,
        )
        return grid_equivalent
    return configured


def _to_non_negative_int(value: object) -> int | None:
    try:
        as_int = int(cast(SupportsInt, value))
    except (TypeError, ValueError):
        return None
    return max(0, int(as_int))


def _is_bayesian_experiment(experiment: dict) -> bool:
    config = experiment.get("config")
    if not isinstance(config, dict):
        return False
    execution = config.get("execution")
    if not isinstance(execution, dict):
        return False
    return execution.get("search_strategy") == "bayesian"


def _ensure_bayesian_summary(
    experiment: dict,
    runs: list[dict] | None = None,
) -> None:
    if not _is_bayesian_experiment(experiment):
        return

    planned_trials = _to_non_negative_int(experiment.get("run_count"))
    if planned_trials is None:
        return

    existing_summary = experiment.get("bayesian_summary")
    if not isinstance(existing_summary, dict):
        existing_summary = {}

    planned_trials = int(planned_trials)
    attempted_trials = existing_summary.get("attempted_trials")
    if isinstance(attempted_trials, int):
        attempted_trials = _to_non_negative_int(attempted_trials) or 0
    elif isinstance(runs, list):
        attempted_trials = len(runs)
    else:
        attempted_trials = 0

    if "discarded_trials" in existing_summary:
        discarded_trials = _to_non_negative_int(existing_summary["discarded_trials"]) or 0
    else:
        discarded_trials = existing_summary.get("discarded_trials", 0)
        discarded_trials = _to_non_negative_int(discarded_trials) or 0

    not_started = max(
        0,
        planned_trials - attempted_trials - discarded_trials,
    )

    existing_summary.update(
        {
            "planned_trials": planned_trials,
            "attempted_trials": attempted_trials,
            "discarded_trials": discarded_trials,
            "grid_equivalent_count": _to_non_negative_int(
                existing_summary.get("grid_equivalent_count")
            )
            or _to_non_negative_int(experiment.get("grid_equivalent_count"))
            or planned_trials,
            "not_started": not_started,
        }
    )
    experiment["bayesian_summary"] = existing_summary


def _normalize_stale_running_status(experiment: dict) -> dict:
    """If status is still RUNNING but no active sweep exists, reconcile from run status."""
    runs = experiment.get("runs")
    if not isinstance(runs, list):
        runs = []
    if experiment.get("status") != ExperimentStatus.RUNNING:
        _ensure_bayesian_summary(experiment, runs=runs)
        return experiment

    experiment_id = experiment.get("experiment_id") or experiment.get("_id")
    if not experiment_id or is_sweep_in_flight(experiment_id):
        return experiment

    runs = list(runs)
    if not runs:
        runs = list(
            get_collection(RUN_STATUS_COLLECTION).find(
                {"experiment_id": experiment_id},
                {"_id": 0},
            )
        )
    _ensure_bayesian_summary(experiment, runs=runs)
    if not runs:
        return experiment

    if any(run.get("phase") not in _TERMINAL_PHASES for run in runs):
        return experiment

    expected = int(experiment.get("run_count") or 0)
    complete = sum(1 for run in runs if run.get("phase") == Phase.COMPLETE.value)
    failed = sum(1 for run in runs if run.get("phase") == Phase.FAILED.value)
    interrupted = sum(1 for run in runs if run.get("phase") == Phase.INTERRUPTED.value)

    if complete == expected and failed == 0:
        resolved_status = ExperimentStatus.COMPLETE
        completion_reason = "all_planned_trials_completed"
    elif failed == 0 and interrupted == 0 and complete < expected and complete > 0:
        resolved_status = ExperimentStatus.COMPLETE
        completion_reason = "completed_with_sampling_shortfall"
    elif failed == expected or (failed > 0 and complete == 0 and failed == len(runs)):
        resolved_status = ExperimentStatus.FAILED
        completion_reason = "all_trials_failed"
    elif failed == 0 and interrupted > 0 and complete > 0:
        resolved_status = ExperimentStatus.PARTIAL
        completion_reason = "interrupted_before_completion"
    elif failed > 0:
        resolved_status = ExperimentStatus.PARTIAL
        completion_reason = "partial_failures"
    else:
        resolved_status = ExperimentStatus.PARTIAL
        completion_reason = "incomplete_before_completion"

    now = datetime.now(UTC)
    resolved = {
        "status": resolved_status,
        "failed_count": failed,
        "completion_reason": completion_reason,
        "completed_at": now,
    }
    get_collection(EXPERIMENTS_COLLECTION).update_one({"_id": experiment_id}, {"$set": resolved})
    experiment.update(resolved)
    _ensure_bayesian_summary(experiment, runs=runs)
    return experiment


async def _run_heavy_read[R](fn: Callable[[], R]) -> R:
    """Run expensive read-only Mongo aggregations off the default API thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(HEAVY_READ_EXECUTOR, fn)


@router.post("")
async def create_experiment(config: ExperimentConfig):
    """Submit a new experiment sweep configuration."""
    try:
        await asyncio.to_thread(validate_experiment_search_indexes, config)
        await asyncio.to_thread(validate_sie_readiness, config)
    except SearchIndexMismatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SIEUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    experiment_id = str(uuid.uuid4())
    timestamp_suffix = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    stamped_name = f"{config.experiment_name}_{timestamp_suffix}"
    runs = _planned_run_count(config)

    metadata = collect_experiment_metadata()
    now = datetime.now(UTC)

    retrieval_methods_for_summary = [r.type.value for r in config.retrieval.retrievers]
    rerankers = [
        r
        for r in config.retrieval.retrievers
        if r.type in {RetrieverType.RERANKER, RetrieverType.CROSS_ENCODER}
    ]
    retrieval_provider_for_summary = (
        rerankers[0].provider if rerankers else config.retrieval.retrieval_provider
    )
    retrieval_model_for_doc = rerankers[0].model if rerankers else config.retrieval.retrieval_model

    experiment_doc = {
        "_id": experiment_id,
        "experiment_id": experiment_id,
        "experiment_name": stamped_name,
        "config": config.model_dump(),
        "created_at": now,
        "started_at": None,  # Set when first run actually begins
        "completed_at": None,
        "status": ExperimentStatus.RUNNING,
        "run_count": runs,
        "grid_equivalent_count": len(expand_sweep(config)),
        **metadata,
        "data_paths": config.data_paths,
        "queries_file": config.queries_file,
        "retrieval_model": retrieval_model_for_doc,
        "top_k_initial": config.retrieval.top_k_initial,
        "top_k_final": config.retrieval.top_k_final,
        "parallelism": config.execution.parallelism,
        "on_error": config.execution.on_error,
        "sweep_summary": {
            "database_provider": config.database_provider,
            "embedding_provider": config.embedding.provider,
            "models": config.embedding.models,
            "chunking_methods": [m.value for m in config.chunking.methods],
            "chunk_sizes": config.chunking.params.chunk_sizes,
            "overlaps": config.chunking.params.overlaps,
            "paddings": config.chunking.params.paddings,
            "retrieval_methods": retrieval_methods_for_summary,
            "retrieval_provider": retrieval_provider_for_summary,
        },
    }
    await asyncio.to_thread(mongo_insert_experiment_doc, experiment_doc)

    logger.info(
        "experiment created — %s (%s), %s planned run(s), %s run(s) per trial strategy",
        stamped_name,
        experiment_id,
        runs,
        len(expand_sweep(config)),
    )
    schedule_sweep(run_sweep, experiment_id, config)

    return {
        "status": "submitted",
        "experiment_id": experiment_id,
        "experiment_name": stamped_name,
        "run_count": runs,
        "message": f"Experiment queued — {runs} run(s) will execute",
    }


@router.get("")
async def list_experiments():
    """List all experiments."""
    logger.debug("list OK — GET /experiments")
    experiments = await asyncio.to_thread(mongo_list_all_experiment_docs)
    for experiment in experiments:
        await asyncio.to_thread(_normalize_stale_running_status, experiment)
    logger.debug("list OK — %s experiment(s)", len(experiments))
    return {"experiments": experiments}


@router.get("/vector-db-stats")
async def get_vector_db_stats_grouped():
    """Vector DB stats for all experiments, grouped by cluster."""
    logger.debug("vector DB stats — GET /experiments/vector-db-stats")
    payload = await _run_heavy_read(mongo_get_vector_db_stats_grouped)
    info_throttled(
        logger,
        "poll:vector-db-stats",
        "vector DB stats OK — %s group(s)",
        len(payload["groups"]),
    )
    return payload


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a single experiment with its run statuses."""
    logger.debug("detail — GET /experiments/%s", experiment_id)
    experiment = await asyncio.to_thread(mongo_find_experiment_with_runs, experiment_id)
    if not experiment:
        logger.warning("detail failed — experiment not found: %s", experiment_id)
        raise HTTPException(status_code=404, detail="Experiment not found")

    runs = experiment["runs"]
    _normalize_stale_running_status(experiment)
    logger.debug(
        "detail OK — %s status=%s, %s run row(s)",
        experiment_id,
        experiment.get("status"),
        len(runs),
    )
    return experiment


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get all query results for an experiment."""
    logger.debug("results — GET /experiments/%s/results", experiment_id)
    results = await asyncio.to_thread(mongo_list_results_for_experiment, experiment_id)
    info_throttled(
        logger,
        f"poll:results:{experiment_id}",
        "results OK — %s row(s) for experiment %s",
        len(results),
        experiment_id,
    )
    return {"experiment_id": experiment_id, "results": results}


@router.get("/{experiment_id}/db-stats")
async def get_experiment_db_stats(experiment_id: str):
    """Get vector database statistics for an experiment."""
    logger.debug("db-stats — GET /experiments/%s/db-stats", experiment_id)
    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    stats = await _run_heavy_read(lambda: mongo_get_experiment_db_stats(experiment_id))
    info_throttled(
        logger,
        f"poll:db-stats:{experiment_id}",
        "db-stats OK — %s: %s chunks, %s MB",
        experiment_id,
        stats["total_chunks"],
        stats["estimated_storage_mb"],
    )
    return {"experiment_id": experiment_id, "db_stats": stats}


@router.get("/{experiment_id}/explore")
async def explore_experiment(experiment_id: str, query: str | None = None):
    """Aggregated results explorer — ranked configs + detailed results."""
    from server.core.results_analyzer import analyze_results

    logger.debug("explore — GET /experiments/%s/explore query=%r", experiment_id, query)

    experiment_doc, query_results, run_statuses = await _run_heavy_read(
        lambda: mongo_load_explore_source(experiment_id)
    )
    if not experiment_doc:
        raise HTTPException(status_code=404, detail="Experiment not found")

    explored = analyze_results(query_results, run_statuses, selected_query=query)
    explored["experiment_id"] = experiment_id
    explored["experiment_name"] = experiment_doc.get("experiment_name", "")

    info_throttled(
        logger,
        f"poll:explore:{experiment_id}",
        "explore OK — %s: %s queries, %s matches, %s configs",
        experiment_id,
        explored["query_count"],
        explored["total_matches"],
        len(explored["ranked_configs"]),
    )
    return explored


@router.post("/{experiment_id}/cancel")
async def cancel_experiment(experiment_id: str):
    """Cancel a running experiment."""
    logger.info("cancel started — POST /experiments/%s/cancel", experiment_id)

    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") != ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Experiment is not running (status: {experiment.get('status')})",
        )

    signalled = request_cancel(experiment_id)
    await asyncio.to_thread(mongo_mark_experiment_cancelled_now, experiment_id)

    logger.info("cancel OK — %s in-flight=%s", experiment_id, signalled)
    return {
        "status": "cancelled" if not signalled else "cancel_requested",
        "experiment_id": experiment_id,
        "message": (
            "Experiment cancelled"
            if not signalled
            else "Cancellation signalled — stopping after the current batch or phase"
        ),
    }


@router.post("/{experiment_id}/pause")
async def pause_experiment(experiment_id: str):
    """Pause a running experiment after the current phase completes."""
    logger.info("pause started — POST /experiments/%s/pause", experiment_id)

    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") != ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Experiment is not running (status: {experiment.get('status')})",
        )

    signalled = request_pause(experiment_id)

    if not signalled:
        await asyncio.to_thread(mongo_mark_experiment_paused_now, experiment_id)

    logger.info("pause OK — %s in-flight=%s", experiment_id, signalled)
    return {
        "status": "pause_requested",
        "experiment_id": experiment_id,
        "message": "Experiment will pause after the current phase completes",
    }


@router.post("/{experiment_id}/resume")
async def resume_experiment(experiment_id: str):
    """Resume a paused experiment from the next incomplete parameter combination."""
    logger.info("resume started — POST /experiments/%s/resume", experiment_id)

    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    status = experiment.get("status")
    if status == ExperimentStatus.RUNNING:
        if is_sweep_in_flight(experiment_id):
            raise HTTPException(status_code=409, detail="Experiment is already running")
        raise HTTPException(
            status_code=409,
            detail=(
                "Experiment is marked running but not executing — restart the server or reconcile"
            ),
        )
    if status != ExperimentStatus.PAUSED:
        raise HTTPException(
            status_code=409,
            detail=f"Experiment cannot be resumed (status: {status})",
        )

    config_payload = experiment.get("config")
    if not config_payload:
        raise HTTPException(status_code=400, detail="Experiment config is missing")

    config = ExperimentConfig.model_validate(config_payload)
    if config.execution.search_strategy == "bayesian":
        raise HTTPException(
            status_code=409,
            detail=("Bayesian experiments cannot be resumed (study state is in-memory only)"),
        )
    await asyncio.to_thread(mongo_mark_experiment_running, experiment_id)
    schedule_sweep(resume_sweep, experiment_id, config)

    runs = _planned_run_count(config)
    logger.info("resume OK — %s scheduled, %s run(s) in sweep", experiment_id, runs)
    return {
        "status": "resume_requested",
        "experiment_id": experiment_id,
        "run_count": runs,
        "message": "Experiment resumed — remaining parameter combinations will execute",
    }


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete an experiment and all its associated data (chunks, results, run statuses)."""
    logger.info("delete started — DELETE /experiments/%s", experiment_id)

    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") == ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete running experiment. Cancel it first.",
        )

    deleted_counts = await asyncio.to_thread(mongo_delete_experiment_data, experiment_id)

    logger.info("delete OK — %s counts=%s", experiment_id, deleted_counts)
    return {
        "status": "deleted",
        "experiment_id": experiment_id,
        "deleted_counts": deleted_counts,
        "message": "Experiment and all associated data deleted",
    }
