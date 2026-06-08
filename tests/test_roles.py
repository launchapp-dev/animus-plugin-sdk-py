"""Full-role-coverage tests: codegen output validates real frames, each role
dispatcher (happy path + method_not_supported/found + pydantic validation
rejecting malformed params), trigger streaming, subject/delete, and back-compat
subpath imports."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from animus_plugin_sdk import PROTOCOL_VERSION, define_plugin

NOW = "2026-06-07T00:00:00.000Z"

INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocol_version": "1.0.0",
        "host_info": {"name": "animus", "version": "x"},
        "capabilities": {},
    },
}


def drive(spec_kwargs: dict[str, Any], frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drive a plugin over an in-memory wire and return parsed frames."""
    inbound = io.StringIO("".join(json.dumps(f) + "\n" for f in frames))
    outbound = io.StringIO()
    handle = define_plugin(
        input=inbound,
        output=outbound,
        skip_cli_args=True,
        **spec_kwargs,
    )
    handle.run()
    return [json.loads(line) for line in outbound.getvalue().splitlines() if line.strip()]


def _result(frames: list[dict[str, Any]], rid: int) -> dict[str, Any]:
    return next(f for f in frames if f.get("id") == rid)


# ---- codegen output validates real frames ---------------------------------


def test_generated_subject_validates() -> None:
    from animus_plugin_sdk.types.generated.subject import Subject

    s = Subject.model_validate(
        {
            "id": "task:1",
            "kind": "task",
            "title": "hi",
            "status": "ready",
            "created_at": NOW,
            "updated_at": NOW,
        }
    )
    assert s.id == "task:1"


def test_generated_subject_filter_permissive() -> None:
    from animus_plugin_sdk.types.generated.subject import SubjectFilter

    assert SubjectFilter.model_validate({}).limit is None
    assert SubjectFilter.model_validate({"status": ["ready"], "kind": ["task"]}).status == ["ready"]


def test_generated_agent_run_request_rejects_malformed() -> None:
    from pydantic import ValidationError

    from animus_plugin_sdk.types.generated.provider import AgentRunRequest

    with pytest.raises(ValidationError):
        AgentRunRequest.model_validate({})
    assert AgentRunRequest.model_validate({"prompt": "hi", "cwd": "/x"}).prompt == "hi"


def test_generated_log_entry_validates() -> None:
    from animus_plugin_sdk.types.generated.log_storage import LogEntry

    e = LogEntry.model_validate(
        {
            "id": "e1",
            "ts": NOW,
            "level": "info",
            "source": "plugin",
            "target": "plugin.test",
            "message": "hi",
        }
    )
    assert e.level == "info"


def test_generated_modules_all_importable() -> None:
    from animus_plugin_sdk.types import generated

    for mod in generated.__all__:
        assert hasattr(generated, mod)


def test_schema_field_alias_roundtrips() -> None:
    # `DaemonEventRecord.schema` shadows pydantic — emitted as `schema_` with an
    # alias so the wire name round-trips.
    from animus_plugin_sdk.types.generated.notifier import DaemonEventRecord

    rec = DaemonEventRecord.model_validate(
        {"id": "1", "event_type": "x", "timestamp": NOW, "data": {}, "schema": "S"}
    )
    assert rec.schema_ == "S"
    assert rec.model_dump(by_alias=True)["schema"] == "S"


# ---- subpath / back-compat imports -----------------------------------------


def test_subpath_modules_expose_contracts() -> None:
    from animus_plugin_sdk.durable_store import DurableStore
    from animus_plugin_sdk.memory_store import MemoryStore
    from animus_plugin_sdk.notifier import Notifier
    from animus_plugin_sdk.provider import AgentRunRequest, Provider
    from animus_plugin_sdk.queue import Queue
    from animus_plugin_sdk.subject import SubjectBackend, ensure_wire_subject
    from animus_plugin_sdk.transport import TransportBackend
    from animus_plugin_sdk.trigger import TriggerBackend, TriggerEvent
    from animus_plugin_sdk.workflow_runner import WorkflowRunner

    assert SubjectBackend and Provider and TriggerBackend and TransportBackend
    assert Queue and WorkflowRunner and DurableStore and MemoryStore and Notifier
    assert AgentRunRequest and TriggerEvent and callable(ensure_wire_subject)


