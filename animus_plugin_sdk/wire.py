"""Newline-delimited JSON-RPC 2.0 transport over stdio.

Mirrors the Rust runtime in `crates/animus-plugin-runtime/src/lib.rs`
and the TS SDK's `wire.ts`:

  - one JSON-RPC frame per line of stdin
  - replies + server-streaming notifications are newline-terminated JSON
    written to stdout
  - parse errors on a single line are logged-and-skipped (do not kill the
    read loop)
  - empty/whitespace-only lines are ignored

Stdout is reserved for protocol frames; SDK diagnostics MUST go to stderr.

Sync API (asyncio is overkill for stdio dispatch and complicates the SDK).
Pattern: `for line in sys.stdin: dispatch(parse(line))`.
"""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import IO, Any

from .types import ErrorCode, RpcError, RpcId, RpcNotification, RpcRequest, RpcResponse

FrameHandler = Callable[[RpcRequest], "RpcResponse | None"]
"""Handler invoked for every parsed inbound JSON-RPC frame.

Return `None` for notifications (no response expected).
"""

Logger = Callable[[str, BaseException | None], None]


def _default_logger(msg: str, err: BaseException | None = None) -> None:
    if err is not None:
        sys.stderr.write(f"[animus-plugin-sdk] {msg}: {err!s}\n")
    else:
        sys.stderr.write(f"[animus-plugin-sdk] {msg}\n")


def encode_frame(frame: RpcResponse | RpcNotification | RpcRequest) -> str:
    """Encode a single JSON-RPC frame as a newline-terminated string.

    Exposed for tests; production code should go through `Wire.send_response`
    or `Wire.send_notification`.

    JSON-RPC 2.0 requires:
      - response frames: exactly one of `result` or `error`; `id` always present
        (including `null` when the original request id was `null`).
      - notification frames: no `id`.
      - request frames: `id` present (including `null`) when expecting a reply.

    We therefore drop the unused half of a response (e.g. omit `error` on an
    `ok` reply) but always preserve `id` and the populated half, even when
    they are `null` — `exclude_none` alone would corrupt the wire shape.
    """
    payload: dict[str, Any] = {"jsonrpc": "2.0"}
    if isinstance(frame, RpcResponse):
        # Always emit `id` (possibly null). Emit exactly one of `result` /
        # `error` based on which was set; preserve `result: null` verbatim
        # (e.g. `subject/next` returning no subject).
        payload["id"] = frame.id
        if frame.error is not None:
            err_dict = frame.error.model_dump(exclude_none=True)
            payload["error"] = err_dict
        else:
            payload["result"] = frame.result
    elif isinstance(frame, RpcNotification):
        payload["method"] = frame.method
        if frame.params is not None:
            payload["params"] = frame.params
    else:  # RpcRequest
        payload["method"] = frame.method
        if frame.id is not None or "id" in frame.model_fields_set:
            payload["id"] = frame.id
        if frame.params is not None:
            payload["params"] = frame.params
    # Preserve any extra fields the wire types allow (`extra="allow"`).
    extras = frame.model_extra or {}
    for k, v in extras.items():
        if k not in payload:
            payload[k] = v
    return json.dumps(payload, separators=(",", ":")) + "\n"


def parse_frame(line: str) -> RpcRequest:
    """Parse one trimmed line into an `RpcRequest`.

    Raises `ValueError` on invalid JSON or structurally invalid JSON-RPC
    (missing `jsonrpc: "2.0"` or `method`).
    """
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("frame is not a JSON object")
    if value.get("jsonrpc") != "2.0":
        raise ValueError(f"unsupported jsonrpc version: {value.get('jsonrpc')!r}")
    method = value.get("method")
    if not isinstance(method, str) or not method:
        raise ValueError("frame missing string `method`")
    return RpcRequest.model_validate(value)


def ok_response(request_id: RpcId, result: Any) -> RpcResponse:
    """Build an `ok` response for the given request id."""
    return RpcResponse(jsonrpc="2.0", id=request_id, result=result, error=None)


def error_response(
    request_id: RpcId,
    code: int,
    message: str,
    data: Any | None = None,
) -> RpcResponse:
    """Build an `error` response for the given request id."""
    return RpcResponse(
        jsonrpc="2.0",
        id=request_id,
        result=None,
        error=RpcError(code=code, message=message, data=data),
    )


