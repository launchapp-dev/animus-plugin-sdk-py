"""queue role contract (spec §7.6, v1.1.0+)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import queue as gen
from .context import CallContext, HealthReport

QueueEnqueueRequest = gen.QueueEnqueueRequest
QueueEnqueueResponse = gen.QueueEnqueueResponse
QueueListRequest = gen.QueueListRequest
QueueListResponse = gen.QueueListResponse
QueueLeaseRequest = gen.QueueLeaseRequest
QueueLeaseResponse = gen.QueueLeaseResponse
QueueStats = gen.QueueStats
QueueHoldRequest = gen.QueueHoldRequest
QueueReleaseRequest = gen.QueueReleaseRequest
QueueDropRequest = gen.QueueDropRequest
QueueMarkAssignedRequest = gen.QueueMarkAssignedRequest
QueueCompletionRequest = gen.QueueCompletionRequest
QueueMutationResponse = gen.QueueMutationResponse
QueueReorderRequest = gen.QueueReorderRequest
QueueReorderResponse = gen.QueueReorderResponse
QueueReleasePendingParams = gen.QueueReleasePendingParams
QueueReleasePendingResponse = gen.QueueReleasePendingResponse
QueueEntry = gen.QueueEntry
SubjectDispatch = gen.SubjectDispatch


@runtime_checkable
class Queue(Protocol):
    """Per-project priority FIFO of ``SubjectDispatch`` envelopes.

    Required: `enqueue`, `list`, `lease`, `stats`, `hold`, `release`, `drop`,
    `mark_assigned`, `completion`, `reorder`. Optional: `release_pending`,
    `health`.
    """

    def enqueue(self, params: QueueEnqueueRequest, ctx: CallContext) -> Any: ...
    def list(self, params: QueueListRequest, ctx: CallContext) -> Any: ...
    def lease(self, params: QueueLeaseRequest, ctx: CallContext) -> Any: ...
    def stats(self, params: dict[str, Any], ctx: CallContext) -> Any: ...
    def hold(self, params: QueueHoldRequest, ctx: CallContext) -> Any: ...
    def release(self, params: QueueReleaseRequest, ctx: CallContext) -> Any: ...
    def drop(self, params: QueueDropRequest, ctx: CallContext) -> Any: ...
    def mark_assigned(self, params: QueueMarkAssignedRequest, ctx: CallContext) -> Any: ...
    def completion(self, params: QueueCompletionRequest, ctx: CallContext) -> Any: ...
    def reorder(self, params: QueueReorderRequest, ctx: CallContext) -> Any: ...

    # Optional:
    # def release_pending(self, params: QueueReleasePendingParams, ctx: CallContext) -> Any: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "HealthReport",
    "Queue",
    "QueueCompletionRequest",
    "QueueDropRequest",
    "QueueEnqueueRequest",
    "QueueEnqueueResponse",
    "QueueEntry",
    "QueueHoldRequest",
    "QueueLeaseRequest",
    "QueueLeaseResponse",
    "QueueListRequest",
    "QueueListResponse",
    "QueueMarkAssignedRequest",
    "QueueMutationResponse",
    "QueueReleasePendingParams",
    "QueueReleasePendingResponse",
    "QueueReleaseRequest",
    "QueueReorderRequest",
    "QueueReorderResponse",
    "QueueStats",
    "SubjectDispatch",
]
