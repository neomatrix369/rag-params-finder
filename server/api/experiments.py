from fastapi import APIRouter, BackgroundTasks
from server.models.config import ExperimentConfig
from server.core.orchestrator import run_experiment
from server.db.atlas import get_collection, EXPERIMENTS_COLLECTION
from server.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("")
async def create_experiment(config: ExperimentConfig, background_tasks: BackgroundTasks):
    """Submit a new experiment configuration."""

    logger.info(f"Received experiment: {config.experiment_name}")

    # Run experiment in background
    background_tasks.add_task(run_experiment, config)

    # Return immediately with placeholder IDs
    # Actual IDs will be generated in the background task
    return {
        "status": "submitted",
        "experiment_name": config.experiment_name,
        "message": "Experiment queued for execution"
    }


@router.get("")
async def list_experiments():
    """List all experiments."""

    experiments_collection = get_collection(EXPERIMENTS_COLLECTION)
    experiments = list(experiments_collection.find({}, {"_id": 0}).sort("created_at", -1))

    logger.info(f"Returning {len(experiments)} experiments")

    return {"experiments": experiments}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a single experiment by ID."""

    experiments_collection = get_collection(EXPERIMENTS_COLLECTION)
    experiment = experiments_collection.find_one(
        {"experiment_id": experiment_id},
        {"_id": 0}
    )

    if not experiment:
        return {"error": "Experiment not found"}, 404

    return experiment
