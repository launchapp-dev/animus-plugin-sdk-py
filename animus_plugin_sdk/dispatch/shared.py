"""Shared helpers for role dispatchers: pydantic param validation + uniform
error mapping to JSON-RPC responses."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..types import ErrorCode, RpcId, RpcResponse
from ..wire import Wire, error_response, ok_response

__all__ = [
    "ParamValidationError",
    "Wire",
    "ack_then_stream",
    "error_response",
    "method_not_found",
    "method_not_supported",
    "ok_response",
    "run_stream_thread",
    "validate_params",
]

_M = TypeVar("_M", bound=BaseModel)


class ParamValidationError(Exception):
    """Raised by `validate_params` when inbound params fail validation.

    Carries a ready-to-send ``-32602`` (``invalid_params``) error response. The
    role dispatchers catch this and return ``.response`` directly, so the
    happy-path call sites get a narrowed, non-Optional validated model.
    """

    def __init__(self, response: RpcResponse) -> None:
        super().__init__("invalid params")
        self.response = response


def validate_params(request_id: RpcId, model: type[_M], raw: Any) -> _M:
    """Validate raw JSON-RPC params against a generated pydantic model.

    Returns the validated model on success. Raises ``ParamValidationError``
    (carrying a ``-32602`` reply with the formatted issue list in
    ``error.data``) on failure — matching the TS SDK's ``validateParams``.
    """
    payload = raw if raw is not None else {}
    if not isinstance(payload, dict):
        raise ParamValidationError(
            error_response(
                request_id,
                ErrorCode.INVALID_PARAMS,
                "invalid params: expected a JSON object",
                {"category": "invalid_request"},
            )
        )
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        issues = [
            {
                "path": ".".join(str(p) for p in err.get("loc", ())),
                "message": err.get("msg", "validation failed"),
                "code": err.get("type", "value_error"),
            }
            for err in exc.errors()
        ]
        first = issues[0]["message"] if issues else "validation failed"
        raise ParamValidationError(
            error_response(
                request_id,
                ErrorCode.INVALID_PARAMS,
                f"invalid params: {first}",
                {"category": "invalid_request", "issues": issues},
            )
        ) from exc


def method_not_supported(request_id: RpcId, method: str) -> RpcResponse:
    """`-32001` method_not_supported (optional method not implemented)."""
    return error_response(
        request_id,
        ErrorCode.METHOD_NOT_SUPPORTED,
        f"method '{method}' not supported",
        {"category": "not_supported"},
    )


def method_not_found(request_id: RpcId, method: str) -> RpcResponse:
    """`-32601` method_not_found (method not recognized for this role)."""
    return error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"unknown method '{method}'")


def run_stream_thread(target: Callable[[], None], name: str) -> None:
    """Spawn a daemon thread to drain a streaming source.

    Streaming roles (trigger/watch, log_storage/tail) ack immediately and then
    drain the author's iterator on this background thread, emitting
    notifications via the wire (whose writes are serialized by a lock). Daemon
    threads do not block process exit on `exit`/EOF.
    """
    thread = threading.Thread(target=target, name=name, daemon=True)
    thread.start()


def ack_then_stream(
    wire: Wire,
    request_id: RpcId,
    ack_body: Any,
    drain: Callable[[], None],
    name: str,
) -> None:
    """Flush the streaming ack, then spawn the drain thread.

    Streaming roles MUST send their `{"watching"/"tailing": true}` ack BEFORE
    any `<role>/event` notification (spec §7.3, §7.4: the response acknowledges
    the stream, subsequent events arrive as notifications). If we returned the
    ack to the caller and let it write the response after spawning the drain
    thread, the drain thread could grab the wire lock and emit the first event
    ahead of the ack. Writing the ack here — before the thread exists —
    guarantees the ack reaches the host first. Callers return ``None`` so the
    wire loop does not double-write the ack.
    """
    wire.send_response(ok_response(request_id, ack_body))
    run_stream_thread(drain, name=name)
