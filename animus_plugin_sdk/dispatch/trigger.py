"""trigger_backend dispatcher (spec §7.3 / §11).

``trigger/watch`` acks ``{"watching": true}`` immediately, then drains the
author's iterator on a background daemon thread, emitting each event as a flat
``trigger/event`` notification (spec §11.1 — no ``{id, event}`` wrapper).
Stream-level errors after the ack become a ``trigger/event`` notification whose
``params`` carries an ``error`` object, terminating the stream.
"""

from __future__ import annotations

from typing import Any

from ..roles.trigger import TriggerBackend, TriggerEvent
from ..types import ErrorCode, PluginCapabilities, RpcId, RpcRequest, RpcResponse
from .shared import (
    Wire,
    ack_then_stream,
    error_response,
    method_not_supported,
    ok_response,
)


def derive_trigger_capabilities(impl: TriggerBackend, extra: list[str]) -> PluginCapabilities:
    methods = ["trigger/watch", "trigger/schema", "health/check"]
    if callable(getattr(impl, "ack", None)):
        methods.append("trigger/ack")
    methods.extend(extra)
    return PluginCapabilities(methods=methods, streaming=True, progress=False, cancellation=False)


def _default_trigger_schema(impl: TriggerBackend) -> dict[str, Any]:
    return {
        "kinds": [],
        "supports_resume": False,
        "supports_dedup": False,
        "supports_ack": callable(getattr(impl, "ack", None)),
    }


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def _event_to_params(event: TriggerEvent | dict[str, Any]) -> dict[str, Any]:
    """Flatten a TriggerEvent into the wire `params`, dropping unset optionals
    (spec §11.1: omitted optionals MUST NOT appear)."""
    if isinstance(event, TriggerEvent):
        data: dict[str, Any] = {"event_id": event.event_id}
        if event.trigger_id is not None:
            data["trigger_id"] = event.trigger_id
        if event.subject_id is not None:
            data["subject_id"] = event.subject_id
        if event.subject_kind is not None:
            data["subject_kind"] = event.subject_kind
        if event.action_hint is not None:
            data["action_hint"] = event.action_hint
        if event.payload is not None:
            data["payload"] = event.payload
        return data
    return dict(event)


def dispatch_trigger(
    request_id: RpcId,
    frame: RpcRequest,
    wire: Wire,
    impl: TriggerBackend,
) -> RpcResponse | None:
    method = frame.method
    raw_params = frame.params if isinstance(frame.params, dict) else {}
    ctx_request_id = request_id
    try:
        if method == "trigger/schema":
            schema_fn = getattr(impl, "schema", None)
            if callable(schema_fn):
                from ..roles.context import CallContext

                return ok_response(
                    request_id, _to_dict(schema_fn(CallContext(request_id=ctx_request_id)))
                )
            return ok_response(request_id, _default_trigger_schema(impl))
        if method == "trigger/watch":
            from ..roles.context import CallContext

            stream = impl.watch(raw_params, CallContext(request_id=ctx_request_id))

            def drain() -> None:
                try:
                    for event in stream:
                        wire.notify("trigger/event", _event_to_params(event))
                except Exception as exc:
                    wire.notify(
                        "trigger/event",
                        {
                            "error": {
                                "code": ErrorCode.INTERNAL_ERROR,
                                "message": f"trigger stream error: {exc!s}",
                            }
                        },
                    )

            ack_then_stream(
                wire, request_id, {"watching": True}, drain, name="animus-trigger-watch"
            )
            return None
        if method == "trigger/ack":
            ack_fn = getattr(impl, "ack", None)
            if not callable(ack_fn):
                return method_not_supported(request_id, method)
            event_id = raw_params.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                return error_response(
                    request_id, ErrorCode.INVALID_PARAMS, "trigger/ack requires string event_id"
                )
            from ..roles.context import CallContext

            # Forward the optional `status` (TriggerAckParams) so impls can
            # distinguish dispatched/queued/failed/skipped acknowledgements.
            ack_params: dict[str, Any] = {"event_id": event_id}
            status = raw_params.get("status")
            if status is not None:
                ack_params["status"] = status
            ack_fn(ack_params, CallContext(request_id=ctx_request_id))
            return ok_response(request_id, {"event_id": event_id, "acked": True})
        return error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"unknown method '{method}'")
    except Exception as exc:
        return error_response(
            request_id, ErrorCode.INTERNAL_ERROR, f"trigger backend error: {exc!s}"
        )
