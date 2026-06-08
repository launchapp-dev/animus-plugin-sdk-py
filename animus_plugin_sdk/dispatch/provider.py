"""provider dispatcher (spec §7.2 / §10).

``agent/run`` / ``agent/resume`` validate the request with the generated
``AgentRunRequest`` model, hand the impl a streaming sink that emits
``agent/output|thinking|toolCall|toolResult|error`` notifications, then reply
with the final ``AgentRunResponse``. ``agent/cancel`` best-effort terminates a
session.

Concurrency model (the fix for the deferred P2): ``agent/run`` / ``agent/resume``
run OFF the wire's serial dispatch loop. The dispatcher spawns the run on a
bounded background worker thread (registered with ``wire.track_worker`` so EOF
joins it), returns ``None`` (no immediate response), and the worker owns sending
its own final response via ``wire.send_response`` — exactly like
``trigger/watch`` already streams ``trigger/event`` notifications out-of-band.
Because the run no longer occupies the serial loop, a subsequently-received
``agent/cancel`` or ``$/cancelRequest`` is dispatched while the run is still
in-flight and can cancel it via the session's ``threading.Event``. All other
methods (and all other roles) keep their in-order serial dispatch. Stdout frames
stay serialized by the wire write-lock, so a streaming notification never
interleaves bytes with the final response.
"""

from __future__ import annotations

import dataclasses
import threading
from typing import Any

from ..roles.context import CallContext
from ..roles.provider import AgentRunRequest, Provider, ProviderCallContext
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.provider import AgentCancelRequest
from .shared import (
    ParamValidationError,
    Wire,
    error_response,
    method_not_found,
    method_not_supported,
    ok_response,
    validate_params,
)

PROVIDER_METHODS = {"run": "agent/run", "resume": "agent/resume", "cancel": "agent/cancel"}


@dataclasses.dataclass
class _ActiveSession:
    """A single in-flight provider session."""

    # Backend session id this run is indexed under, or "" until known. Defaults
    # to the request's session_id; rebound via `bind_session` once the impl
    # emits/returns a provider-assigned id (so `agent/cancel` can reach a session
    # whose id the provider allocates itself).
    session_id: str
    request_id: RpcId
    cancelled: threading.Event
    # Set when cancellation arrived via `$/cancelRequest` (spec §6.3): the run's
    # final reply is then forced to `-32002` regardless of the impl's return. A
    # session-scoped `agent/cancel` sets `cancelled` too but leaves this False —
    # that path lets the impl resolve its own `AgentRunResponse`.
    cancelled_by_request: bool = False