@dataclass
class Wire:
    """A bound stdio wire for sending frames + driving a read loop.

    Streaming roles (trigger/watch, log_storage/tail) drain an author iterator
    on a background thread and emit notifications while the main loop continues
    to read frames. `_write_lock` guards every stdout frame so a background
    thread's notification never interleaves bytes with the main thread's
    response — each frame is written + flushed atomically.
    """

    input: IO[str]
    output: IO[str]
    logger: Logger = _default_logger
    _write_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    # Bounded out-of-band worker threads (detached provider `agent/run`/`resume`)
    # that own sending their own final response. `run()` joins these at EOF so a
    # run started just before stream close still flushes its final reply. Guarded
    # by `_pending_lock`. (Trigger/log-storage watch loops are unbounded and stay
    # as fire-and-forget daemon threads — they are NOT tracked here.)
    _pending: list[threading.Thread] = field(default_factory=list, repr=False)
    _pending_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def send_response(self, response: RpcResponse) -> None:
        with self._write_lock:
            self.output.write(encode_frame(response))
            self.output.flush()

    def send_notification(self, notification: RpcNotification) -> None:
        with self._write_lock:
            self.output.write(encode_frame(notification))
            self.output.flush()

    def notify(self, method: str, params: Any | None = None) -> None:
        """Convenience: build + send a notification from method/params."""
        frame = RpcNotification(jsonrpc="2.0", method=method, params=params)
        self.send_notification(frame)

    def track_worker(self, thread: threading.Thread) -> None:
        """Register a bounded background worker thread (a detached provider run).

        `run()` joins all registered workers at EOF so their final responses are
        flushed before the loop returns. The thread should already be started.
        """
        with self._pending_lock:
            self._pending.append(thread)

    def _join_workers(self) -> None:
        # Drain bounded workers. A settling run cannot register new workers
        # (run/resume only spawn from the inbound loop, which has ended), so a
        # single snapshot-and-join pass suffices; loop defensively regardless.
        while True:
            with self._pending_lock:
                pending = [t for t in self._pending if t.is_alive()]
                self._pending = pending
                if not pending:
                    return
            for thread in pending:
                thread.join()

    def run(self, handler: FrameHandler) -> None:
        """Begin consuming the input stream until EOF.

        Frames that fail to parse are logged via `self.logger` and skipped,
        matching the Rust runtime's "tracing::warn + continue" behavior.
        """
        try:
            for line in self.input:
                self._dispatch_line(line, handler)
        finally:
            self._join_workers()

    # Internal helper extracted for unit testing.
    def _dispatch_line(self, line: str, handler: FrameHandler) -> None:
        trimmed = line.strip()
        if not trimmed:
            return
        try:
            frame = parse_frame(trimmed)
        except (ValueError, Exception) as exc:
            self.logger("invalid JSON-RPC frame", exc)
            return
        try:
            response = handler(frame)
        except Exception as exc:
            self.logger(f"handler error for method '{frame.method}'", exc)
            # Best-effort surface to host so request_id doesn't dangle.
            # Per JSON-RPC 2.0, ONLY a missing `id` makes a frame a
            # notification; `id: null` is still a request and the client is
            # waiting for a reply. Distinguish missing from explicit-null
            # via `model_fields_set`.
            if "id" in frame.model_fields_set:
                self.send_response(
                    error_response(
                        frame.id,
                        ErrorCode.INTERNAL_ERROR,
                        f"unhandled handler error: {exc!s}",
                    )
                )
            return
        if response is not None:
            self.send_response(response)


def create_wire(
    input: IO[str] | None = None,
    output: IO[str] | None = None,
    logger: Logger | None = None,
) -> Wire:
    """Create a `Wire` bound to the given (or default stdin/stdout) streams."""
    chosen_logger: Logger = logger if logger is not None else _default_logger
    return Wire(
        input=input if input is not None else sys.stdin,
        output=output if output is not None else sys.stdout,
        logger=chosen_logger,
    )


def run_lines(lines: Iterable[str], handler: FrameHandler, output: IO[str]) -> None:
    """Drive a sequence of pre-tokenized lines through the dispatcher.

    Useful in tests and for callers that have already line-buffered input.
    """
    wire = Wire(input=sys.stdin, output=output)
    for line in lines:
        wire._dispatch_line(line, handler)


__all__ = [
    "FrameHandler",
    "Logger",
    "Wire",
    "create_wire",
    "encode_frame",
    "error_response",
    "ok_response",
    "parse_frame",
    "run_lines",
]
