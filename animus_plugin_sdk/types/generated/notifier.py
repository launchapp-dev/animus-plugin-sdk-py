# AUTO-GENERATED FROM schemas/animus-notifier-protocol/_all.json — DO NOT EDIT BY HAND.
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


class DaemonEventRecord(GeneratedModel):
    "Wire shape of one daemon event record forwarded to notifiers."
    data: Any
    event_type: str
    id: str
    project_root: Optional[str] = Field(default=None)
    schema_: str = Field(alias="schema")
    seq: Optional[int] = Field(default=None, ge=0)
    timestamp: str


class NotifierFlushParams(GeneratedModel):
    "Parameters for [`METHOD_NOTIFIER_FLUSH`]."
    project_root: Optional[str] = Field(default=None)


class NotifierLifecycleEvent(GeneratedModel):
    "Lifecycle record emitted by a notifier plugin so the daemon can mirror"
    data: Any
    event_type: str
    project_root: Optional[str] = Field(default=None)


class NotifierFlushResult(GeneratedModel):
    "Result for [`METHOD_NOTIFIER_FLUSH`]."
    lifecycle_events: list["NotifierLifecycleEvent"] = Field(default_factory=list)


class NotifierNotifyParams(GeneratedModel):
    "Parameters for [`METHOD_NOTIFIER_NOTIFY`]."
    event: "DaemonEventRecord"


class NotifierNotifyResult(GeneratedModel):
    "Result for [`METHOD_NOTIFIER_NOTIFY`]."
    accepted: bool
    delivered: Optional[int] = Field(default=None, ge=0)
    lifecycle_events: list["NotifierLifecycleEvent"] = Field(default_factory=list)


class NotifierSchema(GeneratedModel):
    "Capability declaration returned by [`METHOD_NOTIFIER_SCHEMA`]."
    connector_kinds: list[str]
    supports_flush: bool


DaemonEventRecord.model_rebuild()
NotifierFlushParams.model_rebuild()
NotifierLifecycleEvent.model_rebuild()
NotifierFlushResult.model_rebuild()
NotifierNotifyParams.model_rebuild()
NotifierNotifyResult.model_rebuild()
NotifierSchema.model_rebuild()
