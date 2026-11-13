import logging
import re
import time

from starlette.datastructures import Headers, MutableHeaders, QueryParams
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.error_handlers import error_response
from app.logging_utils import (
    current_context,
    get_logger,
    reset_request_context,
    resolve_trace_id,
    start_request_context,
)

TRACE_HEADER = "X-Trace-Id"

_ADVISOR_IN_PATH = re.compile(r"/advisors/([A-Za-z0-9-]+)")

logger = get_logger("http")


def _advisor_from_scope(scope: Scope) -> str | None:
    match = _ADVISOR_IN_PATH.search(scope.get("path", ""))
    if match:
        return match.group(1)
    query = QueryParams(scope.get("query_string", b"").decode("latin-1"))
    return query.get("advisor_id") or None


def _level_for(status: int) -> int:
    if status >= 500:
        return logging.ERROR
    if status >= 400:
        return logging.WARNING
    return logging.INFO


class RequestContextMiddleware:
    """Assigns a trace id per request, echoes it in X-Trace-Id and logs one JSON line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = resolve_trace_id(Headers(scope=scope).get(TRACE_HEADER))
        method, path = scope["method"], scope["path"]
        token = start_request_context(trace_id, f"{method} {path}", _advisor_from_scope(scope))
        started = time.perf_counter()
        status = 500
        response_started = False
        failure: Exception | None = None

        async def send_with_trace(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                MutableHeaders(scope=message)[TRACE_HEADER] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        except Exception as exc:
            failure = exc
            if response_started:
                raise
            response = error_response(500, "Internal server error", trace_id)
            await response(scope, receive, send_with_trace)
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            ctx = current_context()
            extra = {
                "status": status,
                "latency_ms": latency_ms,
                "advisor_id": ctx.advisor_id if ctx else None,
            }
            if failure is not None:
                logger.error(
                    "%s: %s",
                    type(failure).__name__,
                    failure,
                    exc_info=(type(failure), failure, failure.__traceback__),
                    extra=extra,
                )
            else:
                logger.log(_level_for(status), "%s %s %s", method, path, status, extra=extra)
            reset_request_context(token)
