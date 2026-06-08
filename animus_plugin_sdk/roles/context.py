"""Shared call context + health-report types used by every role contract."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from ..types import HealthStatus, RpcId


@dataclass
class CallContext:
    """Generic context passed to every role method (extensible)."""

    request_id: RpcId = None
    """Original JSON-RPC request id (for logging / correlation)."""

    cancelled: threading.Event | None = None
    """Cancellation token (analogous to the TS SDK's `ctx.signal`).

    For a provider `run`/`resume`, the SDK sets this to a per-session
    `threading.Event` that is *set* when the host sends `agent/cancel` (matching
    `session_id`) or `$/cancelRequest` (matching the originating request id). A
    cooperating provider can poll `ctx.cancelled.is_set()` or block on
    `ctx.cancelled.wait(timeout=...)` to abort upstream work mid-session. `None`
    for methods that are not cancellable.
    """


@dataclass
class HealthReport:
    """Result of an optional `health()` hook on any role impl."""

    status: HealthStatus = "healthy"
    last_error: str | None = None
    uptime_ms: int | None = None
    memory_usage_bytes: int | None = None


__all__ = ["CallContext", "HealthReport"]
