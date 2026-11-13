import json

import pytest

TRANSFER = {
    "advisor_id": "A-1001",
    "from_account_id": "ACC-000001",
    "to_account_id": "ACC-000002",
    "amount": 500,
}


def _post(client, **overrides):
    return client.post("/api/v1/transfers", json={**TRANSFER, **overrides})


def test_transfer_returns_confirmation_and_balances(app_client) -> None:
    response = _post(app_client)

    assert response.status_code == 201
    body = response.json()
    assert body["confirmation_number"].startswith("TRF-")
    assert body["from_cash_balance"] == 9_500.0
    assert body["to_cash_balance"] == 20_500.0
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_transfer_log_masks_account_numbers_and_omits_ssn_and_names(
    app_client, app_logs
) -> None:
    response = _post(app_client)

    assert response.status_code == 201
    logged = "\n".join(app_logs)
    for secret in ("9000000001", "9000000002", "900-00-0001", "900-00-0002"):
        assert secret not in logged
    for name in ("Client 1", "Client 2"):
        assert name not in logged
    messages = [json.loads(line)["message"] for line in app_logs]
    completed = [m for m in messages if m.startswith("Transfer TRF-")]
    assert len(completed) == 1
    assert "ACC-000001 (****0001)" in completed[0]
    assert "ACC-000002 (****0002)" in completed[0]


def test_unknown_account_returns_404(app_client) -> None:
    response = _post(app_client, to_account_id="ACC-999999")

    assert response.status_code == 404
    assert response.json()["message"] == "Account ACC-999999 not found"


@pytest.mark.parametrize("field", ["from_account_id", "to_account_id"])
def test_account_not_assigned_to_advisor_returns_403(app_client, database, field) -> None:
    response = _post(app_client, **{field: "ACC-000004"})

    assert response.status_code == 403
    assert response.json()["message"] == "Account ACC-000004 is not assigned to advisor A-1001"
    assert database["transfers"].count_documents({}) == 0


@pytest.mark.parametrize("amount", [10_000.01, 1e20, 1e308])
def test_insufficient_funds_returns_409_and_moves_nothing(app_client, database, amount) -> None:
    response = _post(app_client, amount=amount)

    assert response.status_code == 409
    assert response.json()["message"] == "Insufficient funds in account ACC-000001"
    assert database["accounts"].find_one({"account_id": "ACC-000001"})["cash_balance"] == 10_000.0
    assert database["accounts"].find_one({"account_id": "ACC-000002"})["cash_balance"] == 20_000.0


@pytest.mark.parametrize("field", ["advisor_id", "from_account_id", "to_account_id", "amount"])
def test_none_values_are_rejected_with_422(app_client, field) -> None:
    response = _post(app_client, **{field: None})

    assert response.status_code == 422
    assert field in response.json()["message"]


@pytest.mark.parametrize("amount", ["0", "-5", "Infinity", "-Infinity", "NaN"])
def test_invalid_amounts_are_rejected_with_422(app_client, database, amount) -> None:
    # Python's JSON parser accepts the non-standard Infinity and NaN literals.
    raw = json.dumps({**TRANSFER, "amount": 0}).replace('"amount": 0', f'"amount": {amount}')
    response = app_client.post(
        "/api/v1/transfers", content=raw, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert database["accounts"].find_one({"account_id": "ACC-000001"})["cash_balance"] == 10_000.0
