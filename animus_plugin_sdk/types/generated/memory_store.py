# AUTO-GENERATED FROM schemas/animus-memory-store-protocol/_all.json — DO NOT EDIT BY HAND.
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


class MemoryScope(GeneratedModel):
    "Memory scope identifier. The scope id is derived by the plugin from"
    agent_id: Optional[str] = Field(default=None)
    project_id: str
    task_id: Optional[str] = Field(default=None)


class DeleteScopeRequest(GeneratedModel):
    "Request for [`METHOD_MEMORY_DELETE_SCOPE`]."
    scope: "MemoryScope"


class DeleteScopeResponse(GeneratedModel):
    "Response for [`METHOD_MEMORY_DELETE_SCOPE`]."
    ack: bool


class GetMemoryRequest(GeneratedModel):
    "Request for [`METHOD_MEMORY_GET`]."
    key: str
    scope: "MemoryScope"


class GetMemoryResponse(GeneratedModel):
    "Response for [`METHOD_MEMORY_GET`]."
    found: bool
    value: Any = Field(default=None)


class ListScopesRequest(GeneratedModel):
    "Request for [`METHOD_MEMORY_LIST_SCOPES`]."
    cursor: Optional[str] = Field(default=None)
    page_size: Optional[int] = Field(default=None, ge=0)
    project_id: Optional[str] = Field(default=None)


class ListScopesResponse(GeneratedModel):
    "Response for [`METHOD_MEMORY_LIST_SCOPES`]."
    next_cursor: Optional[str] = Field(default=None)
    scopes: list["MemoryScope"]


class MemoryQueryResult(GeneratedModel):
    "A single semantic query hit."
    key: str
    score: float
    value: Any


class MemoryStoreCapabilities(GeneratedModel):
    "Capability flags for memory_store plugins."
    max_query_top_k: Optional[int] = Field(default=None, ge=0)
    native_key_get: Optional[bool] = Field(default=None)
    native_ttl: Optional[bool] = Field(default=None)
    strong_consistency: Optional[bool] = Field(default=None)


class PutMemoryRequest(GeneratedModel):
    "Request for [`METHOD_MEMORY_PUT`]."
    key: str
    scope: "MemoryScope"
    ttl_secs: Optional[int] = Field(default=None, ge=0)
    value: Any


class PutMemoryResponse(GeneratedModel):
    "Response for [`METHOD_MEMORY_PUT`]."
    ack: bool
    indexed_immediately: bool
    record_id: Optional[str] = Field(default=None)


class QueryMemoryRequest(GeneratedModel):
    "Request for [`METHOD_MEMORY_QUERY`]."
    query: str
    scope: "MemoryScope"
    top_k: int = Field(ge=0)


class QueryMemoryResponse(GeneratedModel):
    "Response for [`METHOD_MEMORY_QUERY`]."
    results: list["MemoryQueryResult"]


MemoryScope.model_rebuild()
DeleteScopeRequest.model_rebuild()
DeleteScopeResponse.model_rebuild()
GetMemoryRequest.model_rebuild()
GetMemoryResponse.model_rebuild()
ListScopesRequest.model_rebuild()
ListScopesResponse.model_rebuild()
MemoryQueryResult.model_rebuild()
MemoryStoreCapabilities.model_rebuild()
PutMemoryRequest.model_rebuild()
PutMemoryResponse.model_rebuild()
QueryMemoryRequest.model_rebuild()
QueryMemoryResponse.model_rebuild()
