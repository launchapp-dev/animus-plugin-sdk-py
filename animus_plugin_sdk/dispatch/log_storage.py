"""log_storage_backend dispatcher (spec §7.4 / §12).

``log_storage/store`` persists a batch; optional ``log_storage/query`` and
streaming ``log_storage/tail`` (→ ``log_storage/event`` notifications echoing
the request id) return ``-32001`` when not implemented; ``log_storage/schema``
declares capabilities.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..roles.context import CallContext
from ..roles.log_storage import LogStorageBackend
from ..types import ErrorCode, RpcId, RpcRequest, RpcResponse
from ..types.generated.log_storage import LogEntry, LogQuery
from .shared import (
    ParamValidationError,
    Wire,
    ack_then_stream,
    error_response,
    method_not_found,
    method_not_supported,
    ok_response,
    validate_params,
)

LOG_STORAGE_METHODS = {
    "store": "log_storage/store",
    "query": "log_storage/query",
    "tail": "log_storage/tail",
    "schema": "log_storage/schema",
}


class _StoreParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    entries: list[LogEntry] = Field(default_factory=list)


def _default_schema(impl: LogStorageBackend) -> dict[str, Any]:
    return {
        "supports_query": callable(getattr(impl, "query", None)),
        "supports_tail": callable(getattr(impl, "tail", None)),
        "supports_dedup": False,
        "supports_filtering": {
            "by_level": False,
            "by_source": False,
            "by_target": False,
            "by_time_range": False,
            "by_glob": False,
        },
    }


def _to_dict(value: Any) -> Any:
    return (
        value.model_dump(exclude_none=False, by_alias=True)
        if hasattr(value, "model_dump")
        else value
    )


def dispatch_log_storage(
    request_id: RpcId,
    frame: RpcRequest,
    wire: Wire,
    impl: LogStorageBackend,
) -> RpcResponse | None:
    method = frame.method
    ctx = CallContext(request_id=request_id)
    try:
        if method == LOG_STORAGE_METHODS["store"]:
            store_params = validate_params(request_id, _StoreParams, frame.params)
            return ok_response(
                request_id, _to_dict(impl.store(store_params.model_dump(by_alias=True), ctx))
            )
        if method == LOG_STORAGE_METHODS["query"]:
            query_fn = getattr(impl, "query", None)
            if not callable(query_fn):
                return method_not_supported(request_id, method)
            query = validate_params(request_id, LogQuery, frame.params)
            return ok_response(request_id, _to_dict(query_fn(query, ctx)))
        if method == LOG_STORAGE_METHODS["tail"]:
            tail_fn = getattr(impl, "tail", None)
            if not callable(tail_fn):
                return method_not_supported(request_id, method)
            tail_query = validate_params(request_id, LogQuery, frame.params)
            stream = tail_fn(tail_query, ctx)

            def drain() -> None:
                try:
                    for entry in stream:
                        wire.notify(
                            "log_storage/event", {"id": request_id, "entry": _to_dict(entry)}
                        )
                except Exception as exc:
                    wire.notify(
                        "log_storage/event",
                        {
                            "id": request_id,
                            "error": {
                                "code": ErrorCode.INTERNAL_ERROR,
                                "message": f"log tail error: {exc!s}",
                            },
                        },
                    )

            ack_then_stream(wire, request_id, {"tailing": True}, drain, name="animus-log-tail")
            return None
        if method == LOG_STORAGE_METHODS["schema"]:
            schema_fn = getattr(impl, "schema", None)
            if callable(schema_fn):
                return ok_response(request_id, _to_dict(schema_fn(ctx)))
            return ok_response(request_id, _default_schema(impl))
        return method_not_found(request_id, method)
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(
            request_id, ErrorCode.INTERNAL_ERROR, f"log_storage backend error: {exc!s}"
        )
