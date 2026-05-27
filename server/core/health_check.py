"""Health probes for /healthz and Docker Compose."""

from pymongo.errors import PyMongoError

from server.db.atlas import get_mongo_client
from server.settings import settings

_MONGODB_PLACEHOLDER_MARKERS = (
    "your_mongodb_atlas_uri_here",
    "<user>",
    "<pass>",
    "<cluster>",
)


def mongodb_health_status() -> str:
    """Return ok, error, or skipped for Atlas connectivity."""
    uri = (settings.mongodb_uri or "").strip()
    if not uri:
        return "skipped"
    lowered = uri.lower()
    if any(marker in lowered for marker in _MONGODB_PLACEHOLDER_MARKERS):
        return "error"
    try:
        get_mongo_client().admin.command("ping")
        return "ok"
    except (PyMongoError, ValueError, OSError):
        return "error"
