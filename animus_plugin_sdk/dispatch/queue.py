"""queue dispatcher (spec §7.6). All methods validate against generated request
models and route to the impl."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..roles.context import CallContext
from ..roles.queue import Queue
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.queue import (
    QueueCompletionRequest,
    QueueDropRequest,
    QueueEnqueueRequest,
    QueueHoldRequest,
    QueueLeaseRequest,
    QueueListRequest,
    QueueMarkAssignedRequest,
    QueueReleasePendingParams,
    QueueReleaseRequest,
    QueueReorderRequest,
)
from .shared import (
    ParamValidationError,
    error_response,
    method_not_found,
    method_not_supported,
    ok_response,
    validate_params,
)

QUEUE_METHODS = {
    "enqueue": "queue/enqueue",
    "list": "queue/list",
    "lease": "queue/lease",
    "stats": "queue/stats",
    "hold": "queue/hold",
    "release": "queue/release",
    "drop": "queue/drop",
    "mark_assigned": "queue/mark_assigned",
    "completion": "queue/completion",
    "reorder": "queue/reorder",
}
QUEUE_RELEASE_PENDING = "queue/release_pending"

_VALIDATED: dict[str, tuple[str, type[BaseModel]]] = {
    "queue/enqueue": ("enqueue", QueueEnqueueRequest),
    "queue/list": ("list", QueueListRequest),
    "queue/lease": ("lease", QueueLeaseRequest),
    "queue/hold": ("hold", QueueHoldRequest),
    "queue/release": ("release", QueueReleaseRequest),
    "queue/drop": ("drop", QueueDropRequest),
    "queue/mark_assigned": ("mark_assigned", QueueMarkAssignedRequest),
    "queue/completion": ("completion", QueueCompletionRequest),
    "queue/reorder": ("reorder", QueueReorderRequest),
}


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_queue(request_id: RpcId, frame: RpcRequest, impl: Queue) -> RpcResponse:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method == QUEUE_METHODS["stats"]:
            return ok_response(request_id, _to_dict(impl.stats({}, ctx)))
        if method in _VALIDATED:
            attr, model = _VALIDATED[method]
            value = validate_params(request_id, model, frame.params)
            return ok_response(request_id, _to_dict(getattr(impl, attr)(value, ctx)))
        if method == QUEUE_RELEASE_PENDING:
            fn = getattr(impl, "release_pending", None)
            if not callable(fn):
                return method_not_supported(request_id, method)
            value = validate_params(request_id, QueueReleasePendingParams, frame.params)
            return ok_response(request_id, _to_dict(fn(value, ctx)))
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(request_id, ErrorCode.INTERNAL_ERROR, f"queue error: {exc!s}")
