"""transport_backend dispatcher (spec §13).

``transport/start`` binds the listener (validated against generated
``TransportConfig``), ``transport/shutdown`` drains, ``transport/schema``
declares capabilities. Errors carry an ``error.data.category`` per spec §13.4.
"""

from __future__ import annotations

from typing import Any

from ..roles.context import CallContext
from ..roles.transport import TransportBackend
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.transport import TransportConfig
from .shared import (
    ParamValidationError,
    Wire,
    error_response,
    method_not_found,
    ok_response,
    validate_params,
)

TRANSPORT_METHODS = {
    "start": "transport/start",
    "shutdown": "transport/shutdown",
    "schema": "transport/schema",
}


def _default_schema() -> dict[str, Any]:
    return {"kinds": [], "supports_streaming": False, "supports_websocket": False}


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_transport(
    request_id: RpcId,
    frame: RpcRequest,
    wire: Wire,
    impl: TransportBackend,
) -> RpcResponse:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method == TRANSPORT_METHODS["start"]:
            config = validate_params(request_id, TransportConfig, frame.params)
            return ok_response(request_id, _to_dict(impl.start(config, ctx)))
        if method == TRANSPORT_METHODS["shutdown"]:
            shutdown_fn = getattr(impl, "shutdown", None)
            if callable(shutdown_fn):
                shutdown_fn(ctx)
            return ok_response(request_id, {})
        if method == TRANSPORT_METHODS["schema"]:
            schema_fn = getattr(impl, "schema", None)
            if callable(schema_fn):
                return ok_response(request_id, _to_dict(schema_fn(ctx)))
            return ok_response(request_id, _default_schema())
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(
            request_id,
            ErrorCode.INTERNAL_ERROR,
            f"transport backend error: {exc!s}",
            {"category": "other"},
        )
