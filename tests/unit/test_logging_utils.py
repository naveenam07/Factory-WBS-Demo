import json
import logging
import sys

import pytest

from app.logging_utils import (
    LOGGER_NAME,
    JsonFormatter,
    bind_advisor_id,
    configure_logging,
    current_context,
    current_trace_id,
    get_logger,
    mask_pii,
    reset_request_context,
    resolve_trace_id,
    start_request_context,
)


@pytest.mark.parametrize(
    ("value", "masked"),
    [
        ("9000000001", "****0001"),
        ("900-00-0001", "****0001"),
        (1234567890, "****7890"),
        ("12345", "****2345"),
        ("1234", "****"),
        ("12", "****"),
        ("", "****"),
        (None, "****"),
    ],
)
def test_mask_pii_keeps_last_four_only(value, masked) -> None:
    assert mask_pii(value) == masked


def test_resolve_trace_id_accepts_safe_ids_and_replaces_others() -> None:
    assert resolve_trace_id("abc-123") == "abc-123"
    for candidate in (None, "", "bad id\n", "x" * 65):
        generated = resolve_trace_id(candidate)
        assert generated != candidate
        assert len(generated) == 32


def test_request_context_lifecycle_and_advisor_binding() -> None:
    assert current_trace_id() is None
    bind_advisor_id("A-1001")

    token = start_request_context("trace-1", "POST /api/v1/transfers")
    try:
        bind_advisor_id(None)
        bind_advisor_id("")
        assert current_context().advisor_id is None
        bind_advisor_id("A-1001")
        assert current_trace_id() == "trace-1"
        assert current_context().advisor_id == "A-1001"
    finally:
        reset_request_context(token)

    assert current_context() is None


def _record(message: str, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord("trading-app.test", logging.ERROR, __file__, 1, message, (), exc_info)


def test_json_formatter_includes_context_and_exception() -> None:
    token = start_request_context("trace-2", "GET /healthz", "A-1002")
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            payload = json.loads(JsonFormatter().format(_record("failed", sys.exc_info())))
    finally:
        reset_request_context(token)

    assert payload["trace_id"] == "trace-2"
    assert payload["endpoint"] == "GET /healthz"
    assert payload["advisor_id"] == "A-1002"
    assert payload["message"] == "failed"
    assert "ValueError: boom" in payload["exception"]


def test_json_formatter_without_context() -> None:
    payload = json.loads(JsonFormatter().format(_record("plain")))

    assert payload["trace_id"] is None
    assert payload["endpoint"] is None
    assert "exception" not in payload


def test_configure_logging_and_get_logger() -> None:
    configure_logging()

    app_logger = logging.getLogger(LOGGER_NAME)
    assert isinstance(app_logger.handlers[0].formatter, JsonFormatter)
    assert app_logger.propagate is False
    assert logging.getLogger("uvicorn.access").disabled is True
    assert get_logger().name == LOGGER_NAME
    assert get_logger("transfers").name == f"{LOGGER_NAME}.transfers"
