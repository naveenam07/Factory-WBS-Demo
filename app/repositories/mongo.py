from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import BulkWriteError

from app.models import Account, Advisor, Position
from app.repositories.base import Repositories

DUPLICATE_KEY_ERROR = 11000
SEED_MARKER_ID = "seed"


def ensure_indexes(db: Database) -> None:
    db["advisors"].create_index([("advisor_id", ASCENDING)], unique=True)
    db["accounts"].create_index([("account_id", ASCENDING)], unique=True)
    db["accounts"].create_index([("advisor_id", ASCENDING)])
    db["positions"].create_index([("account_id", ASCENDING), ("symbol", ASCENDING)], unique=True)
    db["prices"].create_index([("symbol", ASCENDING)], unique=True)
    db["orders"].create_index([("confirmation_number", ASCENDING)], unique=True)
    db["transfers"].create_index([("confirmation_number", ASCENDING)], unique=True)


class MongoAdvisorRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["advisors"]

    def get(self, advisor_id: str) -> Advisor | None:
        doc = self._collection.find_one({"advisor_id": advisor_id})
        return Advisor.model_validate(doc) if doc else None

    def list_all(self) -> list[Advisor]:
        return [
            Advisor.model_validate(doc)
            for doc in self._collection.find().sort("advisor_id", ASCENDING)
        ]


class MongoAccountRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["accounts"]

    def get(self, account_id: str) -> Account | None:
        doc = self._collection.find_one({"account_id": account_id})
        return Account.model_validate(doc) if doc else None

    def list_for_advisor(self, advisor_id: str) -> list[Account]:
        cursor = self._collection.find({"advisor_id": advisor_id}).sort("account_id", ASCENDING)
        return [Account.model_validate(doc) for doc in cursor]

    def adjust_balance(self, account_id: str, delta: float) -> float:
        doc = self._collection.find_one_and_update(
            {"account_id": account_id},
            {"$inc": {"cash_balance": delta}},
            return_document=ReturnDocument.AFTER,
        )
        return round(doc["cash_balance"], 2)


class MongoPositionRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["positions"]

    def list_for_account(self, account_id: str) -> list[Position]:
        cursor = self._collection.find({"account_id": account_id}).sort("symbol", ASCENDING)
        return [Position.model_validate(doc) for doc in cursor]


class MongoPriceRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["prices"]

    def get_price(self, symbol: str) -> float | None:
        doc = self._collection.find_one({"symbol": symbol})
        return float(doc["price"]) if doc else None

    def upsert_price(self, symbol: str, price: float) -> None:
        self._collection.update_one(
            {"symbol": symbol},
            {"$set": {"price": price, "updated_at": datetime.now(UTC)}},
            upsert=True,
        )


class MongoOrderRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["orders"]

    def insert(self, order: dict[str, Any]) -> None:
        self._collection.insert_one(dict(order))


class MongoTransferRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["transfers"]

    def insert(self, transfer: dict[str, Any]) -> None:
        self._collection.insert_one(dict(transfer))


class MongoSeedStore:
    """Idempotent bulk loader; safe when several replicas seed the same database at once."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def is_seeded(self) -> bool:
        return self._db["meta"].find_one({"_id": SEED_MARKER_ID}) is not None

    def insert_missing(self, collection: str, documents: list[dict[str, Any]]) -> int:
        if not documents:
            return 0
        try:
            result = self._db[collection].insert_many(
                [dict(doc) for doc in documents], ordered=False
            )
            return len(result.inserted_ids)
        except BulkWriteError as exc:
            errors = exc.details.get("writeErrors", [])
            if any(error.get("code") != DUPLICATE_KEY_ERROR for error in errors):
                raise
            return int(exc.details.get("nInserted", 0))

    def mark_seeded(self, version: int) -> None:
        self._db["meta"].update_one(
            {"_id": SEED_MARKER_ID},
            {"$setOnInsert": {"version": version, "completed_at": datetime.now(UTC)}},
            upsert=True,
        )


def build_repositories(db: Database) -> Repositories:
    return Repositories(
        advisors=MongoAdvisorRepository(db),
        accounts=MongoAccountRepository(db),
        positions=MongoPositionRepository(db),
        prices=MongoPriceRepository(db),
        orders=MongoOrderRepository(db),
        transfers=MongoTransferRepository(db),
    )
