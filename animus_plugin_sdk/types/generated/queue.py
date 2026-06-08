# AUTO-GENERATED FROM schemas/animus-queue-protocol/_all.json — DO NOT EDIT BY HAND.
# Regenerate via: python scripts/codegen.py
# ruff: noqa
from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class GeneratedModel(BaseModel):
    """Base for generated wire models: extra fields preserved (forward compat)."""

    model_config = ConfigDict(
        extra="allow", populate_by_name=True, protected_namespaces=()
    )


class QueueCapabilities(GeneratedModel):
    "Capability flags for queue plugins."
    max_lease_batch: Optional[int] = Field(default=None, ge=0)
    priority_weighted: Optional[bool] = Field(default=None)


class QueueCompletionRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_COMPLETION`]."
    entry_id: str
    status: str
    workflow_id: Optional[str] = Field(default=None)
    workflow_ref: Optional[str] = Field(default=None)


class QueueDropRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_DROP`]."
    entry_id: str


class SubjectRef(GeneratedModel):
    "Backend-qualified subject reference with optional display metadata."
    description: Optional[str] = Field(default=None)
    id: str
    kind: str
    labels: list[str] = Field(default_factory=list)
    metadata: Any = Field(default=None)
    title: Optional[str] = Field(default=None)


class SubjectDispatch(GeneratedModel):
    "Full dispatch envelope handed off from queue / scheduler / trigger to the"
    input: Any = Field(default=None)
    priority: Optional[str] = Field(default=None)
    requested_at: str
    subject: "SubjectRef"
    trigger_source: str
    vars: dict[str, str] = Field(default_factory=dict)
    workflow_ref: str


class QueueEnqueueRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_ENQUEUE`]."
    subject_dispatch: "SubjectDispatch"


class QueueEnqueueResponse(GeneratedModel):
    "Response for [`METHOD_QUEUE_ENQUEUE`]."
    enqueued: bool
    entry_id: str
    subject_id: str


class QueueEntry(GeneratedModel):
    "A queue entry shape returned by list / lease."
    assigned_at: Optional[str] = Field(default=None)
    enqueued_at: str
    entry_id: str
    held_at: Optional[str] = Field(default=None)
    status: str
    subject_dispatch: "SubjectDispatch"
    subject_id: str
    task_id: Optional[str] = Field(default=None)
    workflow_id: Optional[str] = Field(default=None)


class QueueHoldRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_HOLD`]."
    entry_id: str
    reason: Optional[str] = Field(default=None)


SubjectId = str


class QueueLeaseRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_LEASE`]."
    exclude_subjects: Optional[list["SubjectId"]] = Field(default=None)
    max: int = Field(ge=0)
    workflow_ids: Optional[list[str]] = Field(default=None)


class QueueLeaseResponse(GeneratedModel):
    "Response for [`METHOD_QUEUE_LEASE`]."
    leased: list["QueueEntry"]


class QueueListRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_LIST`]."
    limit: Optional[int] = Field(default=None, ge=0)
    offset: Optional[int] = Field(default=None, ge=0)
    status: list[str] = Field(default_factory=list)


class QueueStats(GeneratedModel):
    "Queue aggregate counts."
    assigned: int = Field(ge=0)
    held: int = Field(ge=0)
    pending: int = Field(ge=0)
    total: int = Field(ge=0)


class QueueListResponse(GeneratedModel):
    "Response for [`METHOD_QUEUE_LIST`]."
    entries: list["QueueEntry"]
    stats: "QueueStats"
    total: int = Field(ge=0)


class QueueMarkAssignedRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_MARK_ASSIGNED`]."
    entry_id: str
    workflow_id: Optional[str] = Field(default=None)


class QueueMutationResponse(GeneratedModel):
    "Generic mutation result used by hold / release / drop / mark_assigned /"
    changed: bool
    not_found: Optional[bool] = Field(default=None)


class QueueReleasePendingParams(GeneratedModel):
    "Request for [`METHOD_QUEUE_RELEASE_PENDING`]."
    entry_id: str
    reason: str


class QueueReleasePendingResponse(GeneratedModel):
    "Response for [`METHOD_QUEUE_RELEASE_PENDING`]."
    entry_id: str
    status: str


class QueueReleaseRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_RELEASE`]."
    entry_id: str


class QueueReorderRequest(GeneratedModel):
    "Request for [`METHOD_QUEUE_REORDER`]."
    entry_ids: list[str]


class QueueReorderResponse(GeneratedModel):
    "Response for [`METHOD_QUEUE_REORDER`]."
    reordered_count: int = Field(ge=0)


QueueCapabilities.model_rebuild()
QueueCompletionRequest.model_rebuild()
QueueDropRequest.model_rebuild()
SubjectRef.model_rebuild()
SubjectDispatch.model_rebuild()
QueueEnqueueRequest.model_rebuild()
QueueEnqueueResponse.model_rebuild()
QueueEntry.model_rebuild()
QueueHoldRequest.model_rebuild()
QueueLeaseRequest.model_rebuild()
QueueLeaseResponse.model_rebuild()
QueueListRequest.model_rebuild()
QueueStats.model_rebuild()
QueueListResponse.model_rebuild()
QueueMarkAssignedRequest.model_rebuild()
QueueMutationResponse.model_rebuild()
QueueReleasePendingParams.model_rebuild()
QueueReleasePendingResponse.model_rebuild()
QueueReleaseRequest.model_rebuild()
QueueReorderRequest.model_rebuild()
QueueReorderResponse.model_rebuild()