def test_protocol_version_is_1_1_0() -> None:
    assert PROTOCOL_VERSION == "1.1.0"


def test_task_backend_kind_is_rejected() -> None:
    from animus_plugin_sdk import PluginKind

    with pytest.raises(TypeError, match="not a dispatchable role"):
        define_plugin(
            kind=PluginKind.TASK_BACKEND, impl=object(), name="n", version="v", description="d"
        )


def test_custom_kind_is_rejected() -> None:
    from animus_plugin_sdk import PluginKind

    with pytest.raises(TypeError, match="no SDK dispatcher"):
        define_plugin(kind=PluginKind.CUSTOM, impl=object(), name="n", version="v", description="d")


def test_initialize_tolerates_missing_host_capabilities() -> None:
    # A v1.0 host may omit `capabilities`; the handshake must still succeed.
    frames = drive(
        _subject_spec(_Subject()),
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocol_version": "1.0.0", "host_info": {"name": "a", "version": "x"}},
            }
        ],
    )
    assert _result(frames, 1)["result"]["protocol_version"] == "1.1.0"


def test_string_env_required_marks_required_in_manifest() -> None:
    handle = define_plugin(**_subject_spec(_Subject()), env_required=["TOKEN"])
    env = handle.manifest().model_dump(exclude_none=True, by_alias=True)["env_required"]
    assert env == [{"name": "TOKEN", "required": True}]


def test_env_requirement_object_defaults_required_true() -> None:
    from animus_plugin_sdk import EnvRequirement

    handle = define_plugin(**_subject_spec(_Subject()), env_required=[EnvRequirement(name="TOKEN")])
    env = handle.manifest().model_dump(exclude_none=True, by_alias=True)["env_required"]
    assert env[0]["required"] is True


def test_env_requirement_object_honors_explicit_false() -> None:
    from animus_plugin_sdk import EnvRequirement

    handle = define_plugin(
        **_subject_spec(_Subject()), env_required=[EnvRequirement(name="OPT", required=False)]
    )
    env = handle.manifest().model_dump(exclude_none=True, by_alias=True)["env_required"]
    assert env[0]["required"] is False


def test_build_manifest_defaults_env_required_true() -> None:
    # Direct `build_manifest` callers also get the historical required default.
    from animus_plugin_sdk import (
        EnvRequirement,
        PluginCapabilities,
        PluginIdentity,
        PluginKind,
        build_manifest,
    )

    manifest = build_manifest(
        PluginIdentity(
            name="n", version="v", description="d", plugin_kind=PluginKind.SUBJECT_BACKEND
        ),
        PluginCapabilities(),
        env_required=[EnvRequirement(name="TOKEN")],
    )
    env = manifest.model_dump(exclude_none=True, by_alias=True)["env_required"]
    assert env[0]["required"] is True


def test_subject_get_passes_extra_params_through() -> None:
    seen: dict[str, Any] = {}

    class _GetExtras(_Subject):
        def get(self, params: dict[str, Any], ctx: Any) -> dict[str, Any]:
            seen.update(params)
            return {"id": params["id"], "kind": ctx.kind, "title": "t"}

    drive(
        _subject_spec(_GetExtras()),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "subject/get",
                "params": {"id": "task:1", "projection": "full"},
            },
        ],
    )
    assert seen.get("projection") == "full"


def test_import_emits_no_warnings() -> None:
    import importlib
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        import animus_plugin_sdk
        from animus_plugin_sdk.types.generated import workflow_runner

        importlib.reload(workflow_runner)
    assert animus_plugin_sdk.PROTOCOL_VERSION == "1.1.0"


def test_deprecated_provider_types_importable() -> None:
    # Historical import path must keep working.
    from animus_plugin_sdk import ProviderRunParams, ProviderRunResult
    from animus_plugin_sdk.roles import (
        ProviderRunParams as RolesParams,
    )
    from animus_plugin_sdk.roles import (
        ProviderRunResult as RolesResult,
    )

    assert ProviderRunParams is RolesParams
    assert ProviderRunResult is RolesResult


# ---- subject_backend back-compat + subject/delete --------------------------


