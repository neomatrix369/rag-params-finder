from fastapi import APIRouter

from server.db.atlas import RUN_STATUS_COLLECTION, get_collection

router = APIRouter()


@router.get("/{run_id}/status")
async def get_run_status(run_id: str):
    """Get current status/phase of a single run."""
    status = get_collection(RUN_STATUS_COLLECTION).find_one(
        {"run_id": run_id}, {"_id": 0}
    )
    if not status:
        return {"error": "Run not found"}, 404
    return status
