"""Base / runtime protocol layer.

The wire-shape payload types (``PluginManifest``, ``PluginCapabilities``,
``InitializeParams``, ``InitializeResult``, ``HealthCheckResult``, …) are
re-exported from the generated pydantic module
(``animus_plugin_sdk.types.generated.plugin``) — the Rust protocol crates are
the single source of truth; regenerate via ``python scripts/codegen.py``.

This module adds the hand-maintained constants (``PROTOCOL_VERSION``,
``PluginKind``, ``ErrorCode``) and the JSON-RPC *envelope* types
(``RpcRequest`` / ``RpcNotification`` / ``RpcResponse`` / ``RpcError``), which
are transport contracts rather than domain payloads: the transport relies on
``jsonrpc`` defaulting to ``"2.0"`` and on distinguishing missing-``id`` from
explicit-``null`` via ``model_fields_set`` — neither of which the generated
permissive models guarantee. Their structural shape matches the generated
schema exactly.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# Re-export the generated wire-payload types so authors/handshake source the
# Rust-derived shapes. Aliased to the SDK's historical names where they differ.
from .generated.plugin import (
    EnvRequirement as EnvRequirement,
)
from .generated.plugin import (
    HealthCheckResult as HealthCheckResult,
)
from .generated.plugin import (
    HostCapabilities as HostCapabilities,
)
from .generated.plugin import (
    HostInfo as HostInfo,
)
from .generated.plugin import (
    InitializeParams as InitializeParams,
)
from .generated.plugin import (
    InitializeResult as InitializeResult,
)
from .generated.plugin import (
    KindCapability as KindCapability,
)
from .generated.plugin import (
    McpTool as McpTool,
)
from .generated.plugin import (
    PluginCapabilities as PluginCapabilities,
)
from .generated.plugin import (
    PluginInfo as PluginInfo,
)
from .generated.plugin import (
    PluginManifest as PluginManifest,
)

PROTOCOL_VERSION: Literal["1.1.0"] = "1.1.0"
"""Protocol version this SDK was built against. Mirrors the Rust
`PROTOCOL_VERSION` constant in `animus-plugin-protocol`. Match the TS SDK."""


PluginKindString = str
"""Plugin kind discriminator (kept as a string so unknown kinds round-trip)."""


HealthStatus = Literal["healthy", "degraded", "unhealthy"]
"""Health status emitted by `health/check`."""


class PluginKind:
    """Plugin kind constants (mirror Rust `PLUGIN_KIND_*` + the TS `PluginKind`)."""

    PROVIDER: PluginKindString = "provider"
    SUBJECT_BACKEND: PluginKindString = "subject_backend"
    TASK_BACKEND: PluginKindString = "task_backend"
    TRIGGER_BACKEND: PluginKindString = "trigger_backend"
    LOG_STORAGE_BACKEND: PluginKindString = "log_storage_backend"
    TRANSPORT_BACKEND: PluginKindString = "transport_backend"
    # v1.1.0 additive kinds.
    WORKFLOW_RUNNER: PluginKindString = "workflow_runner"
    QUEUE: PluginKindString = "queue"
    DURABLE_STORE: PluginKindString = "durable_store"
    MEMORY_STORE: PluginKindString = "memory_store"
    NOTIFIER: PluginKindString = "notifier"
    CUSTOM: PluginKindString = "custom"

    ALL: frozenset[str] = frozenset(
        {
            "provider",
            "subject_backend",
            "task_backend",
            "trigger_backend",
            "log_storage_backend",
            "transport_backend",
            "workflow_runner",
            "queue",
            "durable_store",
            "memory_store",
            "notifier",
            "custom",
        }
    )


class ErrorCode:
    """JSON-RPC 2.0 standard + Animus-specific error codes (spec §4)."""

    PARSE_ERROR: int = -32700
    INVALID_REQUEST: int = -32600
    METHOD_NOT_FOUND: int = -32601
    INVALID_PARAMS: int = -32602
    INTERNAL_ERROR: int = -32603
    # Domain method received before `initialize` completed.
    PLUGIN_NOT_INITIALIZED: int = -32000
    # Method is recognized but not implemented (host should fall back).
    METHOD_NOT_SUPPORTED: int = -32001
    # Host cancelled the request via `$/cancelRequest`.
    REQUEST_CANCELLED: int = -32002
    # Request did not complete within the host-imposed timeout.
    TIMEOUT: int = -32003
    # Animus-specific: plugin shutting down.
    SERVER_SHUTDOWN: int = -32099


# JSON-RPC 2.0 envelope types ------------------------------------------------

RpcId = str | int | None
"""JSON-RPC 2.0 request id — per spec a string, number, or null."""


class _EnvelopeModel(BaseModel):
    """Base for the JSON-RPC envelope types — extra fields preserved."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RpcRequest(_EnvelopeModel):
    """A JSON-RPC 2.0 request frame (transport envelope)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    id: RpcId = None
    params: Any | None = None


class RpcNotification(_EnvelopeModel):
    """A JSON-RPC 2.0 notification frame (transport envelope)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Any | None = None


class RpcError(_EnvelopeModel):
    """JSON-RPC 2.0 error payload (transport envelope)."""

    code: int
    message: str
    data: Any | None = None


class RpcResponse(_EnvelopeModel):
    """A JSON-RPC 2.0 response frame (transport envelope)."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: RpcId = None
    result: Any | None = None
    error: RpcError | None = None


__all__ = [
    "PROTOCOL_VERSION",
    "EnvRequirement",
    "ErrorCode",
    "HealthCheckResult",
    "HealthStatus",
    "HostCapabilities",
    "HostInfo",
    "InitializeParams",
    "InitializeResult",
    "KindCapability",
    "McpTool",
    "PluginCapabilities",
    "PluginInfo",
    "PluginKind",
    "PluginKindString",
    "PluginManifest",
    "RpcError",
    "RpcId",
    "RpcNotification",
    "RpcRequest",
    "RpcResponse",
]
