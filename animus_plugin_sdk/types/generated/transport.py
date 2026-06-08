# AUTO-GENERATED FROM schemas/animus-transport-protocol/_all.json — DO NOT EDIT BY HAND.
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


class TransportConfig(GeneratedModel):
    "Configuration handed to a transport plugin on [`TRANSPORT_METHOD_START`]."
    bind_addr: Optional[str] = Field(default=None)
    config: Any = Field(default=None)
    control_socket_path: str
    project_root: str


class TransportInfo(GeneratedModel):
    "Reply returned by [`TransportBackend::start`] once the listener is bound."
    bound_addr: str
    started_at: str


class TransportSchema(GeneratedModel):
    "Capability declaration returned by [`TRANSPORT_METHOD_SCHEMA`]."
    default_port: Optional[int] = Field(default=None, ge=0, le=65535)
    kinds: list[str]
    supports_streaming: bool
    supports_websocket: bool


TransportConfig.model_rebuild()
TransportInfo.model_rebuild()
TransportSchema.model_rebuild()
