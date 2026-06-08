"""Public API for `animus-plugin-sdk`.

This is the back-compat top-level surface: the `define_plugin` entrypoint, the
base/runtime layer, and every role contract. Role-specific generated pydantic
types + contracts are ALSO importable per role:

    from animus_plugin_sdk.subject import SubjectBackend, gen as subject_types
    from animus_plugin_sdk.provider import Provider, AgentRunRequest
    from animus_plugin_sdk.trigger import TriggerBackend, TriggerEvent
    ... and `.transport`, `.log_storage`, `.queue`, `.workflow_runner`,
        `.durable_store`, `.memory_store`, `.notifier`.

The internal wire and handshake helpers are also exported for advanced/test use.
"""

from __future__ import annotations

from .handshake import (
    PluginIdentity,
    build_initialize_result,
    build_manifest,
    validate_initialize_params,
)
from .plugin import PluginHandle, PluginSpec, define_plugin, ensure_wire_subject
from .roles import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStream,
    CallContext,
    DurableStore,
    HealthReport,
    LogStorageBackend,
    MemoryStore,
    Notifier,
    Provider,
    ProviderCallContext,
    ProviderRunParams,
    ProviderRunResult,
    Queue,
    SubjectBackend,
    SubjectCallContext,
    TransportBackend,
    TriggerBackend,
    TriggerEvent,
    WorkflowRunner,
)
from .types import (
    PROTOCOL_VERSION,
    EnvRequirement,
    ErrorCode,
    HealthCheckResult,
    HealthStatus,
    HostCapabilities,
    HostInfo,
    InitializeParams,
    InitializeResult,
    McpTool,
    PluginCapabilities,
    PluginInfo,
    PluginKind,
    PluginKindString,
    PluginManifest,
    RpcError,
    RpcId,
    RpcNotification,
    RpcRequest,
    RpcResponse,
    Subject,
    SubjectCreateRequest,
    SubjectListParams,
    SubjectListResult,
    SubjectPatch,
    SubjectStatus,
)
from .wire import (
    Wire,
    create_wire,
    encode_frame,
    error_response,
    ok_response,
    parse_frame,
)

__version__ = "0.2.0"


__all__ = [
    "PROTOCOL_VERSION",
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentStream",
    "CallContext",
    "DurableStore",
    "EnvRequirement",
    "ErrorCode",
    "HealthCheckResult",
    "HealthReport",
    "HealthStatus",
    "HostCapabilities",
    "HostInfo",
    "InitializeParams",
    "InitializeResult",
    "LogStorageBackend",
    "McpTool",
    "MemoryStore",
    "Notifier",
    "PluginCapabilities",
    "PluginHandle",
    "PluginIdentity",
    "PluginInfo",
    "PluginKind",
    "PluginKindString",
    "PluginManifest",
    "PluginSpec",
    "Provider",
    "ProviderCallContext",
    "ProviderRunParams",
    "ProviderRunResult",
    "Queue",
    "RpcError",
    "RpcId",
    "RpcNotification",
    "RpcRequest",
    "RpcResponse",
    "Subject",
    "SubjectBackend",
    "SubjectCallContext",
    "SubjectCreateRequest",
    "SubjectListParams",
    "SubjectListResult",
    "SubjectPatch",
    "SubjectStatus",
    "TransportBackend",
    "TriggerBackend",
    "TriggerEvent",
    "Wire",
    "WorkflowRunner",
    "__version__",
    "build_initialize_result",
    "build_manifest",
    "create_wire",
    "define_plugin",
    "encode_frame",
    "ensure_wire_subject",
    "error_response",
    "ok_response",
    "parse_frame",
    "validate_initialize_params",
]
