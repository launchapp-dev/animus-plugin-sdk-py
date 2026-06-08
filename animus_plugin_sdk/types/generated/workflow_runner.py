# AUTO-GENERATED FROM schemas/animus-workflow-runner-protocol/_all.json — DO NOT EDIT BY HAND.
# Regenerate via: python scripts/codegen.py
# ruff: noqa
from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class GeneratedModel(BaseModel):
    """Base for generated wire models: extra fields preserved (forward compat)."""

    model_config = ConfigDict(
        extra="allow", populate_by_name=True, protected_namespaces=()
    )


class PhaseEventVariant0(GeneratedModel):
    "Phase started."
    attempt: int = Field(ge=0)
    kind: Literal["started"]
    phase_id: str
    ts: str

class PhaseEventVariant1(GeneratedModel):
    "Phase recorded a decision contract verdict."
    confidence: Optional[float] = Field(default=None)
    kind: Literal["decision"]
    phase_id: str
    ts: str
    verdict: str

class PhaseEventVariant2(GeneratedModel):
    "Phase finished with a final status."
    kind: Literal["completed"]
    phase_id: str
    status: str
    ts: str

PhaseEvent = Union[PhaseEventVariant0, PhaseEventVariant1, PhaseEventVariant2]


class PhaseResultSnapshot(GeneratedModel):
    "A single phase's result snapshot returned in [`WorkflowExecuteResult`]."
    close_reason: Optional[str] = Field(default=None)
    duration_secs: int = Field(ge=0)
    metadata: Any
    next_phase_id: Optional[str] = Field(default=None)
    outcome: Any
    phase_id: str
    status: str


class SubjectRef(GeneratedModel):
    "Backend-qualified subject reference with optional display metadata."
    description: Optional[str] = Field(default=None)
    id: str
    kind: str
    labels: list[str] = Field(default_factory=list)
    metadata: Any = Field(default=None)
    title: Optional[str] = Field(default=None)


class SubjectDispatch(GeneratedModel):
    "Full dispatch envelope handed off from queue / scheduler / trigger to the"
    input: Any = Field(default=None)
    priority: Optional[str] = Field(default=None)
    requested_at: str
    subject: "SubjectRef"
    trigger_source: str
    vars: dict[str, str] = Field(default_factory=dict)
    workflow_ref: str


class WorkflowExecuteRequest(GeneratedModel):
    "Parameters for [`METHOD_WORKFLOW_EXECUTE`]."
    description: Optional[str] = Field(default=None)
    input: Any = Field(default=None)
    mcp_config: Any = Field(default=None)
    model: Optional[str] = Field(default=None)
    phase_filter: Optional[str] = Field(default=None)
    phase_routing: Any = Field(default=None)
    phase_timeout_secs: Optional[int] = Field(default=None, ge=0)
    requirement_id: Optional[str] = Field(default=None)
    subject_dispatch: Optional["SubjectDispatch"] = Field(default=None)
    subject_ref: Optional["SubjectRef"] = Field(default=None)
    task_id: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    tool: Optional[str] = Field(default=None)
    vars: dict[str, str] = Field(default_factory=dict)
    workflow_id: Optional[str] = Field(default=None)
    workflow_ref: Optional[str] = Field(default=None)


class WorkflowExecuteResult(GeneratedModel):
    "Result of [`METHOD_WORKFLOW_EXECUTE`]."
    execution_cwd: str
    phase_events: list["PhaseEvent"] = Field(default_factory=list)
    phase_results: list["PhaseResultSnapshot"]
    phases_completed: int = Field(ge=0)
    phases_requested: list[str]
    phases_total: int = Field(ge=0)
    post_success: Any
    subject_id: str
    success: bool
    total_duration_secs: int = Field(ge=0)
    workflow_id: str
    workflow_ref: str
    workflow_status: str


class WorkflowPhaseRunRequest(GeneratedModel):
    "Parameters for [`METHOD_WORKFLOW_RUN_PHASE`]."
    dispatch_input: Optional[str] = Field(default=None)
    execution_cwd: str
    mcp_config: Any = Field(default=None)
    model_override_: Optional[str] = Field(default=None, alias="model_override")
    phase_attempt: int = Field(ge=0)
    phase_id: str
    phase_routing: Any = Field(default=None)
    phase_timeout_secs: Optional[int] = Field(default=None, ge=0)
    pipeline_vars: dict[str, str] = Field(default_factory=dict)
    rework_context: Optional[str] = Field(default=None)
    schedule_input: Optional[str] = Field(default=None)
    subject_description: str
    subject_id: str
    subject_title: str
    task_complexity: Optional[str] = Field(default=None)
    tool_override: Optional[str] = Field(default=None)
    workflow_id: str
    workflow_ref: str


class WorkflowPhaseRunResult(GeneratedModel):
    "Result of [`METHOD_WORKFLOW_RUN_PHASE`]."
    duration_secs: int = Field(ge=0)
    metadata: Any
    model: Optional[str] = Field(default=None)
    outcome: Any
    phase_status: str
    signals: list[Any] = Field(default_factory=list)
    tool: Optional[str] = Field(default=None)


class WorkflowRunnerCapabilities(GeneratedModel):
    "Backend-specific capability flags serialized into"
    crash_recovery: Optional[bool] = Field(default=None)
    manual_pause_support: Optional[bool] = Field(default=None)
    phase_decision_parsing: Optional[bool] = Field(default=None)
    post_success_actions: Optional[bool] = Field(default=None)
    rework_context_support: Optional[bool] = Field(default=None)


class WorkflowRunnerManifest(GeneratedModel):
    "Static manifest a workflow_runner plugin declares at install time."
    capabilities: "WorkflowRunnerCapabilities"
    description: str
    name: str
    version: str


PhaseResultSnapshot.model_rebuild()
SubjectRef.model_rebuild()
SubjectDispatch.model_rebuild()
WorkflowExecuteRequest.model_rebuild()
WorkflowExecuteResult.model_rebuild()
WorkflowPhaseRunRequest.model_rebuild()
WorkflowPhaseRunResult.model_rebuild()
WorkflowRunnerCapabilities.model_rebuild()
WorkflowRunnerManifest.model_rebuild()
