from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import MarketDataDep, RepositoriesDep
from app.api.schemas import PositionOut, PositionsResponse
from app.logging_utils import bind_advisor_id, current_trace_id
from app.services.positions import PositionsService
from app.services.pricing import PricingService

router = APIRouter(prefix="/api/v1", tags=["positions"])


def get_positions_service(
    repositories: RepositoriesDep, market_data: MarketDataDep
) -> PositionsService:
    return PositionsService(repositories, PricingService(repositories.prices), market_data)


@router.get("/accounts/{account_id}/positions", response_model=PositionsResponse)
def get_account_positions(
    account_id: str,
    service: Annotated[PositionsService, Depends(get_positions_service)],
) -> PositionsResponse:
    result = service.for_account(account_id)
    bind_advisor_id(result.account.advisor_id)
    return PositionsResponse(
        account_id=result.account.account_id,
        advisor_id=result.account.advisor_id,
        positions=[PositionOut.model_validate(p) for p in result.positions],
        total_market_value=result.total_market_value,
        trace_id=current_trace_id(),
    )
