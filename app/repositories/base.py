from dataclasses import dataclass
from typing import Any, Protocol

from app.models import Account, Advisor, Position


class AdvisorRepository(Protocol):
    def get(self, advisor_id: str) -> Advisor | None: ...

    def list_all(self) -> list[Advisor]: ...


class AccountRepository(Protocol):
    def get(self, account_id: str) -> Account | None: ...

    def list_for_advisor(self, advisor_id: str) -> list[Account]: ...

    def adjust_balance(self, account_id: str, delta: float) -> float: ...


class PositionRepository(Protocol):
    def list_for_account(self, account_id: str) -> list[Position]: ...


class PriceRepository(Protocol):
    def get_price(self, symbol: str) -> float | None: ...

    def upsert_price(self, symbol: str, price: float) -> None: ...


class OrderRepository(Protocol):
    def insert(self, order: dict[str, Any]) -> None: ...


class TransferRepository(Protocol):
    def insert(self, transfer: dict[str, Any]) -> None: ...


class SeedStore(Protocol):
    def is_seeded(self) -> bool: ...

    def insert_missing(self, collection: str, documents: list[dict[str, Any]]) -> int: ...

    def mark_seeded(self, version: int) -> None: ...


@dataclass(frozen=True)
class Repositories:
    advisors: AdvisorRepository
    accounts: AccountRepository
    positions: PositionRepository
    prices: PriceRepository
    orders: OrderRepository
    transfers: TransferRepository
