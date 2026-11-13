import pytest

from app.errors import ForbiddenError, InsufficientFundsError, NotFoundError
from app.repositories.base import Repositories
from app.services.transfers import TransferInstruction, TransferService


def _instruction(**overrides) -> TransferInstruction:
    values = {
        "advisor_id": "A-1001",
        "from_account_id": "ACC-000001",
        "to_account_id": "ACC-000002",
        "amount": 500,
    }
    return TransferInstruction(**{**values, **overrides})


def _balance(database, account_id: str) -> float:
    return database["accounts"].find_one({"account_id": account_id})["cash_balance"]


def test_transfer_moves_cash_between_accounts(repositories: Repositories, database) -> None:
    service = TransferService(repositories)

    result = service.transfer(_instruction(), trace_id="trace-456")

    assert result.confirmation_number.startswith("TRF-")
    assert result.source_balance == 9_500.0
    assert result.destination_balance == 20_500.0
    stored = database["transfers"].find_one({"confirmation_number": result.confirmation_number})
    assert stored["trace_id"] == "trace-456"


def test_transfer_of_entire_balance_is_allowed(repositories: Repositories, database) -> None:
    result = TransferService(repositories).transfer(_instruction(amount=10_000))

    assert result.source_balance == 0.0
    assert _balance(database, "ACC-000001") == 0.0


@pytest.mark.parametrize("field", ["from_account_id", "to_account_id"])
def test_unknown_account_raises_not_found(repositories: Repositories, database, field) -> None:
    with pytest.raises(NotFoundError, match="Account ACC-999999 not found"):
        TransferService(repositories).transfer(_instruction(**{field: "ACC-999999"}))

    assert _balance(database, "ACC-000001") == 10_000.0
    assert database["transfers"].count_documents({}) == 0


@pytest.mark.parametrize("field", ["from_account_id", "to_account_id"])
def test_account_of_another_advisor_is_forbidden(
    repositories: Repositories, database, field
) -> None:
    with pytest.raises(ForbiddenError, match="ACC-000004 is not assigned to advisor A-1001"):
        TransferService(repositories).transfer(_instruction(**{field: "ACC-000004"}))

    assert _balance(database, "ACC-000001") == 10_000.0
    assert _balance(database, "ACC-000004") == 40_000.0
    assert database["transfers"].count_documents({}) == 0


def test_unknown_advisor_is_forbidden(repositories: Repositories, database) -> None:
    with pytest.raises(ForbiddenError):
        TransferService(repositories).transfer(_instruction(advisor_id="A-9999"))

    assert database["transfers"].count_documents({}) == 0


def test_insufficient_funds_moves_nothing(repositories: Repositories, database) -> None:
    with pytest.raises(InsufficientFundsError, match="Insufficient funds in account ACC-000001"):
        TransferService(repositories).transfer(_instruction(amount=10_000.01))

    assert _balance(database, "ACC-000001") == 10_000.0
    assert _balance(database, "ACC-000002") == 20_000.0
    assert database["transfers"].count_documents({}) == 0
