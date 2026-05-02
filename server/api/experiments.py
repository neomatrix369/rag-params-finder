import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from server.core.orchestrator import run_sweep
from server.db.atlas import (
    EXPERIMENTS_COLLECTION,
    RESULTS_COLLECTION,
    RUN_STATUS_COLLECTION,
    get_collection,
)
from server.models.config import ExperimentConfig, expand_sweep
from server.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("")
async def create_experiment(config: ExperimentConfig, background_tasks: BackgroundTasks):
    """Submit a new experiment sweep configuration."""
    experiment_id = str(uuid.uuid4())
    timestamp_suffix = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    stamped_name = f"{config.experiment_name}_{timestamp_suffix}"
    runs = expand_sweep(config)

    experiment_doc = {
        "_id": experiment_id,
        "experiment_id": experiment_id,
        "experiment_name": stamped_name,
        "config": config.model_dump(),
        "created_at": datetime.utcnow(),
        "status": "running",
        "run_count": len(runs),
    }
    get_collection(EXPERIMENTS_COLLECTION).insert_one(experiment_doc)

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
    experiments = list(
        get_collection(EXPERIMENTS_COLLECTION)
        .find({}, {"_id": 0})
        .sort("created_at", -1)
    )
    logger.info(f"Listed {len(experiments)} experiments")
    return {"experiments": experiments}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a single experiment with its run statuses."""
    logger.debug(f"GET /experiments/{experiment_id}")
    experiment = get_collection(EXPERIMENTS_COLLECTION).find_one(
        {"experiment_id": experiment_id}, {"_id": 0}
    )
    if not experiment:
        logger.warning(f"Experiment not found: {experiment_id}")
        return {"error": "Experiment not found"}, 404

    runs = list(
        get_collection(RUN_STATUS_COLLECTION)
        .find({"experiment_id": experiment_id}, {"_id": 0})
        .sort("created_at", 1)
    )
    experiment["runs"] = runs
    logger.debug(f"Experiment {experiment_id}: status={experiment.get('status')}, {len(runs)} runs")
    return experiment


@router.get("/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get all query results for an experiment."""
    logger.debug(f"GET /experiments/{experiment_id}/results")
    results = list(
        get_collection(RESULTS_COLLECTION)
        .find({"experiment_id": experiment_id}, {"_id": 0})
    )
    logger.info(f"Returning {len(results)} results for experiment {experiment_id}")
    return {"experiment_id": experiment_id, "results": results}
