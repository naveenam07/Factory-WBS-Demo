from dataclasses import dataclass

from app.errors import NotFoundError
from app.models import Account, Position
from app.repositories.base import Repositories
from app.services.market_data import MarketDataClient
from app.services.pricing import PricingService


@dataclass(frozen=True)
class ValuedPosition:
    symbol: str
    quantity: int
    cost_basis: float
    price: float | None
    market_value: float | None


@dataclass(frozen=True)
class AccountPositions:
    account: Account
    positions: list[ValuedPosition]
    total_market_value: float


class PositionsService:
    def __init__(
        self,
        repositories: Repositories,
        pricing: PricingService,
        market_data: MarketDataClient,
    ) -> None:
        self._repos = repositories
        self._pricing = pricing
        self._market_data = market_data

    def for_account(self, account_id: str) -> AccountPositions:
        account = self._repos.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")

        holdings = self._repos.positions.list_for_account(account_id)
        if self._market_data.enabled:
            self._market_data.refresh([h.symbol for h in holdings], self._repos.prices)

        valued = [self._value(holding) for holding in holdings]
        total = round(sum(p.market_value or 0.0 for p in valued), 2)
        return AccountPositions(account=account, positions=valued, total_market_value=total)

    def _value(self, holding: Position) -> ValuedPosition:
        price = self._pricing.quote(holding.symbol)
        market_value = round(price * holding.quantity, 2) if price is not None else None
        return ValuedPosition(
            symbol=holding.symbol,
            quantity=holding.quantity,
            cost_basis=holding.cost_basis,
            price=price,
            market_value=market_value,
        )