class _Subject:
    def __init__(self, with_delete: bool = False) -> None:
        if with_delete:
            self.delete = self._delete  # type: ignore[method-assign]

    def list(self, params: Any, ctx: Any) -> dict[str, Any]:
        return {
            "subjects": [{"id": f"{ctx.kind}:1", "kind": ctx.kind, "title": "hi"}],
            "fetched_at": None,
        }

    def get(self, params: dict[str, Any], ctx: Any) -> dict[str, Any] | None:
        return (
            {"id": params["id"], "kind": ctx.kind, "title": "got"}
            if params["id"] != "task:miss"
            else None
        )

    def _delete(self, params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        return {"ok": True}


def _subject_spec(impl: Any) -> dict[str, Any]:
    return dict(
        kind="subject_backend",
        impl=impl,
        name="s",
        version="0.1.0",
        description="d",
        subject_kinds=["task"],
    )


def test_subject_legacy_kind_route_and_wire_backfill() -> None:
    frames = drive(
        _subject_spec(_Subject()),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "task/list", "params": {}}],
    )
    res = _result(frames, 2)["result"]
    assert res["subjects"][0]["id"] == "task:1"
    # ensure_wire_subject backfilled status/created_at/updated_at.
    assert res["subjects"][0]["status"] == "ready"
    assert res["subjects"][0]["created_at"]


def test_subject_canonical_route_and_get_not_found() -> None:
    frames = drive(
        _subject_spec(_Subject()),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "subject/get", "params": {"id": "task:miss"}}],
    )
    err = _result(frames, 2)["error"]
    assert err["data"]["category"] == "not_found"


def test_subject_delete_not_implemented_is_method_not_supported() -> None:
    frames = drive(
        _subject_spec(_Subject(with_delete=False)),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "subject/delete", "params": {"id": "task:1"}}],
    )
    assert _result(frames, 2)["error"]["code"] == -32001


def test_subject_delete_when_implemented() -> None:
    impl = _Subject(with_delete=True)
    frames = drive(
        _subject_spec(impl),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "subject/delete", "params": {"id": "task:1"}}],
    )
    assert _result(frames, 2)["result"] == {"ok": True}
    # `subject/delete` is advertised when the impl provides it.
    caps = _result(frames, 1)["result"]["capabilities"]["methods"]
    assert "subject/delete" in caps


def test_subject_delete_reports_pydantic_failure() -> None:
    from animus_plugin_sdk.subject import gen

    class _FailDelete(_Subject):
        def delete(self, params: dict[str, Any], ctx: Any) -> Any:
            return gen.DeleteSubjectResponse(ok=False)

    frames = drive(
        _subject_spec(_FailDelete()),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "subject/delete", "params": {"id": "task:1"}}],
    )
    assert _result(frames, 2)["result"] == {"ok": False}


def test_subject_list_rejects_malformed_filter() -> None:
    frames = drive(
        _subject_spec(_Subject()),
        # `status` must be a list; a bare string fails pydantic validation.
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "subject/list", "params": {"status": 123}}],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


def test_sparse_subject_construction_back_compat() -> None:
    # Historical sparse construction (no status/created_at/updated_at) must not
    # raise — the ergonomic wrappers default them; the SDK backfills on the wire.
    from animus_plugin_sdk import Subject, SubjectListResult

    s = Subject(id="task:1", kind="task", title="hi")
    assert s.status == "ready"
    assert SubjectListResult(subjects=[s]).fetched_at is None


class _MultiKindSubject:
    """Single-declared-kind backend; records ctx.kind + the filter kind seen."""

    def __init__(self) -> None:
        self.seen_kinds: list[str] = []
        self.filter_kinds: list[Any] = []

    def list(self, params: Any, ctx: Any) -> dict[str, Any]:
        self.seen_kinds.append(ctx.kind)
        self.filter_kinds.append(params.kind)
        return {"subjects": [], "fetched_at": None}

    def get(self, params: dict[str, Any], ctx: Any) -> None:
        return None


def test_canonical_route_stays_within_declared_kind() -> None:
    impl = _MultiKindSubject()
    drive(
        _subject_spec(impl),
        # Host sends a `requirement` filter to a task-only backend over the
        # canonical route; it must be invoked as `task`, never `requirement`.
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "subject/list",
                "params": {"kind": ["requirement"]},
            },
        ],
    )
    assert impl.seen_kinds == ["task"]
    assert impl.filter_kinds == [["task"]]


