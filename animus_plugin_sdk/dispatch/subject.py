"""subject_backend dispatcher.

Re-platformed onto the generated pydantic ``SubjectFilter`` while preserving
every back-compat behavior the published subject plugins rely on: canonical
``subject/*`` routes, legacy ``<kind>/*`` routes, the daemon's ``{filter}``
envelope unwrap, CLI ``body``→``description`` mapping, route-kind backfill, the
``ensure_wire_subject`` safety net, and null-get → not-found. Adds the optional
``subject/delete`` verb (``-32001`` when not implemented).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..roles.subject import Subject, SubjectBackend, SubjectCallContext
from ..types import ErrorCode, PluginCapabilities, RpcId, RpcRequest, RpcResponse
from ..types.generated.subject import SubjectFilter
from .shared import (
    ParamValidationError,
    error_response,
    method_not_supported,
    ok_response,
    validate_params,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _call_schema(schema_fn: Any, ctx: SubjectCallContext) -> Any:
    """Invoke an optional `schema` hook, tolerating both the current
    `schema(ctx)` signature and the historical no-arg `schema()`, and normalize
    a returned pydantic model to a JSON-serializable dict."""
    try:
        out = schema_fn(ctx)
    except TypeError:
        out = schema_fn()
    return out.model_dump(exclude_none=False, by_alias=True) if hasattr(out, "model_dump") else out


def _has(impl: Any, name: str) -> bool:
    return callable(getattr(impl, name, None))


def derive_subject_capabilities(
    impl: SubjectBackend,
    kinds: list[str],
    projections: list[str],
) -> PluginCapabilities:
    methods: list[str] = ["subject/list", "subject/get", "subject/schema", "health/check"]
    if _has(impl, "update"):
        methods.append("subject/update")
    if _has(impl, "create"):
        methods.append("subject/create")
    if _has(impl, "status"):
        methods.append("subject/status")
    if _has(impl, "next"):
        methods.append("subject/next")
    if _has(impl, "delete"):
        methods.append("subject/delete")
    # Legacy `<kind>/<verb>` compatibility routes for older daemon builds.
    legacy_verbs = [m[len("subject/") :] for m in methods if m.startswith("subject/")]
    for kind in kinds:
        for verb in legacy_verbs:
            methods.append(f"{kind}/{verb}")
    return PluginCapabilities(
        methods=methods,
        streaming=False,
        progress=False,
        cancellation=False,
        subject_kinds=list(kinds),
        projections=list(projections),
    )


def ensure_wire_subject(s: Subject | dict[str, Any]) -> dict[str, Any]:
    """Fill mandatory wire fields (`status`, `created_at`, `updated_at`).

    Safety net so sparse hello-world subjects still produce wire payloads the
    Rust host can decode (it parses `created_at`/`updated_at` as
    `DateTime<Utc>`; empty strings fail the decode).
    """
    now_iso = _now_iso()
    if isinstance(s, Subject):
        data = s.model_dump(exclude_none=False, by_alias=True)
    else:
        data = dict(s)
    if not data.get("status"):
        data["status"] = "ready"
    if not data.get("created_at"):
        data["created_at"] = now_iso
    if not data.get("updated_at"):
        data["updated_at"] = now_iso
    return data


def _default_subject_schema(kinds: list[str], impl: SubjectBackend) -> dict[str, Any]:
    return {
        "kinds": kinds,
        "status_values": ["ready", "in-progress", "blocked", "done", "cancelled"],
        "supports_watch": False,
        "supports_create": _has(impl, "create"),
        "supports_delete": _has(impl, "delete"),
        "supports_pagination": True,
        "native_status_values": [],
        "status_dispatch_hints": [],
        "custom_fields": [],
    }


def dispatch_subject(
    request_id: RpcId,
    frame: RpcRequest,
    impl: SubjectBackend,
    declared_kinds: list[str],
) -> RpcResponse:
    method = frame.method
    slash = method.find("/")
    if slash < 1:
        return error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"unknown method '{method}'")
    prefix = method[:slash]
    verb = method[slash + 1 :]
    raw_params = frame.params if isinstance(frame.params, dict) else {}

    def matches_declared(incoming: str) -> bool:
        for decl in declared_kinds:
            if decl == incoming:
                return True
            if decl.endswith(".*") and incoming.startswith(decl[:-1]):
                return True
        return False

    def kind_from_id(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        colon = value.find(":")
        return value[:colon] if colon > 0 else None

    def kind_from_params() -> str:
        explicit = raw_params.get("kind")
        if isinstance(explicit, str) and explicit:
            return explicit
        nested = raw_params.get("filter")
        if isinstance(nested, dict):
            nk = nested.get("kind")
            if isinstance(nk, list) and nk and isinstance(nk[0], str):
                return nk[0]
        if isinstance(explicit, list) and explicit and isinstance(explicit[0], str):
            return explicit[0]
        id_kind = kind_from_id(raw_params.get("id"))
        if id_kind:
            return id_kind
        return declared_kinds[0] if declared_kinds else "subject"

    legacy_kind_route = prefix != "subject"
    if legacy_kind_route:
        kind = prefix
    else:
        kind = kind_from_params()
        # Canonical `subject/*` routes must stay within the declared kinds: never
        # let a `task`-only backend be invoked as a `requirement` backend because
        # the host sent `filter.kind=["requirement"]` / `id="requirement:1"`.
        if declared_kinds and not matches_declared(kind):
            kind = declared_kinds[0]

    if legacy_kind_route and declared_kinds and not matches_declared(kind):
        return error_response(
            request_id,
            ErrorCode.METHOD_NOT_FOUND,
            f"plugin does not serve subject kind '{kind}'",
        )

    ctx = SubjectCallContext(request_id=request_id, kind=kind)

    try:
        if verb == "schema":
            schema_fn = getattr(impl, "schema", None)
            if callable(schema_fn):
                return ok_response(request_id, _call_schema(schema_fn, ctx))
            return ok_response(
                request_id,
                _default_subject_schema(declared_kinds if declared_kinds else [kind], impl),
            )
        if verb == "list":
            flat = (
                dict(raw_params["filter"])
                if isinstance(raw_params.get("filter"), dict)
                else dict(raw_params)
            )
            requested = flat.get("kind")
            if legacy_kind_route or requested is None:
                # Legacy `<kind>/list`, or no kind filter → force the routed kind.
                flat["kind"] = [kind]
            elif declared_kinds and isinstance(requested, list):
                # Canonical route with an explicit kind filter: clamp it to the
                # declared set so a `task`-only backend never receives
                # `kind=["task", "requirement"]`. If nothing in the requested
                # filter is served, fall back to the routed kind.
                clamped = [k for k in requested if isinstance(k, str) and matches_declared(k)]
                flat["kind"] = clamped if clamped else [kind]
            value = validate_params(request_id, SubjectFilter, flat)
            list_out = impl.list(value, ctx)
            out_dict = (
                list_out.model_dump(exclude_none=False, by_alias=True)
                if hasattr(list_out, "model_dump")
                else dict(list_out)
            )
            subjects = [ensure_wire_subject(s) for s in (out_dict.get("subjects") or [])]
            response: dict[str, Any] = {
                "subjects": subjects,
                "fetched_at": out_dict.get("fetched_at") or _now_iso(),
            }
            if out_dict.get("next_cursor") is not None:
                response["next_cursor"] = out_dict["next_cursor"]
            return ok_response(request_id, response)
        if verb == "get":
            subject_id = raw_params.get("id")
            if not isinstance(subject_id, str) or not subject_id:
                return error_response(
                    request_id,
                    ErrorCode.INVALID_PARAMS,
                    "subject/get requires string id",
                    {"category": "invalid_request"},
                )
            # Pass the full params through (after validating `id`) so backends
            # that accept extra get-options (projections, expand flags, …) keep
            # receiving them.
            get_out: Subject | None = impl.get(dict(raw_params), ctx)
            if get_out is None:
                return error_response(
                    request_id,
                    ErrorCode.INVALID_PARAMS,
                    f"not found: subject '{subject_id}'",
                    {"category": "not_found"},
                )
            return ok_response(request_id, ensure_wire_subject(get_out))
        if verb == "create":
            create_fn = getattr(impl, "create", None)
            if not callable(create_fn):
                return method_not_supported(request_id, method)
            create_params = dict(raw_params)
            create_params["kind"] = kind
            # CLI sends `body`; SDK exposes `description`. Normalize.
            if create_params.get("body") is not None and create_params.get("description") is None:
                create_params["description"] = create_params.pop("body")
            return ok_response(request_id, ensure_wire_subject(create_fn(create_params, ctx)))
        if verb == "update":
            update_fn = getattr(impl, "update", None)
            if not callable(update_fn):
                return method_not_supported(request_id, method)
            return ok_response(request_id, ensure_wire_subject(update_fn(raw_params, ctx)))
        if verb == "status":
            status_fn = getattr(impl, "status", None)
            if not callable(status_fn):
                return method_not_supported(request_id, method)
            return ok_response(request_id, ensure_wire_subject(status_fn(raw_params, ctx)))
        if verb == "next":
            next_fn = getattr(impl, "next", None)
            if not callable(next_fn):
                return method_not_supported(request_id, method)
            next_out: Subject | None = next_fn(raw_params, ctx)
            return ok_response(
                request_id,
                ensure_wire_subject(next_out) if next_out is not None else None,
            )
        if verb == "delete":
            delete_fn = getattr(impl, "delete", None)
            if not callable(delete_fn):
                return method_not_supported(request_id, method)
            subject_id = raw_params.get("id")
            if not isinstance(subject_id, str) or not subject_id:
                return error_response(
                    request_id,
                    ErrorCode.INVALID_PARAMS,
                    "subject/delete requires string id",
                    {"category": "invalid_request"},
                )
            res = delete_fn({"id": subject_id}, ctx)
            # Authors may return None/void, a dict, or the generated
            # DeleteSubjectResponse model. Read `ok` from any of them; default
            # to True only when the impl gives no explicit verdict.
            if isinstance(res, dict):
                ok = bool(res.get("ok", True))
            elif hasattr(res, "ok"):
                ok = bool(res.ok)
            else:
                ok = True
            return ok_response(request_id, {"ok": ok})
        return error_response(request_id, ErrorCode.METHOD_NOT_FOUND, f"unknown method '{method}'")
    except ParamValidationError as exc:
        return exc.response
    except Exception as exc:
        return error_response(
            request_id,
            ErrorCode.INTERNAL_ERROR,
            f"subject backend error: {exc!s}",
        )
