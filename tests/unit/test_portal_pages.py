from app.api import portal


def test_advisor_picker_links_to_each_advisor(make_client) -> None:
    client = make_client(portal.router)

    response = client.get("/")

    assert response.status_code == 200
    assert "WaveBank Advisor" in response.text
    assert 'href="/advisors/A-1001"' in response.text
    assert 'href="/advisors/A-1002"' in response.text


def test_client_list_page(make_client) -> None:
    client = make_client(portal.router)

    response = client.get("/advisors/A-1001")

    assert response.status_code == 200
    assert 'data-advisor-id="A-1001"' in response.text
    assert 'id="client-rows"' in response.text


def test_account_page_has_positions_and_forms(make_client) -> None:
    client = make_client(portal.router)

    response = client.get("/accounts/ACC-000001?advisor_id=A-1001")

    assert response.status_code == 200
    assert 'data-account-id="ACC-000001"' in response.text
    assert 'id="positions-rows"' in response.text
    assert 'id="trade-form"' in response.text
    assert 'id="transfer-form"' in response.text