def test_canonical_route_clamps_multi_kind_filter() -> None:
    impl = _MultiKindSubject()
    drive(
        _subject_spec(impl),
        # A multi-kind filter is clamped to the declared set: the undeclared
        # `requirement` is dropped, `task` is kept.
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "subject/list",
                "params": {"kind": ["task", "requirement"]},
            },
        ],
    )
    assert impl.filter_kinds == [["task"]]


class _LegacySchemaSubject(_Subject):
    """Backend using the historical no-arg `schema()` signature."""

    def schema(self) -> dict[str, Any]:
        return {"kinds": ["task"], "legacy": True}


def test_legacy_no_arg_schema_hook() -> None:
    frames = drive(
        _subject_spec(_LegacySchemaSubject()),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "subject/schema"}],
    )
    assert _result(frames, 2)["result"]["legacy"] is True


# ---- trigger_backend streaming ---------------------------------------------


class _Trigger:
    def watch(self, params: Any, ctx: Any) -> Any:
        yield {"event_id": "e1", "payload": {"x": 1}}
        yield {"event_id": "e2"}


class _AckTrigger(_Trigger):
    def __init__(self) -> None:
        self.acked: list[dict[str, Any]] = []

    def ack(self, params: dict[str, Any], ctx: Any) -> None:
        self.acked.append(dict(params))


class _ModelSchemaTrigger(_Trigger):
    """Returns a generated TriggerSchema pydantic model from `schema()`."""

    def schema(self, ctx: Any) -> Any:
        from animus_plugin_sdk.trigger import TriggerSchema

        return TriggerSchema.model_validate(
            {
                "kinds": ["slack_mention"],
                "supports_resume": True,
                "supports_dedup": True,
                "supports_ack": False,
            }
        )


def test_trigger_schema_pydantic_model_is_serialized() -> None:
    # A contract-following impl may return the generated TriggerSchema model;
    # the dispatcher must serialize it (not crash the loop on json.dumps).
    frames = drive(
        dict(
            kind="trigger_backend",
            impl=_ModelSchemaTrigger(),
            name="t",
            version="0.1.0",
            description="d",
        ),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "trigger/schema"}],
    )
    assert _result(frames, 2)["result"]["kinds"] == ["slack_mention"]


def test_trigger_watch_streams_flat_events() -> None:
    frames = drive(
        dict(kind="trigger_backend", impl=_Trigger(), name="t", version="0.1.0", description="d"),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "trigger/watch", "params": {}}],
    )
    assert _result(frames, 2)["result"] == {"watching": True}
    events = [f for f in frames if f.get("method") == "trigger/event"]
    assert [e["params"]["event_id"] for e in events] == ["e1", "e2"]
    # Flat shape: event fields live directly on params (no {id, event} wrapper).
    assert "event" not in events[0]["params"]
    assert events[0]["params"]["payload"] == {"x": 1}


def test_trigger_schema_default_and_ack_not_supported() -> None:
    frames = drive(
        dict(kind="trigger_backend", impl=_Trigger(), name="t", version="0.1.0", description="d"),
        [
            INIT,
            {"jsonrpc": "2.0", "id": 2, "method": "trigger/schema"},
            {"jsonrpc": "2.0", "id": 3, "method": "trigger/ack", "params": {"event_id": "e1"}},
        ],
    )
    assert _result(frames, 2)["result"]["supports_ack"] is False
    # ack is a recognized trigger verb but not implemented → method_not_supported.
    assert _result(frames, 3)["error"]["code"] == -32001


def test_trigger_ack_notification_routes_to_impl_with_status() -> None:
    impl = _AckTrigger()
    # `trigger/ack` is a host→plugin notification (no id); it must reach the
    # impl and forward the optional `status`.
    drive(
        dict(kind="trigger_backend", impl=impl, name="t", version="0.1.0", description="d"),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "method": "trigger/ack",
                "params": {"event_id": "e1", "status": "dispatched"},
            },
        ],
    )
    assert impl.acked == [{"event_id": "e1", "status": "dispatched"}]


def test_trigger_advertises_ack_when_implemented() -> None:
    frames = drive(
        dict(
            kind="trigger_backend", impl=_AckTrigger(), name="t", version="0.1.0", description="d"
        ),
        [INIT],
    )
    assert "trigger/ack" in _result(frames, 1)["result"]["capabilities"]["methods"]


