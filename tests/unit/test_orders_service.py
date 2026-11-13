from app.repositories.base import Repositories
from app.services.orders import OrderService, OrderTicket


def test_place_buy_order_for_typed_account(repositories: Repositories, database) -> None:
    service = OrderService(repositories)

    confirmation = service.place(
        OrderTicket(
            advisor_id="A-1001", account_id="ACC-000001", symbol="aapl", side="buy", quantity=5
        ),
        trace_id="trace-123",
    )

    assert confirmation.confirmation_number.startswith("ORD-")
    assert confirmation.status == "accepted"
    assert confirmation.symbol == "AAPL"
    assert confirmation.estimated_value == 1000.0
    stored = database["orders"].find_one({"confirmation_number": confirmation.confirmation_number})
    assert stored["trace_id"] == "trace-123"
