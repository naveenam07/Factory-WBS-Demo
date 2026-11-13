from app.repositories.base import Repositories
from app.services.transfers import TransferInstruction, TransferService


def test_transfer_moves_cash_between_accounts(repositories: Repositories, database) -> None:
    service = TransferService(repositories)

    result = service.transfer(
        TransferInstruction(
            advisor_id="A-1001",
            from_account_id="ACC-000001",
            to_account_id="ACC-000002",
            amount=500,
        ),
        trace_id="trace-456",
    )

    assert result.confirmation_number.startswith("TRF-")
    assert result.source_balance == 9_500.0
    assert result.destination_balance == 20_500.0
    stored = database["transfers"].find_one({"confirmation_number": result.confirmation_number})
    assert stored["trace_id"] == "trace-456"
