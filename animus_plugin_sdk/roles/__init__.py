"""Back-compat barrel for role contracts.

The contracts now live one-per-file under this package and are also published
as subpath modules (``animus_plugin_sdk.subject``, ``.provider``, …). This
module re-exports them so the historical ``from animus_plugin_sdk.roles import
SubjectBackend`` path and the top-level package keep working unchanged.
"""

from __future__ import annotations

from .context import CallContext, HealthReport
from .durable_store import DurableStore
from .log_storage import LogStorageBackend
from .memory_store import MemoryStore
from .notifier import Notifier
from .provider import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStream,
    Provider,
    ProviderCallContext,
    ProviderRunParams,
    ProviderRunResult,
)
from .queue import Queue
from .subject import (
    Subject,
    SubjectBackend,
    SubjectCallContext,
    SubjectCreateRequest,
    SubjectListParams,
    SubjectListResult,
    SubjectPatch,
    SubjectStatus,
)
from .transport import TransportBackend
from .trigger import TriggerBackend, TriggerEvent, TriggerSchema
from .workflow_runner import WorkflowRunner

__all__ = [
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentStream",
    "CallContext",
    "DurableStore",
    "HealthReport",
    "LogStorageBackend",
    "MemoryStore",
    "Notifier",
    "Provider",
    "ProviderCallContext",
    "ProviderRunParams",
    "ProviderRunResult",
    "Queue",
    "Subject",
    "SubjectBackend",
    "SubjectCallContext",
    "SubjectCreateRequest",
    "SubjectListParams",
    "SubjectListResult",
    "SubjectPatch",
    "SubjectStatus",
    "TransportBackend",
    "TriggerBackend",
    "TriggerEvent",
    "TriggerSchema",
    "WorkflowRunner",
]
