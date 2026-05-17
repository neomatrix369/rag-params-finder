import asyncio

from fastapi import APIRouter

from server.db.atlas import RUN_STATUS_COLLECTION, get_collection
from server.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _mongo_fetch_run(run_id: str):
    return get_collection(RUN_STATUS_COLLECTION).find_one({"run_id": run_id}, {"_id": 0})


@router.get("/{run_id}/status")
async def get_run_status(run_id: str):
    """Get current status/phase of a single run."""
    logger.debug(f"GET /runs/{run_id}/status")
    status = await asyncio.to_thread(_mongo_fetch_run, run_id)
    if not status:
        logger.warning(f"Run not found: {run_id}")
        return {"error": "Run not found"}, 404
    logger.debug(f"Run {run_id} phase={status.get('phase')}")
    return status
