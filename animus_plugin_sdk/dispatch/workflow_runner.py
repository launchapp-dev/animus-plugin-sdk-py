"""workflow_runner dispatcher (spec §7.5)."""

from __future__ import annotations

from typing import Any

from ..roles.context import CallContext
from ..roles.workflow_runner import WorkflowRunner
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.workflow_runner import WorkflowExecuteRequest, WorkflowPhaseRunRequest
from .shared import (
    ParamValidationError,
    error_response,
    method_not_found,
    ok_response,
    validate_params,
)

WORKFLOW_RUNNER_METHODS = {"execute": "workflow/execute", "run_phase": "workflow/run_phase"}


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_workflow_runner(
    request_id: RpcId, frame: RpcRequest, impl: WorkflowRunner
) -> RpcResponse:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method == WORKFLOW_RUNNER_METHODS["execute"]:
            execute_request = validate_params(request_id, WorkflowExecuteRequest, frame.params)
            return ok_response(request_id, _to_dict(impl.execute(execute_request, ctx)))
        if method == WORKFLOW_RUNNER_METHODS["run_phase"]:
            phase_request = validate_params(request_id, WorkflowPhaseRunRequest, frame.params)
            return ok_response(request_id, _to_dict(impl.run_phase(phase_request, ctx)))
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(
            request_id, ErrorCode.INTERNAL_ERROR, f"workflow_runner error: {exc!s}"
        )
