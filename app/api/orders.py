from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import RepositoriesDep
from app.api.schemas import OrderRequest, OrderResponse
from app.logging_utils import bind_advisor_id, current_trace_id
from app.services.orders import OrderService, OrderTicket

router = APIRouter(prefix="/api/v1", tags=["orders"])


def get_order_service(repositories: RepositoriesDep) -> OrderService:
    return OrderService(repositories)


@router.post("/orders", response_model=OrderResponse, status_code=201)
def place_order(
    body: OrderRequest,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    bind_advisor_id(body.advisor_id)
    trace_id = current_trace_id()
    confirmation = service.place(OrderTicket(**body.model_dump()), trace_id=trace_id)
    return OrderResponse(**confirmation.__dict__, trace_id=trace_id)
