"""durable_store dispatcher (spec §7.7)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..roles.context import CallContext
from ..roles.durable_store import DurableStore
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.durable_store import (
    AbandonStepRequest,
    BeginStepRequest,
    BeginWorkflowRunRequest,
    CommitStepRequest,
    QueryRunRequest,
    RecoverInFlightRequest,
)
from .shared import (
    ParamValidationError,
    error_response,
    method_not_found,
    ok_response,
    validate_params,
)

DURABLE_STORE_METHODS = {
    "begin_workflow_run": "durable/begin_workflow_run",
    "begin_step": "durable/begin_step",
    "commit_step": "durable/commit_step",
    "abandon_step": "durable/abandon_step",
    "recover_in_flight": "durable/recover_in_flight",
    "query_run": "durable/query_run",
}

_VALIDATED: dict[str, tuple[str, type[BaseModel]]] = {
    "durable/begin_workflow_run": ("begin_workflow_run", BeginWorkflowRunRequest),
    "durable/begin_step": ("begin_step", BeginStepRequest),
    "durable/commit_step": ("commit_step", CommitStepRequest),
    "durable/abandon_step": ("abandon_step", AbandonStepRequest),
    "durable/recover_in_flight": ("recover_in_flight", RecoverInFlightRequest),
    "durable/query_run": ("query_run", QueryRunRequest),
}


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_durable_store(request_id: RpcId, frame: RpcRequest, impl: DurableStore) -> RpcResponse:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method in _VALIDATED:
            attr, model = _VALIDATED[method]
            value = validate_params(request_id, model, frame.params)
            return ok_response(request_id, _to_dict(getattr(impl, attr)(value, ctx)))
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(request_id, ErrorCode.INTERNAL_ERROR, f"durable_store error: {exc!s}")
