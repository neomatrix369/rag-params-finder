from pymongo import MongoClient
from pymongo.database import Database

from server.db.mongodb_uri import mongo_client_kwargs
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
            settings.mongodb_uri,
            **mongo_client_kwargs(settings.mongodb_uri),
        )
        logger.info("mongodb client ready — timezone-aware UTC")
    return _client


def get_database() -> Database:
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client.get_database()
        logger.info("database connected — name=%s", _db.name)
    return _db


def get_collection(name: str):
    logger.debug("collection access — name=%s", name)
    db = get_database()
    return db[name]


# Collection names
CHUNKS_COLLECTION = "chunks"
EXPERIMENTS_COLLECTION = "experiments"
RUN_STATUS_COLLECTION = "run_status"
COLLECTIONS_COLLECTION = "collections"
QUERIES_COLLECTION = "queries"
RESULTS_COLLECTION = "results"
