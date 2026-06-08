"""subject_backend role contract (spec §7.1 / §9).

Wire shapes (``Subject``, ``SubjectFilter``, ``SubjectList``, ``SubjectPatch``,
``SubjectSchema``, …) are generated from the Rust schema and re-exported. The
author-facing ``SubjectBackend`` protocol is an ergonomic wrapper: the SDK
auto-fills wire-mandatory fields, unwraps the daemon's ``{filter}`` envelope,
and backfills ``kind`` from the route.

``list`` receives the generated ``SubjectFilter`` (the validated wire shape,
matching the TS SDK). Its collection filter fields (``status``, ``assignee``,
``labels_any``, …) default to an **empty list** when omitted (mirroring the Rust
schema), not ``None`` — an empty list and an absent filter are semantically the
same "no constraint". Backends should test ``if params.status:`` rather than
``is None`` for "was a filter supplied".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..types.generated import subject as gen
from ..types.subject_protocol import (
    Subject,
    SubjectCreateRequest,
    SubjectListParams,
    SubjectListResult,
    SubjectPatch,
    SubjectStatus,
)
from .context import CallContext, HealthReport

# Advanced authors can reach the exact generated wire shapes.
SubjectFilter = gen.SubjectFilter
SubjectList = gen.SubjectList
SubjectId = gen.SubjectId
SubjectSchema = gen.SubjectSchema
SubjectAttachment = gen.SubjectAttachment
SubjectChangedEvent = gen.SubjectChangedEvent
ChangeKind = gen.ChangeKind
CustomFieldSpec = gen.CustomFieldSpec
CustomFieldKind = gen.CustomFieldKind
StatusDispatchHint = gen.StatusDispatchHint
DeleteSubjectRequest = gen.DeleteSubjectRequest
DeleteSubjectResponse = gen.DeleteSubjectResponse


@dataclass
class SubjectCallContext(CallContext):
    """Context passed to every subject-backend method.

    `kind` is parsed from the RPC method by the SDK so authors don't have to
    (e.g. method `"task/list"` → `ctx.kind == "task"`).
    """

    kind: str = ""


@runtime_checkable
class SubjectBackend(Protocol):
    """A subject backend serves one or more subject kinds.

    Required: `list`, `get`. Optional: `create`, `update`, `status`, `next`,
    `delete`, `schema`, `health`. The dispatcher uses `hasattr` checks before
    routing optional verbs and replies `-32001` (`method_not_supported`) when
    an optional verb is called but not implemented.
    """

    def list(
        self,
        params: SubjectListParams,
        ctx: SubjectCallContext,
    ) -> SubjectListResult: ...

    def get(
        self,
        params: dict[str, Any],
        ctx: SubjectCallContext,
    ) -> Subject | None: ...

    # Optional verbs — define when supported.
    # def create(self, params: SubjectCreateRequest, ctx: SubjectCallContext) -> Subject: ...
    # def update(self, params: dict[str, Any], ctx: SubjectCallContext) -> Subject: ...
    # def status(self, params: dict[str, Any], ctx: SubjectCallContext) -> Subject: ...
    # def next(self, params: dict[str, Any], ctx: SubjectCallContext) -> Subject | None: ...
    # def delete(self, params: dict[str, Any], ctx: SubjectCallContext) -> Any: ...
    # def schema(self, ctx: CallContext) -> dict[str, Any]: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "ChangeKind",
    "CustomFieldKind",
    "CustomFieldSpec",
    "DeleteSubjectRequest",
    "DeleteSubjectResponse",
    "HealthReport",
    "StatusDispatchHint",
    "Subject",
    "SubjectAttachment",
    "SubjectBackend",
    "SubjectCallContext",
    "SubjectChangedEvent",
    "SubjectCreateRequest",
    "SubjectFilter",
    "SubjectId",
    "SubjectList",
    "SubjectListParams",
    "SubjectListResult",
    "SubjectPatch",
    "SubjectSchema",
    "SubjectStatus",
]
