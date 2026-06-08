"""trigger_backend role contract (spec §7.3 / §11).

IMPORTANT: the wire shape of the ``trigger/event`` notification is the FLAT
object defined in spec §11.1 (``event_id``, ``trigger_id``, ``subject_id``,
``subject_kind``, ``action_hint``, ``payload``) — this is
``animus-plugin-protocol::TriggerEvent``, NOT the newer
``animus-trigger-protocol::TriggerEvent``. The plugin-protocol type is the one
the host decodes for this notification, so the contract uses it.

``watch`` returns an iterable / generator of ``TriggerEvent`` (or dict). The SDK
acks ``{"watching": true}`` immediately and drains the iterable on a background
thread, emitting each event as a flat ``trigger/event`` notification.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..types.generated import plugin as gen_plugin
from ..types.generated import trigger as gen_trigger
from .context import CallContext, HealthReport

# Flat wire event (plugin-protocol) + the trigger-protocol schema declaration.
WireTriggerEvent = gen_plugin.TriggerEvent
TriggerSchema = gen_trigger.TriggerSchema


@dataclass
class TriggerEvent:
    """A trigger event emitted on the wire as flat `params` of `trigger/event`
    (spec §11.1). `event_id` is the only required field."""

    event_id: str
    trigger_id: str | None = None
    subject_id: str | None = None
    subject_kind: str | None = None
    action_hint: str | None = None
    payload: Any = None


@runtime_checkable
class TriggerBackend(Protocol):
    """A push-driven event source.

    Required: `watch`. Optional: `ack`, `schema`, `health`.
    """

    def watch(
        self,
        params: dict[str, Any],
        ctx: CallContext,
    ) -> Iterable[TriggerEvent | dict[str, Any]]: ...

    # Optional:
    # def ack(self, params: dict[str, Any], ctx: CallContext) -> None: ...
    # def schema(self, ctx: CallContext) -> TriggerSchema | dict[str, Any]: ...
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "HealthReport",
    "TriggerBackend",
    "TriggerEvent",
    "TriggerSchema",
    "WireTriggerEvent",
]
