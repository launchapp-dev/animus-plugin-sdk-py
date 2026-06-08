"""memory_store role contract (spec §7.8, v1.1.0+)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..types.generated import memory_store as gen
from .context import CallContext, HealthReport

PutMemoryRequest = gen.PutMemoryRequest
PutMemoryResponse = gen.PutMemoryResponse
GetMemoryRequest = gen.GetMemoryRequest
GetMemoryResponse = gen.GetMemoryResponse
QueryMemoryRequest = gen.QueryMemoryRequest
QueryMemoryResponse = gen.QueryMemoryResponse
ListScopesRequest = gen.ListScopesRequest
ListScopesResponse = gen.ListScopesResponse
DeleteScopeRequest = gen.DeleteScopeRequest
DeleteScopeResponse = gen.DeleteScopeResponse


@runtime_checkable
class MemoryStore(Protocol):
    """Persistent semantic memory across runs/agents/tasks.

    Required: `put`, `get`, `query`, `list_scopes`, `delete_scope`. Optional:
    `health`.
    """

    def put(self, params: PutMemoryRequest, ctx: CallContext) -> Any: ...
    def get(self, params: GetMemoryRequest, ctx: CallContext) -> Any: ...
    def query(self, params: QueryMemoryRequest, ctx: CallContext) -> Any: ...
    def list_scopes(self, params: ListScopesRequest, ctx: CallContext) -> Any: ...
    def delete_scope(self, params: DeleteScopeRequest, ctx: CallContext) -> Any: ...

    # Optional:
    # def health(self, ctx: CallContext) -> HealthReport: ...


__all__ = [
    "DeleteScopeRequest",
    "DeleteScopeResponse",
    "GetMemoryRequest",
    "GetMemoryResponse",
    "HealthReport",
    "ListScopesRequest",
    "ListScopesResponse",
    "MemoryStore",
    "PutMemoryRequest",
    "PutMemoryResponse",
    "QueryMemoryRequest",
    "QueryMemoryResponse",
]
