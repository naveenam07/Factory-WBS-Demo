import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.errors import NotFoundError
from app.repositories.base import Repositories

BOOKING_CODES = {"INDIVIDUAL": "IND", "JOINT": "JNT", "IRA": "IRA", "TRUST": "TRS"}


@dataclass(frozen=True)
class OrderTicket:
    advisor_id: str
    account_id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int


@dataclass(frozen=True)
class OrderConfirmation:
    confirmation_number: str
    status: str
    account_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    estimated_value: float


class OrderService:
    def __init__(self, repositories: Repositories) -> None:
        self._repos = repositories

    def place(self, ticket: OrderTicket, trace_id: str | None = None) -> OrderConfirmation:
        account = self._repos.accounts.get(ticket.account_id)
        if account is None:
            raise NotFoundError(f"Account {ticket.account_id} not found")

        symbol = ticket.symbol.upper()
        price = self._repos.prices.get_price(symbol)
        if price is None:
            raise NotFoundError(f"Symbol {symbol} not found")

        booking_code = BOOKING_CODES[account.account_type.upper()]

        confirmation = OrderConfirmation(
            confirmation_number=f"ORD-{secrets.token_hex(5).upper()}",
            status="accepted",
            account_id=account.account_id,
            symbol=symbol,
            side=ticket.side,
            quantity=ticket.quantity,
            price=price,
            estimated_value=round(price * ticket.quantity, 2),
        )
        self._repos.orders.insert(
            {
                **confirmation.__dict__,
                "advisor_id": ticket.advisor_id,
                "booking_code": booking_code,
                "trace_id": trace_id,
                "created_at": datetime.now(UTC),
            }
        )
        return confirmation
