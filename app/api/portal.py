from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import RepositoriesDep

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def advisor_picker(request: Request, repositories: RepositoriesDep) -> HTMLResponse:
    advisors = repositories.advisors.list_all()
    return templates.TemplateResponse(request, "advisors.html", {"advisors": advisors})


@router.get("/advisors/{advisor_id}", response_class=HTMLResponse)
def client_list(request: Request, advisor_id: str) -> HTMLResponse:
    return templates.TemplateResponse(request, "clients.html", {"advisor_id": advisor_id})


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
def account_page(request: Request, account_id: str, advisor_id: str = "") -> HTMLResponse:
    context = {"account_id": account_id, "advisor_id": advisor_id}
    return templates.TemplateResponse(request, "account.html", context)