# ---- provider streaming + validation ---------------------------------------


class _Provider:
    def run(self, params: Any, ctx: Any) -> dict[str, Any]:
        ctx.stream.output(text="hi", final=True)
        ctx.stream.thinking(text="hmm")
        ctx.stream.tool_call(name="grep")
        return {"session_id": "abc", "exit_code": 0, "output": "done", "duration_ms": 1}


class _DataclassProvider:
    def run(self, params: Any, ctx: Any) -> Any:
        from animus_plugin_sdk import ProviderRunResult

        return ProviderRunResult(session_id="abc", output="done", exit_code=0, duration_ms=1)


def test_provider_run_serializes_deprecated_dataclass_result() -> None:
    frames = drive(
        dict(
            kind="provider", impl=_DataclassProvider(), name="p", version="0.1.0", description="d"
        ),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "agent/run",
                "params": {"prompt": "hi", "cwd": "/x"},
            },
        ],
    )
    result = _result(frames, 2)["result"]
    assert result["output"] == "done"
    # The deprecated dataclass lacks `backend` (required on AgentRunResponse);
    # the SDK fills a default so the wire payload still decodes host-side.
    assert "backend" in result


def test_provider_run_streams_then_returns_final() -> None:
    frames = drive(
        dict(kind="provider", impl=_Provider(), name="p", version="0.1.0", description="d"),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "agent/run",
                "params": {"prompt": "hi", "cwd": "/x"},
            },
        ],
    )
    methods = [f.get("method") for f in frames if f.get("method")]
    assert methods == ["agent/output", "agent/thinking", "agent/toolCall"]
    assert _result(frames, 2)["result"]["output"] == "done"


def test_provider_run_rejects_malformed_params() -> None:
    frames = drive(
        dict(kind="provider", impl=_Provider(), name="p", version="0.1.0", description="d"),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "agent/run", "params": {}}],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


def test_provider_resume_not_supported() -> None:
    frames = drive(
        dict(kind="provider", impl=_Provider(), name="p", version="0.1.0", description="d"),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "agent/resume",
                "params": {"prompt": "x", "cwd": "/x"},
            },
        ],
    )
    assert _result(frames, 2)["error"]["code"] == -32001


# ---- log_storage_backend ----------------------------------------------------


class _LogStore:
    def __init__(self, with_tail: bool = False) -> None:
        self.stored: list[Any] = []
        if with_tail:
            self.tail = self._tail  # type: ignore[method-assign]

    def store(self, params: dict[str, Any], ctx: Any) -> dict[str, Any]:
        self.stored.extend(params.get("entries", []))
        return {"stored": len(params.get("entries", []))}

    def _tail(self, params: Any, ctx: Any) -> Any:
        yield {
            "id": "e1",
            "ts": NOW,
            "level": "info",
            "source": "plugin",
            "target": "t",
            "message": "m",
        }


def _entry() -> dict[str, Any]:
    return {
        "id": "e1",
        "ts": NOW,
        "level": "info",
        "source": "plugin",
        "target": "t",
        "message": "m",
    }


def test_log_storage_store_and_query_not_supported() -> None:
    frames = drive(
        dict(
            kind="log_storage_backend", impl=_LogStore(), name="l", version="0.1.0", description="d"
        ),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "log_storage/store",
                "params": {"entries": [_entry()]},
            },
            {"jsonrpc": "2.0", "id": 3, "method": "log_storage/query", "params": {}},
        ],
    )
    assert _result(frames, 2)["result"]["stored"] == 1
    assert _result(frames, 3)["error"]["code"] == -32001


def test_log_storage_store_rejects_malformed() -> None:
    frames = drive(
        dict(
            kind="log_storage_backend", impl=_LogStore(), name="l", version="0.1.0", description="d"
        ),
        # entries items must be LogEntry; a missing required field fails.
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "log_storage/store",
                "params": {"entries": [{"id": "x"}]},
            },
        ],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


