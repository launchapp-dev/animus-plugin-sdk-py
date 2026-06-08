"""Subject wire types.

The exact wire shapes are generated from the Rust ``animus-subject-protocol``
schema (regenerate via ``python scripts/codegen.py``) and reachable via
``animus_plugin_sdk.subject.gen`` (or ``animus_plugin_sdk.types.generated.subject``).

The names exported here (``Subject``, ``SubjectListParams``,
``SubjectListResult``, ``SubjectPatch``, ``SubjectCreateRequest``) are
**author-ergonomic** wrappers. They share the generated wire shapes but keep the
wire-mandatory fields (``status`` / ``created_at`` / ``updated_at`` on a subject,
``fetched_at`` on a list) optional with sensible defaults, so historical sparse
construction — ``Subject(id=..., kind=..., title=...)`` — keeps working. The SDK
backfills any omitted wire-mandatory fields on the way out (see
``dispatch.subject.ensure_wire_subject``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# The generated wire types (exact Rust shape). Re-exported under explicit names
# for advanced authors who want the strict shape.
from .generated.subject import Subject as WireSubject
from .generated.subject import SubjectFilter as SubjectListParams
from .generated.subject import SubjectList as WireSubjectList
from .generated.subject import SubjectPatch as SubjectPatch
from .generated.subject import SubjectStatus as SubjectStatus

__all__ = [
    "Subject",
    "SubjectCreateRequest",
    "SubjectListParams",
    "SubjectListResult",
    "SubjectPatch",
    "SubjectStatus",
    "WireSubject",
    "WireSubjectList",
]


class _PermissiveModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Subject(_PermissiveModel):
    """A single subject record.

    Same fields as the generated wire ``Subject``, but the wire-mandatory
    ``status`` / ``created_at`` / ``updated_at`` are kept optional (with
    defaults) for author ergonomics — the SDK backfills them on the wire when an
    author omits them in a sparse / hello-world example.
    """

    id: str
    kind: str
    title: str
    status: str = "ready"
    created_at: str = ""
    updated_at: str = ""
    description: str | None = None
    priority: int | None = None
    assignee: str | None = None
    labels: list[str] = Field(default_factory=list)
    native_status: str | None = None
    parent: str | None = None
    children: list[str] = Field(default_factory=list)
    attachments: list[Any] = Field(default_factory=list)
    status_metadata: Any | None = None
    url: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)


class SubjectListResult(_PermissiveModel):
    """Result of ``subject/list``.

    Mirrors the generated ``SubjectList`` but keeps ``fetched_at`` optional so
    authors can omit it (the SDK fills it on the wire).
    """

    subjects: list[Subject] = Field(default_factory=list)
    next_cursor: str | None = None
    fetched_at: str | None = None


class SubjectCreateRequest(_PermissiveModel):
    """Author-ergonomic shape of ``subject/create`` params.

    The host serializes top-level keys for ``subject/create``; this mirrors the
    Rust ``SubjectCreateRequest`` for typed author call sites.
    """

    kind: str
    title: str
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    assignee: str | None = None
    labels: list[str] = Field(default_factory=list)
    parent: str | None = None
    url: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)
