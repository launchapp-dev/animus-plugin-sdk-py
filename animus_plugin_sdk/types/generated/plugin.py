# AUTO-GENERATED FROM schemas/animus-plugin-protocol/_all.json — DO NOT EDIT BY HAND.
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


class EnvRequirement(GeneratedModel):
    "One environment variable a plugin asks the host to forward at spawn time."
    description: Optional[str] = Field(default=None)
    name: str
    required: Optional[bool] = Field(default=None)
    sensitive: Optional[bool] = Field(default=None)


HealthStatus = Literal["healthy", "degraded", "unhealthy"]


class HealthCheckResult(GeneratedModel):
    "Response to `health/check`."
    last_error: Optional[str] = Field(default=None)
    memory_usage_bytes: Optional[int] = Field(default=None, ge=0)
    status: "HealthStatus"
    uptime_ms: Optional[int] = Field(default=None, ge=0)


class HostCapabilities(GeneratedModel):
    "Capabilities the host advertises during the handshake."
    cancellation: Optional[bool] = Field(default=None)
    progress: Optional[bool] = Field(default=None)
    streaming: Optional[bool] = Field(default=None)


class HostInfo(GeneratedModel):
    "Identity of the host issuing the `initialize` call."
    name: str
    version: str


class InitializeParams(GeneratedModel):
    "Parameters sent from host to plugin in the `initialize` request."
    capabilities: "HostCapabilities"
    host_info: "HostInfo"
    init_extensions: dict[str, Any] = Field(default_factory=dict)
    protocol_version: str


class KindCapability(GeneratedModel):
    "Typed per-kind capability declaration carried in"
    crate_version: str
    extra: Any = Field(default=None)


class McpTool(GeneratedModel):
    "Description of an MCP tool exposed by a custom plugin."
    description: Optional[str] = Field(default=None)
    input_schema: Any = Field(default=None)
    name: str


class PluginCapabilities(GeneratedModel):
    "Capabilities the plugin advertises during the handshake."
    cancellation: Optional[bool] = Field(default=None)
    mcp_tools: list["McpTool"] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    progress: Optional[bool] = Field(default=None)
    projections: list[str] = Field(default_factory=list)
    streaming: Optional[bool] = Field(default=None)
    subject_kinds: list[str] = Field(default_factory=list)


class PluginInfo(GeneratedModel):
    "Identity of the plugin returned in the `initialize` response."
    description: Optional[str] = Field(default=None)
    name: str
    plugin_kind: str
    version: str


class InitializeResult(GeneratedModel):
    "Plugin's response to `initialize`."
    capabilities: "PluginCapabilities"
    kind_capabilities: dict[str, "KindCapability"] = Field(default_factory=dict)
    plugin_info: "PluginInfo"
    protocol_version: str


class PluginManifest(GeneratedModel):
    "One-shot manifest emitted when a plugin is invoked with `--manifest`."
    capabilities: list[str] = Field(default_factory=list)
    description: str
    env_required: list["EnvRequirement"] = Field(default_factory=list)
    name: str
    notification_buffer_size: Optional[int] = Field(default=None, ge=0)
    plugin_kind: str
    protocol_version: str
    version: str


class RpcError(GeneratedModel):
    "JSON-RPC 2.0 error payload."
    code: int
    data: Any = Field(default=None)
    message: str


class RpcNotification(GeneratedModel):
    "A JSON-RPC 2.0 notification frame."
    jsonrpc: str
    method: str
    params: Any = Field(default=None)


class RpcRequest(GeneratedModel):
    "A JSON-RPC 2.0 request frame."
    id: Any = Field(default=None)
    jsonrpc: str
    method: str
    params: Any = Field(default=None)


class RpcResponse(GeneratedModel):
    "A JSON-RPC 2.0 response frame."
    error: Optional["RpcError"] = Field(default=None)
    id: Any = Field(default=None)
    jsonrpc: str
    result: Any = Field(default=None)


# Open-string enum (known values: dispatched, queued, unmatched, skipped, failed, shutdown); unknown values round-trip as str.
TriggerAckStatus = str


class TriggerAckParams(GeneratedModel):
    "Parameters sent from host to plugin in the `trigger/ack` notification."
    event_id: str
    status: Optional["TriggerAckStatus"] = Field(default=None)


# Open-string enum (known values: create_task, run_workflow); unknown values round-trip as str.
TriggerActionHint = str


class TriggerEvent(GeneratedModel):
    "A trigger event emitted by a trigger backend plugin."
    action_hint: Optional["TriggerActionHint"] = Field(default=None)
    event_id: str
    payload: Any = Field(default=None)
    subject_id: Optional[str] = Field(default=None)
    subject_kind: Optional[str] = Field(default=None)
    trigger_id: Optional[str] = Field(default=None)


class TriggerWatchParams(GeneratedModel):
    "Parameters sent from host to plugin in the `trigger/watch` request."
    config: Any = Field(default=None)
    cursor: Any = Field(default=None)


EnvRequirement.model_rebuild()
HealthCheckResult.model_rebuild()
HostCapabilities.model_rebuild()
HostInfo.model_rebuild()
InitializeParams.model_rebuild()
KindCapability.model_rebuild()
McpTool.model_rebuild()
PluginCapabilities.model_rebuild()
PluginInfo.model_rebuild()
InitializeResult.model_rebuild()
PluginManifest.model_rebuild()
RpcError.model_rebuild()
RpcNotification.model_rebuild()
RpcRequest.model_rebuild()
RpcResponse.model_rebuild()
TriggerAckParams.model_rebuild()
TriggerEvent.model_rebuild()
TriggerWatchParams.model_rebuild()
