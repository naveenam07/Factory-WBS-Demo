import os
import re
from pathlib import Path

from playwright.sync_api import Page, expect

BASE_URL = os.getenv("WAVEBANK_URL", "http://localhost:30080")
SCREENSHOTS = Path(__file__).resolve().parent / "screenshots"


def screenshot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(exist_ok=True)
    page.screenshot(path=SCREENSHOTS / f"{name}.png", full_page=True)


def test_advisor_smoke(page: Page) -> None:
    page.goto(f"{BASE_URL}/")
    expect(page.get_by_role("heading", name="Choose an advisor")).to_be_visible()
    screenshot(page, "01-advisor-picker")

    page.get_by_role("link", name="A-1001").click()
    expect(page.locator("#client-rows tr.clickable")).to_have_count(10)
    screenshot(page, "02-client-list")

    page.locator("#client-rows a").first.click()
    expect(page.locator("#positions-rows tr")).to_have_count(10, timeout=15_000)
    screenshot(page, "03-account")

    banner = page.locator("#banner")
    page.locator("#trade-form input[name=symbol]").fill("AAPL")
    page.locator("#trade-form input[name=quantity]").fill("5")
    page.get_by_role("button", name="Place trade").click()
    expect(banner).to_contain_text("Trade placed")
    expect(banner).to_have_class(re.compile("banner-success"))
    screenshot(page, "04-trade-placed")

    page.locator("#transfer-form input[name=amount]").fill("500")
    with page.expect_response(
        lambda r: r.request.method == "POST" and "/transfers" in r.url
    ) as transfer:
        page.get_by_role("button", name="Move money").click()
    expect(banner).not_to_contain_text("Trade placed")
    screenshot(page, "05-move-money")
    assert transfer.value.status == 201, f"{transfer.value.url} returned {transfer.value.status}"
    expect(banner).to_contain_text("Money moved")
    expect(banner).to_have_class(re.compile("banner-success"))


def test_portal_route_map_matches_live_api(page: Page) -> None:
    routes = page.request.get(f"{BASE_URL}/static/api-routes.json").json()
    live_paths = page.request.get(f"{BASE_URL}/openapi.json").json()["paths"]

    missing = {name: path for name, path in routes.items() if path not in live_paths}
    assert not missing, f"api-routes.json entries with no live API route: {missing}"
