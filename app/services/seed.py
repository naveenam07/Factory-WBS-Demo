import random
from dataclasses import dataclass
from typing import Any

from app.logging_utils import get_logger
from app.repositories.base import SeedStore
from app.services.seed_data import (
    ACCOUNT_TYPES,
    ACCOUNTS_PER_ADVISOR,
    ADVISOR_NAMES,
    BASE_PRICES,
    CLIENT_FIRST_NAMES,
    CLIENT_LAST_NAMES,
    POSITIONS_PER_ACCOUNT,
    UNTYPED_ACCOUNT_ADVISOR,
    UNTYPED_ACCOUNT_SLOTS,
)

SEED_VERSION = 1
RANDOM_SEED = 20261113

logger = get_logger("seed")


@dataclass(frozen=True)
class SeedData:
    advisors: list[dict[str, Any]]
    accounts: list[dict[str, Any]]
    positions: list[dict[str, Any]]
    prices: list[dict[str, Any]]


def _fake_ssn(rng: random.Random) -> str:
    return f"9{rng.randint(0, 99):02d}-{rng.randint(1, 99):02d}-{rng.randint(1, 9999):04d}"


def build_seed_data() -> SeedData:
    """Build the synthetic dataset. Deterministic, so every replica produces identical rows."""
    rng = random.Random(RANDOM_SEED)
    symbols = sorted(BASE_PRICES)
    prices = [{"symbol": symbol, "price": BASE_PRICES[symbol]} for symbol in symbols]

    advisors: list[dict[str, Any]] = []
    accounts: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    used_numbers: set[str] = set()
    account_seq = 0

    for index, name in enumerate(ADVISOR_NAMES):
        advisor_id = f"A-{1001 + index}"
        advisors.append({"advisor_id": advisor_id, "name": name})
        for slot in range(ACCOUNTS_PER_ADVISOR):
            account_seq += 1
            account_id = f"ACC-{account_seq:06d}"
            account_number = str(rng.randint(10**9, 10**10 - 1))
            while account_number in used_numbers:
                account_number = str(rng.randint(10**9, 10**10 - 1))
            used_numbers.add(account_number)

            account_type: str | None = ACCOUNT_TYPES[account_seq % len(ACCOUNT_TYPES)]
            if advisor_id == UNTYPED_ACCOUNT_ADVISOR and slot in UNTYPED_ACCOUNT_SLOTS:
                account_type = None

            client_name = f"{rng.choice(CLIENT_FIRST_NAMES)} {rng.choice(CLIENT_LAST_NAMES)}"
            accounts.append(
                {
                    "account_id": account_id,
                    "advisor_id": advisor_id,
                    "client_name": client_name,
                    "account_type": account_type,
                    "account_number": account_number,
                    "last4": account_number[-4:],
                    "client_ssn": _fake_ssn(rng),
                    "cash_balance": round(rng.uniform(5_000, 250_000), 2),
                }
            )
            for symbol in sorted(rng.sample(symbols, POSITIONS_PER_ACCOUNT)):
                positions.append(
                    {
                        "account_id": account_id,
                        "symbol": symbol,
                        "quantity": rng.randint(5, 400),
                        "cost_basis": round(BASE_PRICES[symbol] * rng.uniform(0.6, 1.15), 2),
                    }
                )

    return SeedData(advisors=advisors, accounts=accounts, positions=positions, prices=prices)


def seed_if_needed(store: SeedStore) -> bool:
    if store.is_seeded():
        return False
    data = build_seed_data()
    inserted = {
        "prices": store.insert_missing("prices", data.prices),
        "advisors": store.insert_missing("advisors", data.advisors),
        "accounts": store.insert_missing("accounts", data.accounts),
        "positions": store.insert_missing("positions", data.positions),
    }
    store.mark_seeded(SEED_VERSION)
    summary = ", ".join(f"{count} {name}" for name, count in inserted.items())
    logger.info("Seeded database: %s", summary)
    return True
