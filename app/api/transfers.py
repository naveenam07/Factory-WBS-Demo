from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import RepositoriesDep
from app.api.schemas import TransferRequest, TransferResponse
from app.logging_utils import bind_advisor_id, current_trace_id, get_logger
from app.services.transfers import TransferInstruction, TransferService

router = APIRouter(prefix="/api/v1", tags=["transfers"])


def get_transfer_service(repositories: RepositoriesDep) -> TransferService:
    return TransferService(repositories)


logger = get_logger("transfers")


@router.post("/transfers", response_model=TransferResponse, status_code=201)
def create_transfer(
    body: TransferRequest,
    service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferResponse:
    bind_advisor_id(body.advisor_id)
    trace_id = current_trace_id()
    result = service.transfer(TransferInstruction(**body.model_dump()), trace_id=trace_id)
    logger.info(
        "Transfer %s completed: $%.2f from account %s (%s, SSN %s) to account %s (%s, SSN %s)",
        result.confirmation_number,
        result.amount,
        result.source.account_number,
        result.source.client_name,
        result.source.client_ssn,
        result.destination.account_number,
        result.destination.client_name,
        result.destination.client_ssn,
    )
    return TransferResponse(
        confirmation_number=result.confirmation_number,
        status="completed",
        amount=result.amount,
        from_account_id=result.source.account_id,
        to_account_id=result.destination.account_id,
        from_cash_balance=result.source_balance,
        to_cash_balance=result.destination_balance,
        trace_id=trace_id,
    )
