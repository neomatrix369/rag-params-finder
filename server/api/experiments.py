import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from server.api.experiments_shared import (
    mongo_delete_experiment_data,
    mongo_find_experiment_by_id,
    mongo_find_experiment_with_runs,
    mongo_insert_experiment_doc,
    mongo_list_all_experiment_docs,
    mongo_list_results_for_experiment,
    mongo_load_explore_source,
    mongo_mark_experiment_cancelled_now,
)
from server.core.orchestrator import request_cancel, run_sweep
from server.models.config import ExperimentConfig, expand_sweep
from server.models.enums import ExperimentStatus
from server.utils.logger import get_logger
from server.utils.metadata import collect_experiment_metadata

logger = get_logger(__name__)

router = APIRouter()


@router.post("")
async def create_experiment(config: ExperimentConfig, background_tasks: BackgroundTasks):
    """Submit a new experiment sweep configuration."""
    experiment_id = str(uuid.uuid4())
    timestamp_suffix = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    stamped_name = f"{config.experiment_name}_{timestamp_suffix}"
    runs = expand_sweep(config)

    metadata = collect_experiment_metadata()
    now = datetime.utcnow()

    experiment_doc = {
        "_id": experiment_id,
        "experiment_id": experiment_id,
        "experiment_name": stamped_name,
        "config": config.model_dump(),
        "created_at": now,
        "started_at": now,
        "completed_at": None,
        "status": ExperimentStatus.RUNNING,
        "run_count": len(runs),
        **metadata,
        "data_paths": config.data_paths,
        "queries_file": config.queries_file,
        "rerank_model": config.retrieval.rerank_model,
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
            "retrieval_methods": [m.value for m in config.retrieval.methods],
            "rerank_provider": config.retrieval.rerank_provider,
        },
    }
    await asyncio.to_thread(mongo_insert_experiment_doc, experiment_doc)

    logger.info(f"Experiment '{stamped_name}' ({experiment_id}): {len(runs)} runs")
    background_tasks.add_task(run_sweep, experiment_id, config)

    return {
        "status": "submitted",
        "experiment_id": experiment_id,
        "experiment_name": stamped_name,
        "run_count": len(runs),
        "message": f"Experiment queued — {len(runs)} run(s) will execute",
    }


@router.get("")
async def list_experiments():
    """List all experiments."""
    logger.debug("GET /experiments — listing all")
    experiments = await asyncio.to_thread(mongo_list_all_experiment_docs)
    logger.debug(f"Listed {len(experiments)} experiments")
    return {"experiments": experiments}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a single experiment with its run statuses."""
    logger.debug(f"GET /experiments/{experiment_id}")
    experiment = await asyncio.to_thread(mongo_find_experiment_with_runs, experiment_id)
    if not experiment:
        logger.warning(f"Experiment not found: {experiment_id}")
        return {"error": "Experiment not found"}, 404

    runs = experiment["runs"]
    logger.debug(f"Experiment {experiment_id}: status={experiment.get('status')}, {len(runs)} runs")
    return experiment


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get all query results for an experiment."""
    logger.debug(f"GET /experiments/{experiment_id}/results")
    results = await asyncio.to_thread(mongo_list_results_for_experiment, experiment_id)
    logger.info(f"Returning {len(results)} results for experiment {experiment_id}")
    return {"experiment_id": experiment_id, "results": results}


@router.get("/{experiment_id}/explore")
async def explore_experiment(experiment_id: str, query: str | None = None):
    """Aggregated results explorer — ranked configs + detailed results."""
    from server.core.results_analyzer import analyze_results

    logger.debug(f"GET /experiments/{experiment_id}/explore (query={query!r})")

    experiment_doc, query_results, run_statuses = await asyncio.to_thread(
        mongo_load_explore_source, experiment_id
    )
    if not experiment_doc:
        raise HTTPException(status_code=404, detail="Experiment not found")

    explored = analyze_results(query_results, run_statuses, selected_query=query)
    explored["experiment_id"] = experiment_id
    explored["experiment_name"] = experiment_doc.get("experiment_name", "")

    logger.info(
        f"Explore {experiment_id}: {explored['query_count']} queries, "
        f"{explored['total_matches']} matches, "
        f"{len(explored['ranked_configs'])} configs"
    )
    return explored


@router.post("/{experiment_id}/cancel")
async def cancel_experiment(experiment_id: str):
    """Cancel a running experiment."""
    logger.info(f"POST /experiments/{experiment_id}/cancel")

    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") != ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Experiment is not running (status: {experiment.get('status')})",
        )

    signalled = request_cancel(experiment_id)

    if not signalled:
        await asyncio.to_thread(mongo_mark_experiment_cancelled_now, experiment_id)

    logger.info(f"Experiment {experiment_id} cancel requested (in-flight={signalled})")
    return {
        "status": "cancel_requested",
        "experiment_id": experiment_id,
        "message": "Experiment will stop after the current phase completes",
    }


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete an experiment and all its associated data (chunks, results, run statuses)."""
    logger.info(f"DELETE /experiments/{experiment_id}")

    experiment = await asyncio.to_thread(mongo_find_experiment_by_id, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.get("status") == ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete running experiment. Cancel it first.",
        )

    deleted_counts = await asyncio.to_thread(mongo_delete_experiment_data, experiment_id)

    logger.info(f"Experiment {experiment_id} deleted: {deleted_counts}")
    return {
        "status": "deleted",
        "experiment_id": experiment_id,
        "deleted_counts": deleted_counts,
        "message": "Experiment and all associated data deleted",
    }
