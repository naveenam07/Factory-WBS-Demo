from fastapi import APIRouter

from app.api.deps import RepositoriesDep
from app.api.schemas import AccountOut, AdvisorAccountsResponse, AdvisorOut, AdvisorsResponse
from app.errors import NotFoundError
from app.logging_utils import current_trace_id

router = APIRouter(prefix="/api/v1", tags=["accounts"])


@router.get("/advisors", response_model=AdvisorsResponse)
def list_advisors(repositories: RepositoriesDep) -> AdvisorsResponse:
    advisors = [AdvisorOut.model_validate(a) for a in repositories.advisors.list_all()]
    return AdvisorsResponse(advisors=advisors, trace_id=current_trace_id())


@router.get("/advisors/{advisor_id}/accounts", response_model=AdvisorAccountsResponse)
def list_advisor_accounts(
    advisor_id: str, repositories: RepositoriesDep
) -> AdvisorAccountsResponse:
    advisor = repositories.advisors.get(advisor_id)
    if advisor is None:
        raise NotFoundError(f"Advisor {advisor_id} not found")
    accounts = [
        AccountOut.model_validate(account)
        for account in repositories.accounts.list_for_advisor(advisor_id)
    ]
    return AdvisorAccountsResponse(
        advisor_id=advisor.advisor_id,
        advisor_name=advisor.name,
        accounts=accounts,
        trace_id=current_trace_id(),
    )
