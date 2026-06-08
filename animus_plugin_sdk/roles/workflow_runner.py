"""workflow_runner role contract (spec §7.5, v1.1.0+)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import workflow_runner as gen
from .context import CallContext, HealthReport

WorkflowExecuteRequest = gen.WorkflowExecuteRequest
WorkflowExecuteResult = gen.WorkflowExecuteResult
WorkflowPhaseRunRequest = gen.WorkflowPhaseRunRequest
WorkflowPhaseRunResult = gen.WorkflowPhaseRunResult
PhaseEvent = gen.PhaseEvent
PhaseResultSnapshot = gen.PhaseResultSnapshot


@runtime_checkable
class WorkflowRunner(Protocol):
    """Executes Animus workflow YAML.

    Required: `execute`, `run_phase`. Optional: `health`.
    """

    def execute(self, params: WorkflowExecuteRequest, ctx: CallContext) -> Any: ...
    def run_phase(self, params: WorkflowPhaseRunRequest, ctx: CallContext) -> Any: ...

    # Optional:
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "HealthReport",
    "PhaseEvent",
    "PhaseResultSnapshot",
    "WorkflowExecuteRequest",
    "WorkflowExecuteResult",
    "WorkflowPhaseRunRequest",
    "WorkflowPhaseRunResult",
    "WorkflowRunner",
]