class ProviderSessionRegistry:
    """Per-plugin-instance registry of in-flight provider sessions.

    Keyed by ``session_id``, with a secondary index by originating JSON-RPC
    request id so ``$/cancelRequest`` can find the session it started.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_session: dict[str, _ActiveSession] = {}
        self._by_request: dict[str, _ActiveSession] = {}

    @staticmethod
    def _request_key(request_id: RpcId) -> str:
        # JSON-RPC ids may be string OR number; `1` and `"1"` are distinct ids
        # (spec §6.3 / JSON-RPC 2.0). Type-tag the key so they never collide.
        if isinstance(request_id, bool):  # bool is an int subclass; tag distinctly
            return f"b:{request_id}"
        if isinstance(request_id, int):
            return f"n:{request_id}"
        if isinstance(request_id, str):
            return f"s:{request_id}"
        return f"x:{request_id}"  # None / other

    def register(self, session: _ActiveSession) -> None:
        with self._lock:
            # Only index a non-empty session id. A run with no request
            # `session_id` stays request-id-addressable (so `$/cancelRequest`
            # still works) and is bound under its real id later via
            # `bind_session` — avoiding a shared "" entry that concurrent no-id
            # runs would clobber.
            if session.session_id:
                self._by_session[session.session_id] = session
            self._by_request[self._request_key(session.request_id)] = session

    def bind_session(self, session: _ActiveSession, session_id: str) -> None:
        """Index a session under a provider-assigned id learned after `register`
        (e.g. the first streamed/returned `session_id`). Idempotent; ignores
        empty ids and never overwrites a different session already holding it."""
        if not session_id or session_id == session.session_id:
            return
        with self._lock:
            if session_id in self._by_session:
                return
            if session.session_id and self._by_session.get(session.session_id) is session:
                del self._by_session[session.session_id]
            session.session_id = session_id
            self._by_session[session_id] = session

    def deregister(self, session: _ActiveSession) -> None:
        with self._lock:
            # Only delete if the entry still points at this session — a resume
            # reusing the same session_id could have replaced it.
            if session.session_id and self._by_session.get(session.session_id) is session:
                del self._by_session[session.session_id]
            key = self._request_key(session.request_id)
            if self._by_request.get(key) is session:
                del self._by_request[key]

    def cancel_by_session(self, session_id: str) -> bool:
        """Session-scoped cancel (`agent/cancel`). Sets the run's cancel token so
        a cooperating impl can stop and resolve its own response. Does NOT force
        a `-32002` reply. Returns True if a session was found."""
        with self._lock:
            session = self._by_session.get(session_id)
        if session is None:
            return False
        session.cancelled.set()
        return True

    def cancel_by_request(self, request_id: RpcId) -> bool:
        """Best-effort cancel by originating request id (`$/cancelRequest`). Sets
        the cancel token and marks the run so its final reply is `-32002`."""
        with self._lock:
            session = self._by_request.get(self._request_key(request_id))
        if session is None:
            return False
        session.cancelled_by_request = True
        session.cancelled.set()
        return True


class _Sink:
    """Concrete `AgentStream` emitting `agent/*` notifications via the wire.

    Each notification carries the `AgentNotification` internally-tagged `kind`
    discriminator plus `session_id` (defaulted from the originating request when
    the author omits it), so a host decoding `params` as `AgentNotification`
    accepts them.
    """

    def __init__(
        self,
        wire: Wire,
        default_session_id: str | None,
        on_session_id: Any = None,
    ) -> None:
        self._wire = wire
        self._sid = default_session_id
        self._on_session_id = on_session_id

    def _session(self, session_id: str | None) -> str:
        resolved = session_id if session_id is not None else (self._sid or "")
        # Late-bind a provider-assigned session id so `agent/cancel` can reach
        # this run even when the original request omitted `session_id`.
        if resolved and self._on_session_id is not None:
            self._on_session_id(resolved)
        return resolved

    def output(self, *, text: str, session_id: str | None = None, final: bool = False) -> None:
        # Emit BOTH `final` (spec §10.3 table) and `is_final` (generated field).
        self._wire.notify(
            "agent/output",
            {
                "kind": "output",
                "text": text,
                "session_id": self._session(session_id),
                "final": final,
                "is_final": final,
            },
        )

    def thinking(self, *, text: str, session_id: str | None = None) -> None:
        self._wire.notify(
            "agent/thinking",
            {"kind": "thinking", "text": text, "session_id": self._session(session_id)},
        )

    def tool_call(
        self,
        *,
        name: str,
        arguments: Any = None,
        server: str | None = None,
        session_id: str | None = None,
    ) -> None:
        self._wire.notify(
            "agent/toolCall",
            {
                "kind": "toolCall",
                "name": name,
                "arguments": {} if arguments is None else arguments,
                "server": server,
                "session_id": self._session(session_id),
            },
        )

    def tool_result(
        self,
        *,
        name: str,
        output: str = "",
        success: bool = True,
        session_id: str | None = None,
    ) -> None:
        self._wire.notify(
            "agent/toolResult",
            {
                "kind": "toolResult",
                "name": name,
                "output": output,
                "success": success,
                "session_id": self._session(session_id),
            },
        )

    def error(
        self, *, message: str, recoverable: bool = False, session_id: str | None = None
    ) -> None:
        self._wire.notify(
            "agent/error",
            {
                "kind": "error",
                "message": message,
                "recoverable": recoverable,
                "session_id": self._session(session_id),
            },
        )


def _result_dict(result: Any) -> Any:
    # Normalize a pydantic model or the deprecated `ProviderRunResult` dataclass
    # to a JSON-serializable dict; dicts pass through; primitives pass through.
    if hasattr(result, "model_dump"):
        return result.model_dump(exclude_none=False, by_alias=True)
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        out = dataclasses.asdict(result)
        # Flatten the deprecated dataclass `extra` bag onto the response so
        # authors can carry the remaining AgentRunResponse fields.
        extra = out.pop("extra", None)
        if isinstance(extra, dict):
            out.update(extra)
        return _fill_required(out)
    if isinstance(result, dict):
        return _fill_required(dict(result))
    return result


def _fill_required(out: dict[str, Any]) -> dict[str, Any]:
    """Backfill `AgentRunResponse`'s required `backend` field when an author
    returns the deprecated/sparse result shape without it, so the emitted wire
    payload still decodes host-side."""
    out.setdefault("backend", "")
    return out


def _result_session_id(result: Any) -> str | None:
    """Extract a `session_id` from a provider run result (model/dataclass/dict),
    if present and non-empty, for late session rebinding."""
    sid: Any = getattr(result, "session_id", None)
    if sid is None and isinstance(result, dict):
        sid = result.get("session_id")
    return sid if isinstance(sid, str) and sid else None


def _run_detached(
    request_id: RpcId,
    wire: Wire,
    registry: ProviderSessionRegistry,
    call: Any,
    run_request: AgentRunRequest,
) -> None:
    """Run a long-running `agent/run` / `agent/resume` off the serial loop.

    Registers the session (so `agent/cancel` / `$/cancelRequest` can reach it),
    runs the impl on a bounded worker thread, and sends the final response via
    `wire.send_response`. A `$/cancelRequest`-cancelled run replies with `-32002`
    (spec §6.3 + §4); otherwise the author's `AgentRunResponse` (or `-32603` on a
    thrown error).
    """
    resolved_session_id = getattr(run_request, "session_id", None) or ""
    session = _ActiveSession(
        session_id=resolved_session_id,
        request_id=request_id,
        cancelled=threading.Event(),
    )
    registry.register(session)

    ctx = ProviderCallContext(
        request_id=request_id,
        cancelled=session.cancelled,
        stream=_Sink(wire, resolved_session_id, lambda sid: registry.bind_session(session, sid)),
    )

    def worker() -> None:
        try:
            try:
                result = call(run_request, ctx)
                # Late-bind from the final result's session_id too, in case the
                # impl returned a provider-assigned id without streaming one.
                final_sid = _result_session_id(result)
                if final_sid:
                    registry.bind_session(session, final_sid)
                if session.cancelled_by_request:
                    response = error_response(
                        request_id, ErrorCode.REQUEST_CANCELLED, "request cancelled"
                    )
                else:
                    response = ok_response(request_id, _result_dict(result))
            except Exception as exc:
                if session.cancelled_by_request:
                    response = error_response(
                        request_id, ErrorCode.REQUEST_CANCELLED, "request cancelled"
                    )
                else:
                    response = error_response(
                        request_id, ErrorCode.INTERNAL_ERROR, f"provider error: {exc!s}"
                    )
            finally:
                registry.deregister(session)
            wire.send_response(response)
        except Exception as exc:  # pragma: no cover - last-resort guard
            wire.logger(f"provider run worker error for id {request_id!r}", exc)

    thread = threading.Thread(target=worker, name="animus-provider-run", daemon=True)
    thread.start()
    # Gate EOF on this run so its final response flushes before the loop ends.
    wire.track_worker(thread)


def dispatch_provider(
    request_id: RpcId,
    frame: RpcRequest,
    wire: Wire,
    impl: Provider,
    registry: ProviderSessionRegistry,
) -> RpcResponse | None:
    method = frame.method
    try:
        if method in (PROVIDER_METHODS["run"], PROVIDER_METHODS["resume"]):
            resume_fn = getattr(impl, "resume", None)
            if method == PROVIDER_METHODS["resume"] and not callable(resume_fn):
                return method_not_supported(request_id, method)
            run_request = validate_params(request_id, AgentRunRequest, frame.params)
            # TODO(codex-p2): `agent/resume` shares `AgentRunRequest` with
            # `agent/run`, so a resume that omits `session_id` is accepted and the
            # impl is handed an empty id. Spec §7.2 says resume carries
            # `session_id` "set". Rejecting an unset id here is a pre-existing
            # behavior change orthogonal to the concurrency fix and could regress
            # lenient providers / conformance fixtures, so it is deferred to a
            # focused follow-up rather than bundled into this change.
            call = impl.run if method == PROVIDER_METHODS["run"] else resume_fn
            _run_detached(request_id, wire, registry, call, run_request)
            return None  # detached; final response sent later via send_response
        if method == PROVIDER_METHODS["cancel"]:
            cancel_request = validate_params(request_id, AgentCancelRequest, frame.params)
            # Trigger the in-flight session's cancel token, if any.
            found = registry.cancel_by_session(cancel_request.session_id)
            cancel_fn = getattr(impl, "cancel", None)
            if callable(cancel_fn):
                return ok_response(
                    request_id,
                    _result_dict(cancel_fn(cancel_request, CallContext(request_id=request_id))),
                )
            # No author hook: report based on whether a live session was found.
            return ok_response(
                request_id, {"session_id": cancel_request.session_id, "cancelled": found}
            )
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(request_id, ErrorCode.INTERNAL_ERROR, f"provider error: {exc!s}")
