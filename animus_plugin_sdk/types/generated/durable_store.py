# AUTO-GENERATED FROM schemas/animus-durable-store-protocol/_all.json — DO NOT EDIT BY HAND.
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


class AbandonStepRequest(GeneratedModel):
    "Request for [`METHOD_DURABLE_ABANDON_STEP`]."
    reason: Optional[str] = Field(default=None)
    step_id: str


class AbandonStepResponse(GeneratedModel):
    "Response for [`METHOD_DURABLE_ABANDON_STEP`]."
    ack: bool


class BeginStepRequest(GeneratedModel):
    "Request for [`METHOD_DURABLE_BEGIN_STEP`]."
    idempotency_key: str
    payload: Any = Field(default=None)
    phase_id: str
    reservation_ttl_secs: Optional[int] = Field(default=None, ge=0)
    run_id: str
    step_name: str


class StepError(GeneratedModel):
    "Structured error payload returned with PRIOR_ERROR or carried by"
    code: str
    details: Any = Field(default=None)
    message: str


class BeginStepResponse(GeneratedModel):
    "Response for [`METHOD_DURABLE_BEGIN_STEP`]."
    prior_error: Optional["StepError"] = Field(default=None)
    prior_output: Any = Field(default=None)
    reservation_expires_at: Optional[str] = Field(default=None)
    status: str
    step_id: str


class BeginWorkflowRunRequest(GeneratedModel):
    "Request for [`METHOD_DURABLE_BEGIN_WORKFLOW_RUN`]."
    inputs: Any = Field(default=None)
    phase_id: str
    run_id: str


class BeginWorkflowRunResponse(GeneratedModel):
    "Response for [`METHOD_DURABLE_BEGIN_WORKFLOW_RUN`]."
    epoch: int = Field(ge=0)


class CommitStepRequest(GeneratedModel):
    "Request for [`METHOD_DURABLE_COMMIT_STEP`]."
    error: Optional["StepError"] = Field(default=None)
    outcome: str
    output: Any = Field(default=None)
    step_id: str


class CommitStepResponse(GeneratedModel):
    "Response for [`METHOD_DURABLE_COMMIT_STEP`]."
    ack: bool


class DurableStoreCapabilities(GeneratedModel):
    "Capability flags for durable_store plugins."
    default_reservation_ttl_secs: Optional[int] = Field(default=None, ge=0)
    max_payload_bytes: Optional[int] = Field(default=None, ge=0)
    supports_recovery: Optional[bool] = Field(default=None)


class InFlightRun(GeneratedModel):
    "A run that had outstanding reservations at recovery time."
    last_committed_step: Optional[str] = Field(default=None)
    phase_id: str
    replay_state: Any = Field(default=None)
    run_id: str


class QueryRunRequest(GeneratedModel):
    "Request for [`METHOD_DURABLE_QUERY_RUN`]."
    phase_id: str
    run_id: str


class StepRecord(GeneratedModel):
    "A committed step record returned by [`METHOD_DURABLE_QUERY_RUN`]."
    committed_at: str
    error: Optional["StepError"] = Field(default=None)
    idempotency_key: str
    outcome: str
    output: Any = Field(default=None)
    step_id: str
    step_name: str


class QueryRunResponse(GeneratedModel):
    "Response for [`METHOD_DURABLE_QUERY_RUN`]."
    phase_id: str
    run_id: str
    status: str
    steps: list["StepRecord"]


class RecoverInFlightRequest(GeneratedModel):
    "Request for [`METHOD_DURABLE_RECOVER_IN_FLIGHT`]."
    since_epoch: int = Field(ge=0)


class RecoverInFlightResponse(GeneratedModel):
    "Response for [`METHOD_DURABLE_RECOVER_IN_FLIGHT`]."
    in_flight: list["InFlightRun"]


AbandonStepRequest.model_rebuild()
AbandonStepResponse.model_rebuild()
BeginStepRequest.model_rebuild()
StepError.model_rebuild()
BeginStepResponse.model_rebuild()
BeginWorkflowRunRequest.model_rebuild()
BeginWorkflowRunResponse.model_rebuild()
CommitStepRequest.model_rebuild()
CommitStepResponse.model_rebuild()
DurableStoreCapabilities.model_rebuild()
InFlightRun.model_rebuild()
QueryRunRequest.model_rebuild()
StepRecord.model_rebuild()
QueryRunResponse.model_rebuild()
RecoverInFlightRequest.model_rebuild()
RecoverInFlightResponse.model_rebuild()
