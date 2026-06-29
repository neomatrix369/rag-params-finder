"""Health probes for /healthz and Docker Compose."""

from datetime import UTC

import certifi
from pymongo import MongoClient
from pymongo.errors import PyMongoError

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
        # Short timeout — default MongoClient waits ~30s; Docker healthcheck allows 10s.
        client: MongoClient = MongoClient(
            uri,
            tlsCAFile=certifi.where(),
            tz_aware=True,
            tzinfo=UTC,
            serverSelectionTimeoutMS=settings.health_check_mongodb_timeout_ms,
        )
        client.admin.command("ping")
        return "ok"
    except (PyMongoError, ValueError, OSError):
        return "error"
