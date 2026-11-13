from app.api import accounts


def test_list_accounts_for_advisor(make_client) -> None:
    client = make_client(accounts.router)

    response = client.get("/api/v1/advisors/A-1001/accounts")

    assert response.status_code == 200
    body = response.json()
    assert body["advisor_id"] == "A-1001"
    assert [a["account_id"] for a in body["accounts"]] == ["ACC-000001", "ACC-000002", "ACC-000003"]
    assert all(a["advisor_id"] == "A-1001" for a in body["accounts"])
    assert "account_number" not in response.text
    assert "client_ssn" not in response.text


def test_list_advisors(make_client) -> None:
    client = make_client(accounts.router)

    response = client.get("/api/v1/advisors")

    assert response.status_code == 200
    assert [a["advisor_id"] for a in response.json()["advisors"]] == ["A-1001", "A-1002"]
