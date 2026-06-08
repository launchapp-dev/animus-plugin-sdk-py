"""Concurrency tests for the provider role.

A long-running `agent/run` must execute OFF the wire's serial dispatch loop so a
concurrently-arriving `agent/cancel` / `$/cancelRequest` is processed mid-run and
can cancel it, while ordered replies for non-provider methods are preserved.
"""

from __future__ import annotations

import io
import json
import threading
from typing import Any

from animus_plugin_sdk import define_plugin

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


def _final(session_id: str) -> dict[str, Any]:
    return {
        "backend": "test",
        "duration_ms": 1,
        "exit_code": 0,
        "output": "done",
        "session_id": session_id,
    }


def drive(spec_kwargs: dict[str, Any], frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inbound = io.StringIO("".join(json.dumps(f) + "\n" for f in frames))
    outbound = io.StringIO()
    handle = define_plugin(input=inbound, output=outbound, skip_cli_args=True, **spec_kwargs)
    handle.run()  # joins detached provider workers at EOF
    return [json.loads(line) for line in outbound.getvalue().splitlines() if line.strip()]


def _by_id(frames: list[dict[str, Any]], rid: int) -> dict[str, Any] | None:
    return next((f for f in frames if f.get("id") == rid), None)


class _CancellableProvider:
    """A provider whose `run` blocks until its cancel token fires."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.aborted = False

    def run(self, params: Any, ctx: Any) -> dict[str, Any]:
        # Block until the SDK sets the per-session cancel token (or a safety
        # timeout so a bug can't hang the test suite forever).
        assert ctx.cancelled is not None
        if ctx.cancelled.wait(timeout=5.0):
            self.aborted = True
        return _final(self.session_id)

    def cancel(self, params: Any, ctx: Any) -> dict[str, Any]:
        return {"session_id": params.session_id, "cancelled": True}


def _run_frame(rid: int, session_id: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "method": "agent/run",
        "params": {"prompt": "hi", "cwd": "/x", "session_id": session_id},
    }


def test_agent_cancel_interrupts_in_flight_run() -> None:
    impl = _CancellableProvider("sess-1")
    frames = drive(
        dict(kind="provider", impl=impl, name="p", version="0.1.0", description="d"),
        [
            INIT,
            _run_frame(2, "sess-1"),
            # Concurrent cancel arriving while run is in-flight. If run blocked
            # the serial loop this would never be dispatched until run resolved.
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "agent/cancel",
                "params": {"session_id": "sess-1"},
            },
        ],
    )
    assert impl.aborted is True
    cancel_reply = _by_id(frames, 3)
    assert cancel_reply is not None
    assert cancel_reply["result"]["cancelled"] is True
    # The run's final response is still emitted to the original id (2).
    run_reply = _by_id(frames, 2)
    assert run_reply is not None
    assert run_reply["result"]["session_id"] == "sess-1"


def test_agent_cancel_unknown_session_returns_cancelled_false() -> None:
    # Provider with NO cancel() hook so the registry-only path is exercised.
    class _NoCancelProvider:
        def run(self, params: Any, ctx: Any) -> dict[str, Any]:
            ctx.cancelled.wait(timeout=5.0)
            return _final("sess-known")

    frames = drive(
        dict(kind="provider", impl=_NoCancelProvider(), name="p", version="0.1.0", description="d"),
        [
            INIT,
            _run_frame(2, "sess-known"),
            {"jsonrpc": "2.0", "id": 3, "method": "agent/cancel", "params": {"session_id": "nope"}},
            # Clean up the still-running session so the worker can finish.
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "agent/cancel",
                "params": {"session_id": "sess-known"},
            },
        ],
    )
    unknown = _by_id(frames, 3)
    assert unknown is not None
    assert "error" not in unknown
    assert unknown["result"] == {"session_id": "nope", "cancelled": False}
    known = _by_id(frames, 4)
    assert known is not None
    assert known["result"] == {"session_id": "sess-known", "cancelled": True}


def test_ordered_replies_for_interleaved_non_provider_methods() -> None:
    impl = _CancellableProvider("sess-x")
    frames = drive(
        dict(kind="provider", impl=impl, name="p", version="0.1.0", description="d"),
        [
            INIT,
            _run_frame(10, "sess-x"),
            {"jsonrpc": "2.0", "id": 11, "method": "health/check"},
            {"jsonrpc": "2.0", "id": 12, "method": "$/ping"},
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "agent/cancel",
                "params": {"session_id": "sess-x"},
            },
        ],
    )
    ids = [f.get("id") for f in frames]
    idx11, idx12 = ids.index(11), ids.index(12)
    # health/check (11) and ping (12) reply in arrival order relative to each
    # other, and BEFORE the run's own final reply (10) — proving the run did
    # not block the serial loop.
    assert idx11 < idx12
    idx10 = ids.index(10)
    assert idx11 < idx10
    assert idx12 < idx10


def test_cancel_request_resolves_run_with_minus_32002() -> None:
    impl = _CancellableProvider("sess-c")
    frames = drive(
        dict(kind="provider", impl=impl, name="p", version="0.1.0", description="d"),
        [
            INIT,
            _run_frame(20, "sess-c"),
            # Notification (no id) targeting the originating request id 20.
            {"jsonrpc": "2.0", "method": "$/cancelRequest", "params": {"id": 20}},
        ],
    )
    run_reply = _by_id(frames, 20)
    assert run_reply is not None
    assert "result" not in run_reply
    assert run_reply["error"]["code"] == -32002


def test_run_streams_notifications_then_final_response() -> None:
    class _StreamingProvider:
        def run(self, params: Any, ctx: Any) -> dict[str, Any]:
            ctx.stream.thinking(text="pondering")
            ctx.stream.output(text="partial")
            ctx.stream.output(text="final", final=True)
            return _final("sess-s")

    frames = drive(
        dict(
            kind="provider", impl=_StreamingProvider(), name="p", version="0.1.0", description="d"
        ),
        [INIT, _run_frame(30, "sess-s")],
    )
    methods = [f.get("method") for f in frames if f.get("method")]
    assert methods == ["agent/thinking", "agent/output", "agent/output"]
    run_reply = _by_id(frames, 30)
    assert run_reply is not None
    assert run_reply["result"]["output"] == "done"
    # The final response is the LAST frame on the wire (single-writer ordering).
    assert frames[-1].get("id") == 30


def test_agent_cancel_reaches_provider_assigned_session_id() -> None:
    # Request omits session_id; the provider allocates + streams its own. A host
    # only learns that id from the stream, so it cancels AFTER receiving it. We
    # model that ordering with a gated input stream: the cancel line is withheld
    # until the provider has streamed its id (and thus the SDK has late-bound the
    # registry entry under it).
    streamed = threading.Event()

    class _ProviderAssignedSession:
        def __init__(self) -> None:
            self.aborted = False

        def run(self, params: Any, ctx: Any) -> dict[str, Any]:
            ctx.stream.thinking(text="starting", session_id="provider-sid")
            streamed.set()
            if ctx.cancelled.wait(timeout=5.0):
                self.aborted = True
            return _final("provider-sid")

        def cancel(self, params: Any, ctx: Any) -> dict[str, Any]:
            return {"session_id": params.session_id, "cancelled": True}

    init_line = json.dumps(INIT) + "\n"
    run_line = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 40,
                "method": "agent/run",
                "params": {"prompt": "hi", "cwd": "/x"},
            }
        )
        + "\n"
    )
    cancel_line = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 41,
                "method": "agent/cancel",
                "params": {"session_id": "provider-sid"},
            }
        )
        + "\n"
    )

    class _GatedInput:
        """Yields init + run immediately, then blocks until the provider has
        streamed its session id before yielding the cancel line."""

        def __iter__(self) -> Any:
            yield init_line
            yield run_line
            streamed.wait(timeout=5.0)
            yield cancel_line

    impl = _ProviderAssignedSession()
    outbound = io.StringIO()
    define_plugin(
        kind="provider",
        impl=impl,
        name="p",
        version="0.1.0",
        description="d",
        skip_cli_args=True,
        input=_GatedInput(),  # type: ignore[arg-type]
        output=outbound,
    ).run()
    frames = [json.loads(line) for line in outbound.getvalue().splitlines() if line.strip()]
    assert impl.aborted is True
    assert _by_id(frames, 40) is not None


def test_provider_advertises_cancellation_capability() -> None:
    # `$/cancelRequest` support is now wired, so the initialize result must
    # advertise `capabilities.cancellation = true`.
    frames = drive(
        dict(
            kind="provider",
            impl=_CancellableProvider("s"),
            name="p",
            version="0.1.0",
            description="d",
        ),
        [INIT],
    )
    init_reply = _by_id(frames, 1)
    assert init_reply is not None
    assert init_reply["result"]["capabilities"]["cancellation"] is True


def test_resume_without_session_id_is_rejected() -> None:
    # Spec §7.2: agent/resume resumes a prior session and carries session_id.
    # A resume with no session id has nothing to resume -> invalid_params, and
    # the impl's resume() must not be invoked.
    class _ResumableProvider:
        def __init__(self) -> None:
            self.resume_called = False

        def run(self, params: Any, ctx: Any) -> dict[str, Any]:
            return _final("sess-x")

        def resume(self, params: Any, ctx: Any) -> dict[str, Any]:
            self.resume_called = True
            return _final("sess-x")

    impl = _ResumableProvider()
    frames = drive(
        dict(kind="provider", impl=impl, name="p", version="0.1.0", description="d"),
        [
            INIT,
            {
                "jsonrpc": "2.0",
                "id": 60,
                "method": "agent/resume",
                "params": {"prompt": "hi", "cwd": "/x"},
            },
        ],
    )
    reply = _by_id(frames, 60)
    assert reply is not None
    assert reply["error"]["code"] == -32602
    assert impl.resume_called is False
