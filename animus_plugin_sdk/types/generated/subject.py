# AUTO-GENERATED FROM schemas/animus-subject-protocol/_all.json — DO NOT EDIT BY HAND.
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


ChangeKind = Literal["created", "updated", "status-changed", "deleted", "dispatch-label-changed", "attachment-added", "attachment-removed"]


CustomFieldKind = Literal["string", "number", "bool", "enum", "date"]


class CustomFieldSpec(GeneratedModel):
    "Description of one custom field a backend exposes."
    key: str
    type: "CustomFieldKind"
    values: Optional[list[str]] = Field(default=None)


SubjectId = str


class DeleteSubjectRequest(GeneratedModel):
    "Request payload for `subject/delete`. Added in v0.1.8."
    id: "SubjectId"


class DeleteSubjectResponse(GeneratedModel):
    "Response payload for `subject/delete`. Added in v0.1.8."
    ok: bool


SubjectStatus = Literal["ready", "in-progress", "blocked", "done", "cancelled"]


class StatusDispatchHint(GeneratedModel):
    "A mapping from a backend-native status string to its normalized bucket"
    description: Optional[str] = Field(default=None)
    dispatch_label: Optional[str] = Field(default=None)
    maps_to: "SubjectStatus"
    native_status: str


class SubjectAttachment(GeneratedModel):
    "An attachment on a [`Subject`] \u2014 document, URL, file, comment thread, or"
    id: str
    kind: str
    metadata: Any = Field(default=None)
    mime_type: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    uri: str


class Subject(GeneratedModel):
    "A normalized cross-backend representation of a unit of dispatchable work."
    assignee: Optional[str] = Field(default=None)
    attachments: list["SubjectAttachment"] = Field(default_factory=list)
    children: list["SubjectId"] = Field(default_factory=list)
    created_at: str
    custom: dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = Field(default=None)
    id: "SubjectId"
    kind: str
    labels: list[str] = Field(default_factory=list)
    native_status: Optional[str] = Field(default=None)
    parent: Optional["SubjectId"] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=0, le=255)
    status: "SubjectStatus"
    status_metadata: Any = Field(default=None)
    title: str
    updated_at: str
    url: Optional[str] = Field(default=None)


class SubjectChangedEvent(GeneratedModel):
    "Notification payload for `subject/changed`."
    change_kind: "ChangeKind"
    id: "SubjectId"
    previous_dispatch_label: Optional[str] = Field(default=None)
    previous_native_status: Optional[str] = Field(default=None)
    subject: "Subject"


class SubjectFilter(GeneratedModel):
    "Filter passed to `subject/list`."
    assignee: list[str] = Field(default_factory=list)
    cursor: Optional[str] = Field(default=None)
    dispatch_label: Optional[str] = Field(default=None)
    has_attachment_kind: Optional[str] = Field(default=None)
    kind: list[str] = Field(default_factory=list)
    labels_all: list[str] = Field(default_factory=list)
    labels_any: list[str] = Field(default_factory=list)
    limit: Optional[int] = Field(default=None, ge=0)
    native_status: Optional[str] = Field(default=None)
    status: list["SubjectStatus"] = Field(default_factory=list)
    updated_since: Optional[str] = Field(default=None)


class SubjectList(GeneratedModel):
    "Result of `subject/list`."
    fetched_at: str
    next_cursor: Optional[str] = Field(default=None)
    subjects: list["Subject"]


class SubjectPatch(GeneratedModel):
    "A patch applied to a subject via `subject/update`."
    assignee: Optional[str] = Field(default=None)
    comment: Optional[str] = Field(default=None)
    custom: dict[str, Any] = Field(default_factory=dict)
    labels_add: list[str] = Field(default_factory=list)
    labels_remove: list[str] = Field(default_factory=list)
    status: Optional["SubjectStatus"] = Field(default=None)


class SubjectSchema(GeneratedModel):
    "Capability declaration returned by `subject/schema`."
    custom_fields: list["CustomFieldSpec"] = Field(default_factory=list)
    kinds: list[str]
    native_status_values: list[str] = Field(default_factory=list)
    status_dispatch_hints: list["StatusDispatchHint"] = Field(default_factory=list)
    status_values: list["SubjectStatus"]
    supports_create: bool
    supports_delete: Optional[bool] = Field(default=None)
    supports_pagination: bool
    supports_watch: bool


CustomFieldSpec.model_rebuild()
DeleteSubjectRequest.model_rebuild()
DeleteSubjectResponse.model_rebuild()
StatusDispatchHint.model_rebuild()
SubjectAttachment.model_rebuild()
Subject.model_rebuild()
SubjectChangedEvent.model_rebuild()
SubjectFilter.model_rebuild()
SubjectList.model_rebuild()
SubjectPatch.model_rebuild()
SubjectSchema.model_rebuild()
