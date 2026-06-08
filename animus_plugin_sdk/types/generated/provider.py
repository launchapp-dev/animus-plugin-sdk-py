# AUTO-GENERATED FROM schemas/animus-provider-protocol/_all.json — DO NOT EDIT BY HAND.
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


class AgentCancelRequest(GeneratedModel):
    "Parameters for an `agent/cancel` call."
    session_id: str


class AgentNotificationVariant0(GeneratedModel):
    "Incremental text the model has produced. Maps to"
    is_final: Optional[bool] = Field(default=None)
    kind: Literal["output"]
    session_id: str
    text: str

class AgentNotificationVariant1(GeneratedModel):
    "Visible reasoning from the model. Maps to"
    kind: Literal["thinking"]
    session_id: str
    text: str

class AgentNotificationVariant2(GeneratedModel):
    "Agent invoked a tool. Maps to [`NOTIFICATION_AGENT_TOOL_CALL`]."
    arguments: Any
    kind: Literal["toolCall"]
    name: str
    server: Optional[str] = Field(default=None)
    session_id: str

class AgentNotificationVariant3(GeneratedModel):
    "Tool returned a result. Maps to [`NOTIFICATION_AGENT_TOOL_RESULT`]."
    kind: Literal["toolResult"]
    name: str
    output: Any
    session_id: str
    success: bool

class AgentNotificationVariant4(GeneratedModel):
    "Error encountered mid-run. Maps to [`NOTIFICATION_AGENT_ERROR`]."
    kind: Literal["error"]
    message: str
    recoverable: bool
    session_id: str

AgentNotification = Union[AgentNotificationVariant0, AgentNotificationVariant1, AgentNotificationVariant2, AgentNotificationVariant3, AgentNotificationVariant4]


class AgentRunRequest(GeneratedModel):
    "Parameters for an `agent/run` (or `agent/resume`) call."
    cwd: str
    env: dict[str, str] = Field(default_factory=dict)
    mcp_servers: Any = Field(default=None)
    model: Optional[str] = Field(default=None)
    permission_mode: Optional[str] = Field(default=None)
    project_root: Optional[str] = Field(default=None)
    prompt: str
    response_schema: Any = Field(default=None)
    runtime_contract: Any = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    system_prompt: Optional[str] = Field(default=None)
    timeout_secs: Optional[int] = Field(default=None, ge=0)
    tools: Any = Field(default=None)


class TokenUsage(GeneratedModel):
    "Token-accounting summary for an agent run."
    cache_writes: Optional[int] = Field(default=None, ge=0)
    cached: Optional[int] = Field(default=None, ge=0)
    input: int = Field(ge=0)
    output: int = Field(ge=0)


class AgentRunResponse(GeneratedModel):
    "Final response to `agent/run` or `agent/resume`."
    backend: str
    decision_verdict: Any = Field(default=None)
    duration_ms: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)
    exit_code: int
    metadata: list[Any] = Field(default_factory=list)
    output: str
    session_id: str
    thinking: list[str] = Field(default_factory=list)
    tokens_used: Optional["TokenUsage"] = Field(default=None)
    tool_calls: list[Any] = Field(default_factory=list)
    tool_results: list[Any] = Field(default_factory=list)


class ProviderCapabilities(GeneratedModel):
    "Provider capability flags."
    cancellation: Optional[bool] = Field(default=None)
    mcp: Optional[bool] = Field(default=None)
    resume: Optional[bool] = Field(default=None)
    streaming: Optional[bool] = Field(default=None)
    write_capable: Optional[bool] = Field(default=None)


class ProviderManifest(GeneratedModel):
    "Static manifest describing what a provider plugin supports."
    capabilities: "ProviderCapabilities"
    description: str
    name: str
    supported_models: list[str]
    tool: str
    version: str


AgentCancelRequest.model_rebuild()
AgentRunRequest.model_rebuild()
TokenUsage.model_rebuild()
AgentRunResponse.model_rebuild()
ProviderCapabilities.model_rebuild()
ProviderManifest.model_rebuild()
