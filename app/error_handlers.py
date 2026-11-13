from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError
from app.logging_utils import bind_advisor_id, current_trace_id


def error_response(
    status: int,
    message: str,
    trace_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"status": status, "message": message, "trace_id": trace_id or current_trace_id()},
        headers=headers,
    )


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors()[:3]:
        location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
        parts.append(f"{location}: {error.get('msg')}" if location else str(error.get("msg")))
    return "Invalid request: " + "; ".join(parts)


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404 and exc.detail == "Not Found":
        message = f"No route matches {request.method} {request.url.path}"
        try:
            body = await request.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            bind_advisor_id(body.get("advisor_id"))
    elif isinstance(exc.detail, str) and exc.detail:
        message = exc.detail
    else:
        message = HTTPStatus(exc.status_code).phrase
    return error_response(exc.status_code, message, headers=getattr(exc, "headers", None))


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    if isinstance(exc.body, dict):
        bind_advisor_id(exc.body.get("advisor_id"))
    return error_response(422, _validation_message(exc))


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.message)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(AppError, handle_app_error)
