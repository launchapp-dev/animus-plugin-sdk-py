"""`define_plugin(...)` — single entrypoint for authoring an Animus plugin.

Authors describe their plugin (identity + role + impl) and the SDK:

  1. handles the `--manifest` CLI shortcut
  2. runs the stdio JSON-RPC loop
  3. dispatches lifecycle methods (initialize / $/ping / health/check /
     shutdown / exit)
  4. validates inbound domain params with the generated pydantic models and
     routes them to the author's `impl`
  5. forwards unknown methods as MethodNotFound

All plugin roles from spec.md §7 are wired: subject_backend, trigger_backend,
provider, log_storage_backend, transport_backend, queue, workflow_runner,
durable_store, memory_store, notifier.

Streaming concurrency: the wire read loop is synchronous and serial. Streaming
roles (trigger/watch, log_storage/tail) ack immediately and drain the author's
iterator on a background daemon thread, emitting notifications via the wire
whose stdout writes are serialized by a lock — so the synchronous subject path
and per-frame stdout framing are never disturbed. Provider streaming runs
inline on the dispatch thread (the impl emits via `ctx.stream` before returning
the final response).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import IO, Any

from .dispatch.durable_store import dispatch_durable_store
from .dispatch.log_storage import dispatch_log_storage
from .dispatch.memory_store import dispatch_memory_store
from .dispatch.notifier import derive_notifier_capabilities, dispatch_notifier
from .dispatch.provider import (
    PROVIDER_METHODS,
    ProviderSessionRegistry,
    dispatch_provider,
)
from .dispatch.queue import (
    QUEUE_METHODS,
    QUEUE_RELEASE_PENDING,
    dispatch_queue,
)
from .dispatch.subject import (
    derive_subject_capabilities,
    dispatch_subject,
    ensure_wire_subject,
)
from .dispatch.transport import TRANSPORT_METHODS, dispatch_transport
from .dispatch.trigger import derive_trigger_capabilities, dispatch_trigger
from .dispatch.workflow_runner import WORKFLOW_RUNNER_METHODS, dispatch_workflow_runner
from .handshake import (
    PluginIdentity,
    build_initialize_result,
    build_manifest,
    validate_initialize_params,
)
from .roles.context import CallContext, HealthReport
from .types import (
    EnvRequirement,
    ErrorCode,
    HealthCheckResult,
    InitializeParams,
    PluginCapabilities,
    PluginKind,
    PluginManifest,
    RpcId,
    RpcRequest,
    RpcResponse,
)
from .wire import Wire, create_wire, error_response, ok_response

# Per-kind protocol crate versions for the v1.1.0 kinds (advertised via
# `kind_capabilities`). v1.0.0 kinds leave this empty so the wire output stays
# byte-identical to the pre-v1.1.0 shape.
_KIND_CAPABILITY_KEYS = {
    PluginKind.WORKFLOW_RUNNER: "workflow_runner",
    PluginKind.QUEUE: "queue",
    PluginKind.DURABLE_STORE: "durable_store",
    PluginKind.MEMORY_STORE: "memory_store",
    PluginKind.NOTIFIER: "notifier",
}

# Required methods enforced at construction time per role.
_REQUIRED_METHODS: dict[str, list[str]] = {
    PluginKind.SUBJECT_BACKEND: ["list", "get"],
    PluginKind.TRIGGER_BACKEND: ["watch"],
    PluginKind.PROVIDER: ["run"],
    PluginKind.TRANSPORT_BACKEND: ["start"],
    PluginKind.LOG_STORAGE_BACKEND: ["store"],
    PluginKind.QUEUE: [
        "enqueue",
        "list",
        "lease",
        "stats",
        "hold",
        "release",
        "drop",
        "mark_assigned",
        "completion",
        "reorder",
    ],
    PluginKind.WORKFLOW_RUNNER: ["execute", "run_phase"],
    PluginKind.DURABLE_STORE: [
        "begin_workflow_run",
        "begin_step",
        "commit_step",
        "abandon_step",
        "recover_in_flight",
        "query_run",
    ],
    PluginKind.MEMORY_STORE: ["put", "get", "query", "list_scopes", "delete_scope"],
    PluginKind.NOTIFIER: ["notify"],
}


@dataclass
class PluginSpec:
    """Author-supplied plugin description."""

    kind: str
    impl: Any
    name: str
    version: str
    description: str
    subject_kinds: list[str] = field(default_factory=list)
    projections: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    env_required: list[EnvRequirement] = field(default_factory=list)
    extra_capabilities: list[str] = field(default_factory=list)
    notification_buffer_size: int | None = None
    # Test hooks (mirror TS SDK `input`/`output`/`skipCliArgs`).
    input: IO[str] | None = None
    output: IO[str] | None = None
    skip_cli_args: bool = False


@dataclass
class PluginHandle:
    """Returned from `define_plugin`. Drive `.run()` to enter the JSON-RPC loop."""

    _spec: PluginSpec
    _identity: PluginIdentity
    _capabilities: PluginCapabilities
    _manifest: PluginManifest
    _kind_capabilities: dict[str, Any]

    def manifest(self) -> PluginManifest:
        """Static manifest for this plugin (also what `--manifest` prints)."""
        return self._manifest

    def initialize(self, params: InitializeParams) -> RpcResponse:
        """Build the `initialize` reply (exposed for tests)."""
        incompat = validate_initialize_params(params)
        if incompat:
            return error_response(None, ErrorCode.INVALID_REQUEST, incompat)
        return ok_response(
            None,
            _initialize_result_payload(self._identity, self._capabilities, self._kind_capabilities),
        )

    def run(self) -> None:
        """Drive the JSON-RPC loop until the input stream closes."""
        _run_loop(
            self._spec, self._manifest, self._identity, self._capabilities, self._kind_capabilities
        )


def _has_method(impl: Any, name: str) -> bool:
    return callable(getattr(impl, name, None))


def _derive_capabilities(spec: PluginSpec) -> PluginCapabilities:
    impl = spec.impl
    if spec.kind == PluginKind.SUBJECT_BACKEND:
        return derive_subject_capabilities(impl, list(spec.subject_kinds), list(spec.projections))
    if spec.kind == PluginKind.TRIGGER_BACKEND:
        return derive_trigger_capabilities(impl, list(spec.capabilities))
    if spec.kind == PluginKind.PROVIDER:
        methods = [PROVIDER_METHODS["run"], "health/check"]
        if _has_method(impl, "resume"):
            methods.append(PROVIDER_METHODS["resume"])
        if _has_method(impl, "cancel"):
            methods.append(PROVIDER_METHODS["cancel"])
        # `cancellation` advertises `$/cancelRequest` support, which the SDK now
        # wires: a `$/cancelRequest` for an in-flight run sets the session's
        # cancel token and resolves the run with `-32002`. `agent/cancel` (in
        # `methods` when the impl provides it) is the session-scoped surface.
        return PluginCapabilities(
            methods=methods, streaming=True, progress=False, cancellation=True
        )
    if spec.kind == PluginKind.LOG_STORAGE_BACKEND:
        methods = ["log_storage/store", "log_storage/schema", "health/check"]
        if _has_method(impl, "query"):
            methods.append("log_storage/query")
        tail = _has_method(impl, "tail")
        if tail:
            methods.append("log_storage/tail")
        return PluginCapabilities(
            methods=methods, streaming=tail, progress=False, cancellation=False
        )
    if spec.kind == PluginKind.TRANSPORT_BACKEND:
        methods = [
            TRANSPORT_METHODS["start"],
            TRANSPORT_METHODS["shutdown"],
            TRANSPORT_METHODS["schema"],
            "health/check",
        ]
        return PluginCapabilities(
            methods=methods, streaming=False, progress=False, cancellation=False
        )
    if spec.kind == PluginKind.QUEUE:
        methods = [*QUEUE_METHODS.values(), "health/check"]
        if _has_method(impl, "release_pending"):
            methods.append(QUEUE_RELEASE_PENDING)
        return PluginCapabilities(
            methods=methods, streaming=False, progress=False, cancellation=False
        )
    if spec.kind == PluginKind.WORKFLOW_RUNNER:
        return PluginCapabilities(
            methods=[*WORKFLOW_RUNNER_METHODS.values(), "health/check"],
            streaming=False,
            progress=False,
            cancellation=False,
        )
    if spec.kind == PluginKind.DURABLE_STORE:
        from .dispatch.durable_store import DURABLE_STORE_METHODS

        return PluginCapabilities(
            methods=[*DURABLE_STORE_METHODS.values(), "health/check"],
            streaming=False,
            progress=False,
            cancellation=False,
        )
    if spec.kind == PluginKind.MEMORY_STORE:
        from .dispatch.memory_store import MEMORY_STORE_METHODS

        return PluginCapabilities(
            methods=[*MEMORY_STORE_METHODS.values(), "health/check"],
            streaming=False,
            progress=False,
            cancellation=False,
        )
    if spec.kind == PluginKind.NOTIFIER:
        return derive_notifier_capabilities(impl)
    return PluginCapabilities(methods=[])


def _validate_spec(spec: PluginSpec) -> None:
    if not spec.name:
        raise TypeError("define_plugin: `name` is required")
    if not spec.version:
        raise TypeError("define_plugin: `version` is required")
    if not spec.description:
        raise TypeError("define_plugin: `description` is required")
    if not spec.kind:
        raise TypeError("define_plugin: `kind` is required")
    if spec.kind not in PluginKind.ALL:
        raise TypeError(f"define_plugin: unknown kind '{spec.kind}'")
    if spec.impl is None:
        raise TypeError("define_plugin: `impl` is required")
    if spec.kind == PluginKind.TASK_BACKEND:
        # `task_backend` is a legacy kind with no dispatcher (subjects with
        # `kind=task` use `subject_backend`). Fail fast rather than accept a
        # plugin whose every domain method would return MethodNotFound.
        raise TypeError(
            "define_plugin: kind 'task_backend' is not a dispatchable role; "
            "use kind='subject_backend' with subject_kinds=['task']"
        )
    required = _REQUIRED_METHODS.get(spec.kind)
    if required is None:
        # No SDK-side dispatch path exists for `custom` (the host surfaces its
        # domain methods opaquely via `animus.plugin.call`) or any unhandled
        # kind, so the dispatcher would only ever return MethodNotFound. Fail
        # fast, matching the TS SDK's `validateSpec` default.
        raise TypeError(
            f"define_plugin: kind '{spec.kind}' has no SDK dispatcher; "
            "custom domain methods are not wired by this SDK"
        )
    for m in required:
        if not _has_method(spec.impl, m):
            raise TypeError(f"{spec.kind} impl must implement {m}()")


def define_plugin(
    kind: str,
    impl: Any,
    *,
    name: str,
    version: str,
    description: str,
    subject_kinds: list[str] | None = None,
    projections: list[str] | None = None,
    capabilities: list[str] | None = None,
    env_required: list[EnvRequirement] | list[str] | None = None,
    extra_capabilities: list[str] | None = None,
    notification_buffer_size: int | None = None,
    input: IO[str] | None = None,
    output: IO[str] | None = None,
    skip_cli_args: bool = False,
) -> PluginHandle:
    """Author-facing entrypoint.

    Example::

        define_plugin(
            kind="subject_backend",
            impl=MySubjectBackend(),
            name="hello-subjects",
            version="0.1.0",
            description="Hard-coded sample backend",
            subject_kinds=["task"],
            env_required=["MY_API_TOKEN"],
        ).run()
    """
    # Allow plain-string env_required for ergonomic call sites. The string form
    # means "the plugin needs this var", so mark it `required=True` explicitly
    # (the generated model's `required` defaults to None and would otherwise be
    # dropped from the manifest by `exclude_none`).
    normalized_env: list[EnvRequirement] = []
    for entry in env_required or []:
        if isinstance(entry, str):
            normalized_env.append(EnvRequirement(name=entry, required=True))
        else:
            # Preserve the historical public-API default: an EnvRequirement with
            # an unset `required` is treated as required (the generated model
            # leaves it None, which would otherwise drop from the manifest).
            if getattr(entry, "required", None) is None:
                entry = entry.model_copy(update={"required": True})
            normalized_env.append(entry)

    spec = PluginSpec(
        kind=kind,
        impl=impl,
        name=name,
        version=version,
        description=description,
        subject_kinds=list(subject_kinds or []),
        projections=list(projections or []),
        capabilities=list(capabilities or []),
        env_required=normalized_env,
        extra_capabilities=list(extra_capabilities or []),
        notification_buffer_size=notification_buffer_size,
        input=input,
        output=output,
        skip_cli_args=skip_cli_args,
    )
    _validate_spec(spec)
    identity = PluginIdentity(
        name=spec.name,
        version=spec.version,
        description=spec.description,
        plugin_kind=spec.kind,
    )
    capabilities_obj = _derive_capabilities(spec)

    # Manifest-only capability tokens that aid host preflight without spawning.
    extra_caps: list[str] = []
    if spec.kind == PluginKind.SUBJECT_BACKEND:
        for k in spec.subject_kinds:
            extra_caps.append(f"subject_kind:{k}")
    if spec.kind == PluginKind.TRANSPORT_BACKEND:
        extra_caps.extend(spec.capabilities)
    extra_caps.extend(spec.extra_capabilities)

    kind_capabilities = _derive_kind_capabilities(spec)

    manifest = build_manifest(
        identity,
        capabilities_obj,
        env_required=spec.env_required,
        notification_buffer_size=spec.notification_buffer_size,
        extra_capabilities=extra_caps,
    )
    return PluginHandle(
        _spec=spec,
        _identity=identity,
        _capabilities=capabilities_obj,
        _manifest=manifest,
        _kind_capabilities=kind_capabilities,
    )


def _derive_kind_capabilities(spec: PluginSpec) -> dict[str, Any]:
    key = _KIND_CAPABILITY_KEYS.get(spec.kind)
    if not key:
        return {}
    return {key: {"crate_version": "0.1.0", "extra": {}}}


# ---- run loop --------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _initialize_result_payload(
    identity: PluginIdentity,
    capabilities: PluginCapabilities,
    kind_capabilities: dict[str, Any],
) -> dict[str, Any]:
    result = build_initialize_result(identity, capabilities, kind_capabilities)
    payload = result.model_dump(exclude_none=True, by_alias=True)
    # Drop an empty `kind_capabilities` so v1.0.0 kinds stay byte-identical to
    # the pre-v1.1.0 wire shape.
    if not payload.get("kind_capabilities"):
        payload.pop("kind_capabilities", None)
    return payload


def _build_health_ok() -> dict[str, Any]:
    return HealthCheckResult(status="healthy").model_dump(exclude_none=False, by_alias=True)


def _run_loop(
    spec: PluginSpec,
    manifest_payload: PluginManifest,
    identity: PluginIdentity,
    capabilities: PluginCapabilities,
    kind_capabilities: dict[str, Any],
) -> None:
    if not spec.skip_cli_args:
        args = sys.argv[1:]
        if "--manifest" in args or "-m" in args:
            payload = manifest_payload.model_dump(exclude_none=True, by_alias=True)
            sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
            sys.stdout.flush()
            sys.exit(0)
        if "--help" in args or "-h" in args:
            sys.stderr.write(
                f"{identity.name} {identity.version} - Animus STDIO plugin\n"
                "Usage:\n"
                f"  {identity.name} --manifest    Print plugin manifest as JSON and exit\n"
                f"  {identity.name}               Run JSON-RPC loop on stdin/stdout\n"
            )
            sys.exit(0)

    wire = create_wire(input=spec.input, output=spec.output)

    # One session registry per plugin instance. Only provider plugins populate
    # it (run/resume register; agent/cancel + $/cancelRequest interrupt).
    provider_sessions = ProviderSessionRegistry()

    def handler(frame: RpcRequest) -> RpcResponse | None:
        return _dispatch(
            frame, wire, spec, identity, capabilities, kind_capabilities, provider_sessions
        )

    wire.run(handler)


# ---- dispatch --------------------------------------------------------------


def _dispatch(
    frame: RpcRequest,
    wire: Wire,
    spec: PluginSpec,
    identity: PluginIdentity,
    capabilities: PluginCapabilities,
    kind_capabilities: dict[str, Any],
    provider_sessions: ProviderSessionRegistry,
) -> RpcResponse | None:
    request_id = frame.id
    method = frame.method

    # Notifications (no `id`): never respond. Per JSON-RPC 2.0 only a missing
    # `id` makes a frame a notification; `id: null` is still a request.
    is_notification = (
        request_id is None
        and "id" not in (frame.model_extra or {})
        and frame.model_fields_set.isdisjoint({"id"})
    )
    if is_notification:
        if method == "exit":
            sys.exit(0)
        # `trigger/ack` is spec'd as a host→plugin notification (no id). Route it
        # to a trigger backend that advertises `ack` so it can persist delivery
        # state; the impl's return value is discarded (no reply for a
        # notification). Other notifications (`initialized`, `$/cancelRequest`,
        # `$/progress`, unknown) are dropped.
        if method == "trigger/ack" and spec.kind == PluginKind.TRIGGER_BACKEND:
            dispatch_trigger(None, frame, wire, spec.impl)
            return None
        # `$/cancelRequest` (spec §6.3): for a provider, best-effort cancel the
        # in-flight run started by that request id. The detached run then
        # resolves with `-32002` (request_cancelled). No-op for other roles.
        if method == "$/cancelRequest" and spec.kind == PluginKind.PROVIDER:
            params = frame.params if isinstance(frame.params, dict) else {}
            cancel_id = params.get("id")
            if cancel_id is not None:
                provider_sessions.cancel_by_request(cancel_id)
        return None

    if method == "initialize":
        params_raw = frame.params if isinstance(frame.params, dict) else {}
        # Tolerate v1.0 / older hosts that omit `capabilities` on initialize:
        # the generated model marks it required, but the SDK keeps the handshake
        # lenient (an absent capabilities block means "no host capabilities").
        if "capabilities" not in params_raw:
            params_raw = {**params_raw, "capabilities": {}}
        try:
            init_params = InitializeParams.model_validate(params_raw)
        except Exception as exc:
            return error_response(
                request_id,
                ErrorCode.INVALID_PARAMS,
                f"invalid initialize params: {exc!s}",
            )
        incompat = validate_initialize_params(init_params)
        if incompat:
            return error_response(request_id, ErrorCode.INVALID_REQUEST, incompat)
        return ok_response(
            request_id,
            _initialize_result_payload(identity, capabilities, kind_capabilities),
        )
    if method == "$/ping":
        return ok_response(request_id, {})
    if method == "health/check":
        return _handle_health(request_id, spec)
    if method == "shutdown":
        return ok_response(request_id, {})
    if method == "exit":
        return ok_response(request_id, {})
    return _dispatch_role(request_id, frame, wire, spec, provider_sessions)


def _handle_health(request_id: RpcId, spec: PluginSpec) -> RpcResponse:
    if _has_method(spec.impl, "health"):
        try:
            report = spec.impl.health(CallContext(request_id=request_id))
            if isinstance(report, HealthReport):
                result = {
                    "status": report.status,
                    "uptime_ms": report.uptime_ms,
                    "memory_usage_bytes": report.memory_usage_bytes,
                    "last_error": report.last_error,
                }
            elif hasattr(report, "model_dump"):
                result = report.model_dump(exclude_none=False, by_alias=True)
            else:
                result = dict(report)
            return ok_response(request_id, result)
        except Exception as exc:
            return ok_response(
                request_id,
                {
                    "status": "unhealthy",
                    "uptime_ms": None,
                    "memory_usage_bytes": None,
                    "last_error": f"health probe threw: {exc!s}",
                },
            )
    return ok_response(request_id, _build_health_ok())


def _dispatch_role(
    request_id: RpcId,
    frame: RpcRequest,
    wire: Wire,
    spec: PluginSpec,
    provider_sessions: ProviderSessionRegistry,
) -> RpcResponse | None:
    kind = spec.kind
    impl = spec.impl
    if kind == PluginKind.SUBJECT_BACKEND:
        return dispatch_subject(request_id, frame, impl, list(spec.subject_kinds))
    if kind == PluginKind.TRIGGER_BACKEND:
        return dispatch_trigger(request_id, frame, wire, impl)
    if kind == PluginKind.PROVIDER:
        return dispatch_provider(request_id, frame, wire, impl, provider_sessions)
    if kind == PluginKind.LOG_STORAGE_BACKEND:
        return dispatch_log_storage(request_id, frame, wire, impl)
    if kind == PluginKind.TRANSPORT_BACKEND:
        return dispatch_transport(request_id, frame, wire, impl)
    if kind == PluginKind.QUEUE:
        return dispatch_queue(request_id, frame, impl)
    if kind == PluginKind.WORKFLOW_RUNNER:
        return dispatch_workflow_runner(request_id, frame, impl)
    if kind == PluginKind.DURABLE_STORE:
        return dispatch_durable_store(request_id, frame, impl)
    if kind == PluginKind.MEMORY_STORE:
        return dispatch_memory_store(request_id, frame, impl)
    if kind == PluginKind.NOTIFIER:
        return dispatch_notifier(request_id, frame, impl)
    return error_response(
        request_id, ErrorCode.METHOD_NOT_FOUND, f"unknown method '{frame.method}'"
    )


__all__ = [
    "PluginHandle",
    "PluginSpec",
    "define_plugin",
    "ensure_wire_subject",
]
