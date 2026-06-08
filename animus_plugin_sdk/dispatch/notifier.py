"""notifier dispatcher. ``notifier/notify`` (required), optional
``notifier/flush`` (→ -32001 when absent), and ``notifier/schema``."""

from __future__ import annotations

from typing import Any

from ..roles.context import CallContext
from ..roles.notifier import Notifier
from ..types import ErrorCode, PluginCapabilities, RpcId, RpcRequest, RpcResponse
from ..types.generated.notifier import NotifierFlushParams, NotifierNotifyParams
from .shared import (
    ParamValidationError,
    error_response,
    method_not_found,
    method_not_supported,
    ok_response,
    validate_params,
)

NOTIFIER_METHODS = {
    "notify": "notifier/notify",
    "flush": "notifier/flush",
    "schema": "notifier/schema",
}


def derive_notifier_capabilities(impl: Notifier) -> PluginCapabilities:
    methods = [NOTIFIER_METHODS["notify"], NOTIFIER_METHODS["schema"], "health/check"]
    if callable(getattr(impl, "flush", None)):
        methods.append(NOTIFIER_METHODS["flush"])
    return PluginCapabilities(methods=methods, streaming=False, progress=False, cancellation=False)


def _default_schema(impl: Notifier) -> dict[str, Any]:
    return {"connector_kinds": [], "supports_flush": callable(getattr(impl, "flush", None))}


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_notifier(request_id: RpcId, frame: RpcRequest, impl: Notifier) -> RpcResponse:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method == NOTIFIER_METHODS["notify"]:
            notify_params = validate_params(request_id, NotifierNotifyParams, frame.params)
            return ok_response(request_id, _to_dict(impl.notify(notify_params, ctx)))
        if method == NOTIFIER_METHODS["flush"]:
            flush_fn = getattr(impl, "flush", None)
            if not callable(flush_fn):
                return method_not_supported(request_id, method)
            flush_params = validate_params(request_id, NotifierFlushParams, frame.params)
            return ok_response(request_id, _to_dict(flush_fn(flush_params, ctx)))
        if method == NOTIFIER_METHODS["schema"]:
            schema_fn = getattr(impl, "schema", None)
            if callable(schema_fn):
                return ok_response(request_id, _to_dict(schema_fn(ctx)))
            return ok_response(request_id, _default_schema(impl))
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(request_id, ErrorCode.INTERNAL_ERROR, f"notifier error: {exc!s}")
