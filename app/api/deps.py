from typing import Annotated

from fastapi import Depends, Request

from app.repositories.base import Repositories
from app.services.market_data import MarketDataClient


def get_repositories(request: Request) -> Repositories:
    return request.app.state.repositories


def get_market_data(request: Request) -> MarketDataClient:
    return request.app.state.market_data


RepositoriesDep = Annotated[Repositories, Depends(get_repositories)]
MarketDataDep = Annotated[MarketDataClient, Depends(get_market_data)]
