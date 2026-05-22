from datetime import UTC

import certifi
from pymongo import MongoClient
from pymongo.database import Database

from server.settings import settings
from server.utils.logger import get_logger

logger = get_logger(__name__)

_client: MongoClient | None = None
_db: Database | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        if not settings.mongodb_uri:
            raise ValueError("MONGODB_URI not set in .env or environment")
        _client = MongoClient(
            settings.mongodb_uri, tlsCAFile=certifi.where(), tz_aware=True, tzinfo=UTC
        )
        logger.info("MongoDB client initialized (timezone-aware UTC)")
    return _client


def get_database() -> Database:
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client.get_database()
        logger.info(f"Connected to database: {_db.name}")
    return _db


def get_collection(name: str):
    logger.debug(f"Accessing collection: {name}")
    db = get_database()
    return db[name]


# Collection names
CHUNKS_COLLECTION = "chunks"
EXPERIMENTS_COLLECTION = "experiments"
RUN_STATUS_COLLECTION = "run_status"
COLLECTIONS_COLLECTION = "collections"
QUERIES_COLLECTION = "queries"
RESULTS_COLLECTION = "results"
