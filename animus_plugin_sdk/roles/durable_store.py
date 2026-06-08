"""durable_store role contract (spec §7.7, v1.1.0+)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import durable_store as gen
from .context import CallContext, HealthReport

BeginWorkflowRunRequest = gen.BeginWorkflowRunRequest
BeginWorkflowRunResponse = gen.BeginWorkflowRunResponse
BeginStepRequest = gen.BeginStepRequest
BeginStepResponse = gen.BeginStepResponse
CommitStepRequest = gen.CommitStepRequest
CommitStepResponse = gen.CommitStepResponse
AbandonStepRequest = gen.AbandonStepRequest
AbandonStepResponse = gen.AbandonStepResponse
RecoverInFlightRequest = gen.RecoverInFlightRequest
RecoverInFlightResponse = gen.RecoverInFlightResponse
QueryRunRequest = gen.QueryRunRequest
QueryRunResponse = gen.QueryRunResponse


@runtime_checkable
class DurableStore(Protocol):
    """Reservation-fenced step persistence.

    Required: `begin_workflow_run`, `begin_step`, `commit_step`,
    `abandon_step`, `recover_in_flight`, `query_run`. Optional: `health`.
    """

    def begin_workflow_run(self, params: BeginWorkflowRunRequest, ctx: CallContext) -> Any: ...
    def begin_step(self, params: BeginStepRequest, ctx: CallContext) -> Any: ...
    def commit_step(self, params: CommitStepRequest, ctx: CallContext) -> Any: ...
    def abandon_step(self, params: AbandonStepRequest, ctx: CallContext) -> Any: ...
    def recover_in_flight(self, params: RecoverInFlightRequest, ctx: CallContext) -> Any: ...
    def query_run(self, params: QueryRunRequest, ctx: CallContext) -> Any: ...

    # Optional:
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "AbandonStepRequest",
    "AbandonStepResponse",
    "BeginStepRequest",
    "BeginStepResponse",
    "BeginWorkflowRunRequest",
    "BeginWorkflowRunResponse",
    "CommitStepRequest",
    "CommitStepResponse",
    "DurableStore",
    "HealthReport",
    "QueryRunRequest",
    "QueryRunResponse",
    "RecoverInFlightRequest",
    "RecoverInFlightResponse",
]
