import requests

from app.logging_utils import get_logger
from app.repositories.base import PriceRepository

logger = get_logger("market_data")


class MarketDataClient:
    """Optional quote refresh from an external price feed (enabled by MARKET_DATA_URL)."""

    def __init__(
        self,
        base_url: str | None,
        timeout: float = 2.0,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._timeout = timeout
        self._session = session or requests.Session()

    @property
    def enabled(self) -> bool:
        return self._base_url is not None

    def fetch_quotes(self, symbols: list[str]) -> dict[str, float]:
        if not self.enabled or not symbols:
            return {}
        try:
            response = self._session.get(
                f"{self._base_url}/quotes",
                params={"symbols": ",".join(sorted(set(symbols)))},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Market data refresh failed: %s", type(exc).__name__)
            return {}

        quotes: dict[str, float] = {}
        for item in payload.get("quotes", []):
            try:
                quotes[str(item["symbol"]).upper()] = float(item["price"])
            except (KeyError, TypeError, ValueError):
                continue
        return quotes

    def refresh(self, symbols: list[str], prices: PriceRepository) -> int:
        quotes = self.fetch_quotes(symbols)
        for symbol, price in quotes.items():
            prices.upsert_price(symbol, price)
        return len(quotes)
