import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from app.errors import NotFoundError
from app.models import Account
from app.repositories.base import Repositories


@dataclass(frozen=True)
class TransferInstruction:
    advisor_id: str
    from_account_id: str
    to_account_id: str
    amount: float


@dataclass(frozen=True)
class TransferResult:
    confirmation_number: str
    amount: float
    source: Account
    destination: Account
    source_balance: float
    destination_balance: float


class TransferService:
    def __init__(self, repositories: Repositories) -> None:
        self._repos = repositories

    def _load(self, account_id: str) -> Account:
        account = self._repos.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")
        return account

    def transfer(
        self, instruction: TransferInstruction, trace_id: str | None = None
    ) -> TransferResult:
        amount = round(instruction.amount, 2)
        source = self._load(instruction.from_account_id)
        destination = self._load(instruction.to_account_id)

        source_balance = self._repos.accounts.adjust_balance(source.account_id, -amount)
        destination_balance = self._repos.accounts.adjust_balance(destination.account_id, amount)

        confirmation_number = f"TRF-{secrets.token_hex(5).upper()}"
        self._repos.transfers.insert(
            {
                "confirmation_number": confirmation_number,
                "advisor_id": instruction.advisor_id,
                "from_account_id": source.account_id,
                "to_account_id": destination.account_id,
                "amount": amount,
                "status": "completed",
                "trace_id": trace_id,
                "created_at": datetime.now(UTC),
            }
        )
        return TransferResult(
            confirmation_number=confirmation_number,
            amount=amount,
            source=source,
            destination=destination,
            source_balance=source_balance,
            destination_balance=destination_balance,
        )
