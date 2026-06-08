"""provider role contract (spec §7.2 / §10).

A provider runs an agent session. ``run`` / ``resume`` stream
``agent/output|thinking|toolCall|toolResult|error`` notifications via the
``ctx.stream`` sink and then return the final ``AgentRunResponse``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..types.generated import provider as gen
from .context import CallContext, HealthReport

AgentRunRequest = gen.AgentRunRequest
AgentRunResponse = gen.AgentRunResponse
AgentCancelRequest = gen.AgentCancelRequest
AgentNotification = gen.AgentNotification
TokenUsage = gen.TokenUsage
ProviderCapabilities = gen.ProviderCapabilities


class AgentStream(Protocol):
    """Streaming sink handed to provider `run`/`resume` impls. Each method maps
    to the matching `agent/*` JSON-RPC notification (spec §10.3). Every variant
    carries `session_id`; the SDK defaults it from the originating request's
    session id when the author omits it."""

    def output(self, *, text: str, session_id: str | None = ..., final: bool = ...) -> None: ...
    def thinking(self, *, text: str, session_id: str | None = ...) -> None: ...
    def tool_call(
        self,
        *,
        name: str,
        arguments: Any = ...,
        server: str | None = ...,
        session_id: str | None = ...,
    ) -> None: ...
    def tool_result(
        self,
        *,
        name: str,
        output: str = ...,
        success: bool = ...,
        session_id: str | None = ...,
    ) -> None: ...
    def error(
        self,
        *,
        message: str,
        recoverable: bool = ...,
        session_id: str | None = ...,
    ) -> None: ...


@dataclass
class ProviderCallContext(CallContext):
    """Provider call context adds the streaming sink."""

    stream: AgentStream | None = None


@runtime_checkable
class Provider(Protocol):
    """Runs agent sessions.

    Required: `run`. Optional: `resume`, `cancel`, `health`.
    """

    def run(
        self,
        params: AgentRunRequest,
        ctx: ProviderCallContext,
    ) -> AgentRunResponse | dict[str, Any]: ...

    # Optional:
    # def resume(self, params: AgentRunRequest, ctx: ProviderCallContext) -> AgentRunResponse: ...
    # def cancel(self, params: AgentCancelRequest, ctx: CallContext) -> dict[str, Any]: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


@dataclass
class ProviderRunParams:
    """Deprecated. The provider contract now uses the generated `AgentRunRequest`.

    Kept so historical `from animus_plugin_sdk.roles import ProviderRunParams`
    imports keep working.
    """

    prompt: str
    cwd: str
    model: str | None = None
    session_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderRunResult:
    """Deprecated. The provider contract now uses the generated `AgentRunResponse`."""

    session_id: str
    output: str
    exit_code: int
    duration_ms: int
    extra: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "AgentCancelRequest",
    "AgentNotification",
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentStream",
    "HealthReport",
    "Provider",
    "ProviderCallContext",
    "ProviderCapabilities",
    "ProviderRunParams",
    "ProviderRunResult",
    "TokenUsage",
]