def test_log_storage_tail_streams_events() -> None:
    frames = drive(
        dict(
            kind="log_storage_backend",
            impl=_LogStore(with_tail=True),
            name="l",
            version="0.1.0",
            description="d",
        ),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "log_storage/tail", "params": {}}],
    )
    assert _result(frames, 2)["result"] == {"tailing": True}
    events = [f for f in frames if f.get("method") == "log_storage/event"]
    assert len(events) == 1
    assert events[0]["params"]["id"] == 2
    assert events[0]["params"]["entry"]["id"] == "e1"


# ---- transport_backend ------------------------------------------------------


class _Transport:
    def start(self, params: Any, ctx: Any) -> dict[str, Any]:
        return {"bound_addr": "127.0.0.1:8080", "started_at": NOW}


def test_transport_start_and_schema() -> None:
    frames = drive(
        dict(
            kind="transport_backend", impl=_Transport(), name="tr", version="0.1.0", description="d"
        ),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "transport/start",
                "params": {"control_socket_path": "/s", "project_root": "/p"},
            },
            {"jsonrpc": "2.0", "id": 3, "method": "transport/schema"},
        ],
    )
    assert _result(frames, 2)["result"]["bound_addr"] == "127.0.0.1:8080"
    assert _result(frames, 3)["result"]["supports_streaming"] is False


def test_transport_start_rejects_malformed() -> None:
    frames = drive(
        dict(
            kind="transport_backend", impl=_Transport(), name="tr", version="0.1.0", description="d"
        ),
        # control_socket_path is required.
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "transport/start",
                "params": {"project_root": "/p"},
            },
        ],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


# ---- queue ------------------------------------------------------------------


class _Queue:
    def enqueue(self, p: Any, c: Any) -> dict[str, Any]:
        return {"entry_id": "q1", "duplicate": False}

    def list(self, p: Any, c: Any) -> dict[str, Any]:
        return {"entries": [], "next_cursor": None}

    def lease(self, p: Any, c: Any) -> dict[str, Any]:
        return {"entries": []}

    def stats(self, p: Any, c: Any) -> dict[str, Any]:
        return {"pending": 0}

    def hold(self, p: Any, c: Any) -> dict[str, Any]:
        return {"changed": [], "not_found": []}

    def release(self, p: Any, c: Any) -> dict[str, Any]:
        return {"changed": [], "not_found": []}

    def drop(self, p: Any, c: Any) -> dict[str, Any]:
        return {"changed": [], "not_found": []}

    def mark_assigned(self, p: Any, c: Any) -> dict[str, Any]:
        return {"changed": [], "not_found": []}

    def completion(self, p: Any, c: Any) -> dict[str, Any]:
        return {"changed": [], "not_found": []}

    def reorder(self, p: Any, c: Any) -> dict[str, Any]:
        return {"reordered_count": 0}


def test_queue_stats_and_unknown_method() -> None:
    frames = drive(
        dict(kind="queue", impl=_Queue(), name="q", version="0.1.0", description="d"),
        [
            INIT,
            {"jsonrpc": "2.0", "id": 2, "method": "queue/stats"},
            {"jsonrpc": "2.0", "id": 3, "method": "queue/bogus"},
        ],
    )
    assert _result(frames, 2)["result"] == {"pending": 0}
    assert _result(frames, 3)["error"]["code"] == -32601
    # v1.1.0 kind advertises kind_capabilities.
    assert _result(frames, 1)["result"]["kind_capabilities"]["queue"]["crate_version"] == "0.1.0"


def test_queue_lease_rejects_negative_max() -> None:
    # `QueueLeaseRequest.max` has `minimum: 0`; the generated validator must
    # reject a negative value with -32602 (schema-faithful numeric bounds).
    frames = drive(
        dict(kind="queue", impl=_Queue(), name="q", version="0.1.0", description="d"),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "queue/lease", "params": {"max": -1}}],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


def test_queue_enqueue_rejects_malformed() -> None:
    frames = drive(
        dict(kind="queue", impl=_Queue(), name="q", version="0.1.0", description="d"),
        # subject_dispatch is required on QueueEnqueueRequest.
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "queue/enqueue", "params": {}}],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


def test_queue_release_pending_not_supported() -> None:
    frames = drive(
        dict(kind="queue", impl=_Queue(), name="q", version="0.1.0", description="d"),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "queue/release_pending", "params": {}}],
    )
    # Recognized optional method, not implemented → method_not_supported.
    assert _result(frames, 2)["error"]["code"] == -32001


