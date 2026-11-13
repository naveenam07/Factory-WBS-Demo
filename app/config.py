import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongo_url: str
    mongo_db: str
    market_data_url: str | None
    market_data_timeout: float
    startup_attempts: int
    startup_retry_seconds: float


def load_settings() -> Settings:
    return Settings(
        mongo_url=os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"),
        mongo_db=os.getenv("MONGO_DB", "wavebank"),
        market_data_url=os.getenv("MARKET_DATA_URL") or None,
        market_data_timeout=float(os.getenv("MARKET_DATA_TIMEOUT", "2.0")),
        startup_attempts=int(os.getenv("DB_STARTUP_ATTEMPTS", "30")),
        startup_retry_seconds=float(os.getenv("DB_STARTUP_RETRY_SECONDS", "2.0")),
    )
