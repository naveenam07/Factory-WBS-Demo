import time

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from app.config import Settings
from app.logging_utils import get_logger
from app.repositories.mongo import MongoSeedStore, ensure_indexes
from app.services.seed import seed_if_needed

logger = get_logger("db")


def create_database(settings: Settings) -> Database:
    client: MongoClient = MongoClient(
        settings.mongo_url,
        connect=False,
        serverSelectionTimeoutMS=5000,
        appname="trading-app",
    )
    return client[settings.mongo_db]


def initialize_database(db: Database, attempts: int = 30, retry_seconds: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            ensure_indexes(db)
            seed_if_needed(MongoSeedStore(db))
            return
        except ConnectionFailure as exc:
            if attempt == attempts:
                raise
            logger.warning(
                "Database not ready (attempt %d/%d): %s", attempt, attempts, type(exc).__name__
            )
            time.sleep(retry_seconds)
