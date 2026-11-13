import time

from app.repositories.base import PriceRepository

QUOTE_INTERVAL_SECONDS = 0.3


class PricingService:
    def __init__(self, prices: PriceRepository) -> None:
        self._prices = prices

    def quote(self, symbol: str) -> float | None:
        time.sleep(QUOTE_INTERVAL_SECONDS)
        return self._prices.get_price(symbol)
