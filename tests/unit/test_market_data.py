import json
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from app.repositories.base import Repositories
from app.services.market_data import MarketDataClient


class _QuoteHandler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, bytes, float]] = {}
    seen: list[dict] = []

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        self.seen.append(
            {"path": parsed.path, "query": parse_qs(parsed.query), "headers": dict(self.headers)}
        )
        status, body, delay = self.routes.get(parsed.path, (404, b"{}", 0.0))
        if delay:
            time.sleep(delay)
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def quote_server() -> Iterator[tuple[str, type[_QuoteHandler]]]:
    handler = type("Handler", (_QuoteHandler,), {"routes": {}, "seen": []})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", handler
    finally:
        server.shutdown()
        server.server_close()


def _json(payload: object) -> bytes:
    return json.dumps(payload).encode()


def test_disabled_without_base_url() -> None:
    client = MarketDataClient(None)

    assert client.enabled is False
    assert client.fetch_quotes(["AAPL"]) == {}


def test_empty_symbols_skip_the_request(quote_server) -> None:
    base_url, handler = quote_server
    client = MarketDataClient(base_url)

    assert client.fetch_quotes([]) == {}
    assert handler.seen == []


def test_default_session_is_a_requests_session() -> None:
    client = MarketDataClient("http://127.0.0.1:1/")

    assert isinstance(client._session, requests.Session)
    assert client._base_url == "http://127.0.0.1:1"


def test_fetch_quotes_parses_payload_and_sends_sorted_unique_symbols(quote_server) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (
        200,
        _json(
            {
                "quotes": [
                    {"symbol": "aapl", "price": "201.5"},
                    {"symbol": "MSFT", "price": 402},
                    {"symbol": "BAD", "price": "not-a-number"},
                    {"symbol": "NOPRICE"},
                    {"symbol": "NULL", "price": None},
                ]
            }
        ),
        0.0,
    )
    client = MarketDataClient(base_url + "/")

    quotes = client.fetch_quotes(["MSFT", "AAPL", "MSFT"])

    assert quotes == {"AAPL": 201.5, "MSFT": 402.0}
    assert len(handler.seen) == 1
    assert handler.seen[0]["path"] == "/quotes"
    assert handler.seen[0]["query"] == {"symbols": ["AAPL,MSFT"]}


def test_missing_quotes_key_returns_empty(quote_server) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (200, _json({}), 0.0)

    assert MarketDataClient(base_url).fetch_quotes(["AAPL"]) == {}


@pytest.mark.parametrize("status", [404, 500, 503])
def test_http_error_status_returns_empty(quote_server, status, caplog) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (status, _json({"quotes": [{"symbol": "AAPL", "price": 1}]}), 0.0)

    assert MarketDataClient(base_url).fetch_quotes(["AAPL"]) == {}
    assert "HTTPError" in caplog.text


def test_invalid_json_returns_empty(quote_server, caplog) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (200, b"<html>not json</html>", 0.0)

    assert MarketDataClient(base_url).fetch_quotes(["AAPL"]) == {}
    assert "Market data refresh failed" in caplog.text


def test_timeout_returns_empty(quote_server, caplog) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (200, _json({"quotes": []}), 1.0)

    assert MarketDataClient(base_url, timeout=0.1).fetch_quotes(["AAPL"]) == {}
    assert "Timeout" in caplog.text


def test_connection_error_returns_empty(caplog) -> None:
    with ThreadingHTTPServer(("127.0.0.1", 0), _QuoteHandler) as server:
        port = server.server_address[1]

    assert MarketDataClient(f"http://127.0.0.1:{port}").fetch_quotes(["AAPL"]) == {}
    assert "ConnectionError" in caplog.text


def test_refresh_upserts_fetched_prices(quote_server, repositories: Repositories) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (
        200,
        _json({"quotes": [{"symbol": "AAPL", "price": 210.25}, {"symbol": "TSLA", "price": 99}]}),
        0.0,
    )

    updated = MarketDataClient(base_url).refresh(["AAPL", "TSLA"], repositories.prices)

    assert updated == 2
    assert repositories.prices.get_price("AAPL") == 210.25
    assert repositories.prices.get_price("TSLA") == 99.0


def test_refresh_leaves_prices_unchanged_on_failure(
    quote_server, repositories: Repositories
) -> None:
    base_url, handler = quote_server
    handler.routes["/quotes"] = (500, b"{}", 0.0)

    updated = MarketDataClient(base_url).refresh(["AAPL"], repositories.prices)

    assert updated == 0
    assert repositories.prices.get_price("AAPL") == 200.0
