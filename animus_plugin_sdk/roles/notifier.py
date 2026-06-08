"""notifier role contract.

Methods (from ``animus-notifier-protocol``): ``notifier/notify`` (required),
``notifier/flush`` (optional), ``notifier/schema``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import notifier as gen
from .context import CallContext, HealthReport

NotifierNotifyParams = gen.NotifierNotifyParams
NotifierNotifyResult = gen.NotifierNotifyResult
NotifierFlushParams = gen.NotifierFlushParams
NotifierFlushResult = gen.NotifierFlushResult
NotifierSchema = gen.NotifierSchema
DaemonEventRecord = gen.DaemonEventRecord


@runtime_checkable
class Notifier(Protocol):
    """Hands daemon events to an external connector.

    Required: `notify`. Optional: `flush`, `schema`, `health`.
    """

    def notify(self, params: NotifierNotifyParams, ctx: CallContext) -> Any: ...

    # Optional:
    # def flush(self, params: NotifierFlushParams, ctx: CallContext) -> Any: ...
    # def schema(self, ctx: CallContext) -> NotifierSchema | dict: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "DaemonEventRecord",
    "HealthReport",
    "Notifier",
    "NotifierFlushParams",
    "NotifierFlushResult",
    "NotifierNotifyParams",
    "NotifierNotifyResult",
    "NotifierSchema",
]
