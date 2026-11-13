import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime

SERVICE_NAME = "trading-app"
LOGGER_NAME = "trading-app"

_TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@dataclass
class RequestContext:
    trace_id: str
    endpoint: str
    advisor_id: str | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def mask_pii(value: object) -> str:
    """Mask an account number, SSN or tax ID for logging, keeping the last four characters only."""
    text = "" if value is None else str(value)
    return f"****{text[-4:]}" if len(text) > 4 else "****"


def new_trace_id() -> str:
    return uuid.uuid4().hex


def resolve_trace_id(candidate: str | None) -> str:
    if candidate and _TRACE_ID_PATTERN.match(candidate):
        return candidate
    return new_trace_id()


def start_request_context(
    trace_id: str, endpoint: str, advisor_id: str | None = None
) -> Token[RequestContext | None]:
    return _request_context.set(RequestContext(trace_id, endpoint, advisor_id))


def reset_request_context(token: Token[RequestContext | None]) -> None:
    _request_context.reset(token)


def current_context() -> RequestContext | None:
    return _request_context.get()


def current_trace_id() -> str | None:
    ctx = _request_context.get()
    return ctx.trace_id if ctx else None


def bind_advisor_id(advisor_id: object) -> None:
    # The context object is shared with the middleware, so mutating it (rather than
    # setting a new value) is visible there even from threadpool-run handlers.
    ctx = _request_context.get()
    if ctx is not None and isinstance(advisor_id, str) and advisor_id:
        ctx.advisor_id = advisor_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = _request_context.get()
        timestamp = datetime.fromtimestamp(record.created, tz=UTC)
        payload = {
            "timestamp": timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "endpoint": getattr(record, "endpoint", ctx.endpoint if ctx else None),
            "status": getattr(record, "status", None),
            "latency_ms": getattr(record, "latency_ms", None),
            "trace_id": getattr(record, "trace_id", ctx.trace_id if ctx else None),
            "advisor_id": getattr(record, "advisor_id", ctx.advisor_id if ctx else None),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    app_logger = logging.getLogger(LOGGER_NAME)
    app_logger.handlers = [handler]
    app_logger.setLevel(level)
    app_logger.propagate = False

    server_logger = logging.getLogger("uvicorn")
    server_logger.handlers = [handler]
    server_logger.propagate = False

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = []
    access_logger.propagate = False
    access_logger.disabled = True


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)