# ---- workflow_runner / durable_store / memory_store ------------------------


class _WorkflowRunner:
    def execute(self, p: Any, c: Any) -> dict[str, Any]:
        return {"workflow_status": "completed", "phase_results": [], "phase_events": []}

    def run_phase(self, p: Any, c: Any) -> dict[str, Any]:
        return {"phase_status": "completed"}


def test_workflow_runner_run_phase_and_unknown() -> None:
    frames = drive(
        dict(
            kind="workflow_runner",
            impl=_WorkflowRunner(),
            name="w",
            version="0.1.0",
            description="d",
        ),
        [
            INIT,
            {"jsonrpc": "2.0", "id": 2, "method": "workflow/run_phase", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "workflow/bogus"},
        ],
    )
    # run_phase params may validate as empty (all optional) or reject; either way
    # a recognized method must not be -32601.
    assert (
        _result(frames, 2).get("result") is not None
        or _result(frames, 2)["error"]["code"] == -32602
    )
    assert _result(frames, 3)["error"]["code"] == -32601


class _MemoryStore:
    def put(self, p: Any, c: Any) -> dict[str, Any]:
        return {"indexed_immediately": True}

    def get(self, p: Any, c: Any) -> dict[str, Any]:
        return {"value": None}

    def query(self, p: Any, c: Any) -> dict[str, Any]:
        return {"results": []}

    def list_scopes(self, p: Any, c: Any) -> dict[str, Any]:
        return {"scopes": []}

    def delete_scope(self, p: Any, c: Any) -> dict[str, Any]:
        return {"deleted": True}


def test_memory_store_unknown_method() -> None:
    frames = drive(
        dict(kind="memory_store", impl=_MemoryStore(), name="m", version="0.1.0", description="d"),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "memory/bogus"}],
    )
    assert _result(frames, 2)["error"]["code"] == -32601
    assert (
        _result(frames, 1)["result"]["kind_capabilities"]["memory_store"]["crate_version"]
        == "0.1.0"
    )


# ---- notifier ---------------------------------------------------------------


class _Notifier:
    def notify(self, p: Any, c: Any) -> dict[str, Any]:
        return {"delivered": True}


def test_notifier_notify_and_flush_not_supported() -> None:
    event = {"id": "1", "event_type": "x", "timestamp": NOW, "data": {}, "schema": "v1"}
    frames = drive(
        dict(kind="notifier", impl=_Notifier(), name="n", version="0.1.0", description="d"),
        [
            INIT,
            {"jsonrpc": "2.0", "id": 2, "method": "notifier/notify", "params": {"event": event}},
            {"jsonrpc": "2.0", "id": 3, "method": "notifier/flush", "params": {}},
            {"jsonrpc": "2.0", "id": 4, "method": "notifier/schema"},
        ],
    )
    assert _result(frames, 2)["result"]["delivered"] is True
    assert _result(frames, 3)["error"]["code"] == -32001
    assert _result(frames, 4)["result"]["supports_flush"] is False


def test_notifier_notify_rejects_malformed_event() -> None:
    frames = drive(
        dict(kind="notifier", impl=_Notifier(), name="n", version="0.1.0", description="d"),
        # `event` is required and its DaemonEventRecord fields are required.
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "notifier/notify", "params": {"event": {}}}],
    )
    assert _result(frames, 2)["error"]["code"] == -32602


# ---- lifecycle: v1.0.0 host compatibility + kind_capabilities omission -----


def test_subject_kind_omits_kind_capabilities() -> None:
    frames = drive(_subject_spec(_Subject()), [INIT])
    # v1.0.0 kinds keep the wire shape byte-identical (no kind_capabilities key).
    assert "kind_capabilities" not in _result(frames, 1)["result"]
    assert _result(frames, 1)["result"]["protocol_version"] == "1.1.0"


def test_shutdown_returns_empty() -> None:
    frames = drive(
        _subject_spec(_Subject()),
        [INIT, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"}],
    )
    assert _result(frames, 2)["result"] == {}


def test_exit_notification_terminates_process() -> None:
    # An `exit` notification (no id) terminates the plugin process.
    with pytest.raises(SystemExit):
        drive(
            _subject_spec(_Subject()),
            [INIT, {"jsonrpc": "2.0", "method": "exit"}],
        )
