"""Security regression tests for the advisories fixed by the requests 2.34.2 pin."""

import io
import json

import pytest
import requests
from urllib3.connectionpool import HTTPSConnectionPool
from urllib3.response import HTTPResponse

from app.services.market_data import MarketDataClient

FEED_URL = "https://127.0.0.1:8443"


@pytest.fixture
def pool_requests(monkeypatch) -> list[tuple[HTTPSConnectionPool, str]]:
    """Record which HTTPS connection pool serves each request, without opening sockets."""
    seen: list[tuple[HTTPSConnectionPool, str]] = []

    def fake_urlopen(self, method, url, **kwargs) -> HTTPResponse:
        seen.append((self, self.cert_reqs))
        body = json.dumps({"quotes": [{"symbol": "AAPL", "price": 201.5}]}).encode()
        return HTTPResponse(
            body=io.BytesIO(body),
            headers={"Content-Type": "application/json"},
            status=200,
            reason="OK",
            preload_content=False,
        )

    def no_network(self, *args, **kwargs):
        raise AssertionError("security regression tests must not open network connections")

    monkeypatch.setattr(HTTPSConnectionPool, "urlopen", fake_urlopen)
    monkeypatch.setattr(HTTPSConnectionPool, "_new_conn", no_network)
    return seen


def test_cve_2024_35195_verify_false_does_not_carry_over_to_market_data_request(
    pool_requests,
) -> None:
    """CVE-2024-35195 / GHSA-9wx4-h78v-vm56 / PYSEC-2026-1873, fixed in requests 2.32.0."""
    session = requests.Session()
    session.trust_env = False
    client = MarketDataClient(FEED_URL, session=session)

    session.get(f"{FEED_URL}/health", verify=False)
    quotes = client.fetch_quotes(["AAPL"])

    assert quotes == {"AAPL": 201.5}
    (unverified_pool, unverified_reqs), (quote_pool, quote_reqs) = pool_requests
    assert unverified_reqs == "CERT_NONE"
    # Connections opened by the verify=False request stay alive in their pool and are reused
    # without a new TLS handshake, so the verified request must be served by a different pool.
    assert quote_pool is not unverified_pool
    assert quote_reqs == "CERT_REQUIRED"
