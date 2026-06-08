"""memory_store dispatcher (spec §7.8)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..roles.context import CallContext
from ..roles.memory_store import MemoryStore
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.memory_store import (
    DeleteScopeRequest,
    GetMemoryRequest,
    ListScopesRequest,
    PutMemoryRequest,
    QueryMemoryRequest,
)
from .shared import (
    ParamValidationError,
    error_response,
    method_not_found,
    ok_response,
    validate_params,
)

MEMORY_STORE_METHODS = {
    "put": "memory/put",
    "get": "memory/get",
    "query": "memory/query",
    "list_scopes": "memory/list_scopes",
    "delete_scope": "memory/delete_scope",
}

_VALIDATED: dict[str, tuple[str, type[BaseModel]]] = {
    "memory/put": ("put", PutMemoryRequest),
    "memory/get": ("get", GetMemoryRequest),
    "memory/query": ("query", QueryMemoryRequest),
    "memory/list_scopes": ("list_scopes", ListScopesRequest),
    "memory/delete_scope": ("delete_scope", DeleteScopeRequest),
}


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_memory_store(request_id: RpcId, frame: RpcRequest, impl: MemoryStore) -> RpcResponse:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method in _VALIDATED:
            attr, model = _VALIDATED[method]
            value = validate_params(request_id, model, frame.params)
            return ok_response(request_id, _to_dict(getattr(impl, attr)(value, ctx)))
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(request_id, ErrorCode.INTERNAL_ERROR, f"memory_store error: {exc!s}")
