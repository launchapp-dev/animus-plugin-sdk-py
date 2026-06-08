# AUTO-GENERATED FROM schemas/animus-trigger-protocol/_all.json — DO NOT EDIT BY HAND.
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


class TriggerEvent(GeneratedModel):
    "One event emitted by a trigger backend."
    action_hint: Optional[str] = Field(default=None)
    id: str
    kind: str
    occurred_at: str
    payload: Any
    subject_id: Optional[str] = Field(default=None)


class TriggerSchema(GeneratedModel):
    "Capability declaration returned by [`METHOD_TRIGGER_SCHEMA`]."
    kinds: list[str]
    supports_ack: bool
    supports_dedup: bool
    supports_resume: bool


TriggerEvent.model_rebuild()
TriggerSchema.model_rebuild()
