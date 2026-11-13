from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.logging_utils import SERVICE_NAME, current_trace_id

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME, trace_id=current_trace_id())
