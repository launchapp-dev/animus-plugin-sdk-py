"""log_storage_backend role contract (spec §7.4 / §12)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import log_storage as gen
from .context import CallContext, HealthReport

LogEntry = gen.LogEntry
LogQuery = gen.LogQuery
LogQueryResult = gen.LogQueryResult
LogStorageSchema = gen.LogStorageSchema
LogLevel = gen.LogLevel
LogSource = gen.LogSource
SupportsFiltering = gen.SupportsFiltering


@runtime_checkable
class LogStorageBackend(Protocol):
    """Persists structured log entries.

    Required: `store`. Optional: `query`, `tail` (streaming), `schema`,
    `health`. ``tail`` returns an iterable of ``LogEntry`` drained on a
    background thread into ``log_storage/event`` notifications echoing the
    request id.
    """

    def store(self, params: dict[str, Any], ctx: CallContext) -> dict[str, Any]: ...

    # Optional:
    # def query(self, params: LogQuery, ctx: CallContext) -> LogQueryResult | dict: ...
    # def tail(self, params: LogQuery, ctx: CallContext) -> Iterable[LogEntry | dict]: ...
    # def schema(self, ctx: CallContext) -> LogStorageSchema | dict: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "HealthReport",
    "LogEntry",
    "LogLevel",
    "LogQuery",
    "LogQueryResult",
    "LogSource",
    "LogStorageBackend",
    "LogStorageSchema",
    "SupportsFiltering",
]
