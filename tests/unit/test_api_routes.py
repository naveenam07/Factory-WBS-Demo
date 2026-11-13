import json
import re
from pathlib import Path

import pytest

import app as app_package

ROUTES_FILE = Path(app_package.__file__).resolve().parent / "static" / "api-routes.json"
PORTAL_ROUTES: dict[str, str] = json.loads(ROUTES_FILE.read_text())


def _shape(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


@pytest.fixture
def api_paths(app_client) -> set[str]:
    return {_shape(path) for path in app_client.app.openapi()["paths"]}


@pytest.mark.parametrize(("name", "path"), sorted(PORTAL_ROUTES.items()))
def test_every_portal_route_matches_a_fastapi_route(name: str, path: str, api_paths) -> None:
    assert _shape(path) in api_paths, f"api-routes.json '{name}' -> {path} has no FastAPI route"


def test_portal_transfers_route_books_a_transfer(app_client) -> None:
    response = app_client.post(
        PORTAL_ROUTES["transfers"],
        json={
            "advisor_id": "A-1001",
            "from_account_id": "ACC-000001",
            "to_account_id": "ACC-000002",
            "amount": 500,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "completed"


def test_wrong_transfer_route_version_returns_404(app_client) -> None:
    response = app_client.post(
        "/api/v2/transfers",
        json={
            "advisor_id": "A-1001",
            "from_account_id": "ACC-000001",
            "to_account_id": "ACC-000002",
            "amount": 500,
        },
    )

    assert response.status_code == 404
    assert response.json()["message"] == "No route matches POST /api/v2/transfers"
