from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio.to_thread
from fastapi import FastAPI
from pymongo.database import Database

from app.api import accounts, health, orders, positions, transfers
from app.config import Settings, load_settings
from app.db import create_database, initialize_database
from app.error_handlers import register_error_handlers
from app.logging_utils import configure_logging
from app.middleware import RequestContextMiddleware
from app.repositories.mongo import build_repositories
from app.services.market_data import MarketDataClient


def create_app(database: Database | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging()
    db = database if database is not None else create_database(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await anyio.to_thread.run_sync(
            initialize_database, db, settings.startup_attempts, settings.startup_retry_seconds
        )
        yield

    app = FastAPI(title="WaveBank Advisor Trading API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = db
    app.state.repositories = build_repositories(db)
    app.state.market_data = MarketDataClient(
        settings.market_data_url, timeout=settings.market_data_timeout
    )

    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    for module in (health, accounts, positions, orders, transfers):
        app.include_router(module.router)
    return app


app = create_app()
