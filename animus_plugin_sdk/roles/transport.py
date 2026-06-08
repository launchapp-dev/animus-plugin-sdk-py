"""transport_backend role contract (spec §13)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import transport as gen
from .context import CallContext, HealthReport

TransportConfig = gen.TransportConfig
TransportInfo = gen.TransportInfo
TransportSchema = gen.TransportSchema


@runtime_checkable
class TransportBackend(Protocol):
    """Owns an external protocol surface (HTTP/GraphQL/…).

    Required: `start`. Optional: `shutdown`, `schema`, `health`.
    """

    def start(
        self, params: TransportConfig, ctx: CallContext
    ) -> TransportInfo | dict[str, Any]: ...

    # Optional:
    # def shutdown(self, ctx: CallContext) -> None: ...
    # def schema(self, ctx: CallContext) -> TransportSchema | dict[str, Any]: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "HealthReport",
    "TransportBackend",
    "TransportConfig",
    "TransportInfo",
    "TransportSchema",
]
