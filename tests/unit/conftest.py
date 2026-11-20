import logging
from collections.abc import Iterator

import mongomock
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pymongo.database import Database

from app.config import Settings
from app.logging_utils import LOGGER_NAME, JsonFormatter
from app.main import create_app
from app.repositories.base import Repositories
from app.repositories.mongo import build_repositories, ensure_indexes

ADVISORS = [
    {"advisor_id": "A-1001", "name": "Test Advisor One"},
    {"advisor_id": "A-1002", "name": "Test Advisor Two"},
]

ACCOUNTS = [
    {
        "account_id": f"ACC-00000{n}",
        "advisor_id": "A-1001" if n <= 3 else "A-1002",
        "client_name": f"Client {n}",
        "account_type": account_type,
        "account_number": f"90000000{n:02d}",
        "last4": f"00{n:02d}",
        "client_ssn": f"900-00-000{n}",
        "cash_balance": 10_000.0 * n,
    }
    for n, account_type in enumerate(["individual", "joint", "ira", "trust"], start=1)
]

POSITIONS = [
    {"account_id": "ACC-000001", "symbol": "AAPL", "quantity": 10, "cost_basis": 150.0},
    {"account_id": "ACC-000001", "symbol": "MSFT", "quantity": 4, "cost_basis": 300.0},
]

PRICES = [{"symbol": "AAPL", "price": 200.0}, {"symbol": "MSFT", "price": 400.0}]


@pytest.fixture
def database() -> Database:
    db = mongomock.MongoClient()["wavebank_test"]
    ensure_indexes(db)
    for name, docs in (
        ("advisors", ADVISORS),
        ("accounts", ACCOUNTS),
        ("positions", POSITIONS),
        ("prices", PRICES),
    ):
        db[name].insert_many([dict(doc) for doc in docs])
    return db


@pytest.fixture
def repositories(database: Database) -> Repositories:
    return build_repositories(database)


@pytest.fixture
def make_client(repositories: Repositories) -> Iterator:
    clients: list[TestClient] = []

    def _make(*routers: APIRouter) -> TestClient:
        app = FastAPI()
        app.state.repositories = repositories
        for router in routers:
            app.include_router(router)
        client = TestClient(app)
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.close()

@pytest.fixture
def app_client(database: Database) -> Iterator[TestClient]:
    settings = Settings(
        mongo_url="mongodb://unused",
        mongo_db="wavebank_test",
        market_data_url=None,
        market_data_timeout=1.0,
        startup_attempts=1,
        startup_retry_seconds=0.0,
    )
    # No context manager: the lifespan would try to seed a real MongoDB.
    client = TestClient(create_app(database=database, settings=settings))
    yield client
    client.close()


@pytest.fixture
def app_logs(app_client: TestClient) -> Iterator[list[str]]:
    lines: list[str] = []

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(self.format(record))

    handler = _Collect()
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger(LOGGER_NAME)
    app_logger.addHandler(handler)
    yield lines
    app_logger.removeHandler(handler)
