#!/usr/bin/env python3
"""Code-generate **pydantic v2 models** from the Rust-emitted JSON Schema bundles
in ``schemas/<crate>/_all.json``.

The Rust protocol crates are the single source of truth; this emitter is
deterministic and re-runnable (the drift check regenerates into a temp dir and
diffs). It mirrors the TypeScript SDK's ``scripts/codegen.mjs`` Zod emitter so
the two SDKs stay at feature parity.

Output: one module per protocol crate under
``animus_plugin_sdk/types/generated/<module>.py``, each exporting a pydantic
``BaseModel`` subclass (or a type alias) for every ``$def`` in that bundle, plus
a ``generated/__init__.py`` barrel re-exporting every module under a namespace.

Design notes mirror the TS emitter:
  - ``$ref`` resolves to the sibling class within the same module. Forward /
    cyclic references work because every module sets
    ``from __future__ import annotations`` and we call ``model_rebuild()`` at the
    end of the module.
  - Open-string enums on the Rust side (``TriggerActionHint``,
    ``TriggerAckStatus``) flatten an ``Other(String)`` variant to ``str`` on the
    wire; they are emitted as ``str`` aliases so unknown values still validate.
  - Schemaless fields (no type / ``$ref`` / ``oneOf`` / ``anyOf``) — the
    JSON-RPC envelope fields ``params`` / ``result`` / ``payload`` / ``data`` /
    ``id`` / ``input_schema`` and Rust ``serde_json::Value`` fields — emit
    ``Any`` so they stay permissive (never reject a valid frame).
  - ``date-time`` formatted strings stay ``str`` (the wire keeps RFC-3339
    strings; coercing to ``datetime`` would break byte round-trips).
  - Objects allow extra fields (``extra="allow"``) for forward-compat with newer
    hosts/minors, matching the TS ``.passthrough()`` behaviour.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_ROOT = REPO_ROOT / "schemas"
DEFAULT_OUT_DIR = REPO_ROOT / "animus_plugin_sdk" / "types" / "generated"

# Open-string enum vocabularies. Mirrors the TS emitter's OPEN_ENUMS. Each of
# these Rust types has an `Other(String)` variant that flattens to a bare string
# on the wire, so we keep them as `str` (the schema already says `type: string`,
# and the known literals are documented for authors in the docstring).
OPEN_ENUM_DOCS = {
    "TriggerActionHint": ["create_task", "run_workflow"],
    "TriggerAckStatus": [
        "dispatched",
        "queued",
        "unmatched",
        "skipped",
        "failed",
        "shutdown",
    ],
}

# Field names whose value is intentionally schemaless on the wire (serde_json
# Value / JSON-RPC envelope). These emit `Any` regardless of how schemars
# rendered them (it renders them as bare nodes anyway, but this list documents
# intent).
SCHEMALESS_HINT = {
    "payload",
    "extra",
    "fields",
    "input_schema",
    "params",
    "result",
    "data",
    "value",
}


def module_name_for_crate(crate: str) -> str:
    """`animus-log-storage-protocol` -> `log_storage`."""
    stem = crate
    if stem.startswith("animus-"):
        stem = stem[len("animus-") :]
    if stem.endswith("-protocol"):
        stem = stem[: -len("-protocol")]
    return stem.replace("-", "_")


class Context:
    """Per-module rendering context: tracks declared names for ref resolution."""

    def __init__(self, names: set[str]) -> None:
        self.names = names

    def ref_expr(self, ref_name: str) -> str:
        # Always a forward-reference-safe string annotation (the module sets
        # `from __future__ import annotations`, so all annotations are strings).
        if ref_name in self.names:
            return f'"{ref_name}"'
        # Unknown ref (e.g. a type defined in another crate's bundle). Keep
        # permissive rather than emitting a dangling name.
        return "Any"


def render_node(node: object, ctx: Context, field_name: str | None = None) -> str:
    """Render a Python type annotation for an arbitrary JSON-Schema node."""
    if node is True or node is None:
        return "Any"
    if node is False:
        return "Any"
    if not isinstance(node, dict):
        return "Any"

    # $ref -> sibling class.
    ref = node.get("$ref")
    if isinstance(ref, str):
        return ctx.ref_expr(ref.replace("#/$defs/", ""))

    # oneOf / anyOf -> union (internally-tagged enums emit oneOf of objects;
    # nullable refs emit anyOf of [ref, null]).
    variants = node.get("oneOf")
    if variants is None:
        variants = node.get("anyOf")
    if isinstance(variants, list):
        if len(variants) == 1:
            return render_node(variants[0], ctx, field_name)
        # oneOf of `{const: "x", type: "string"}` is a closed string enum.
        if all(
            isinstance(v, dict)
            and isinstance(v.get("const"), str)
            and v.get("type") in ("string", None)
            for v in variants
        ):
            lits = ", ".join(json.dumps(v["const"]) for v in variants)
            return f"Literal[{lits}]"
        # anyOf of [X, {type: null}] -> Optional[X].
        non_null = [v for v in variants if not (isinstance(v, dict) and v.get("type") == "null")]
        has_null = any(isinstance(v, dict) and v.get("type") == "null" for v in variants)
        if has_null and len(non_null) == 1:
            inner = render_node(non_null[0], ctx, field_name)
            return f"Optional[{inner}]"
        rendered = [render_node(v, ctx, field_name) for v in (non_null or variants)]
        # De-dupe while preserving order.
        seen: list[str] = []
        for r in rendered:
            if r not in seen:
                seen.append(r)
        union = seen[0] if len(seen) == 1 else "Union[" + ", ".join(seen) + "]"
        return f"Optional[{union}]" if has_null else union

    if "const" in node:
        return f"Literal[{json.dumps(node['const'])}]"

    enum = node.get("enum")
    if isinstance(enum, list) and all(isinstance(v, str) for v in enum):
        lits = ", ".join(json.dumps(v) for v in enum)
        return f"Literal[{lits}]"

    type_ = node.get("type")
    if isinstance(type_, list):
        non_null = [t for t in type_ if t != "null"]
        has_null = "null" in type_
        if not non_null:
            return "None"
        inner_node = dict(node)
        inner_node["type"] = non_null[0] if len(non_null) == 1 else non_null
        inner = render_node(inner_node, ctx, field_name)
        return f"Optional[{inner}]" if has_null else inner

    if type_ == "string":
        return "str"
    if type_ == "integer":
        return "int"
    if type_ == "number":
        return "float"
    if type_ == "boolean":
        return "bool"
    if type_ == "null":
        return "None"
    if type_ == "array":
        items = node.get("items")
        inner = render_node(items, ctx, field_name) if items is not None else "Any"
        return f"list[{inner}]"
    if type_ == "object":
        add = node.get("additionalProperties")
        if isinstance(add, dict):
            val = render_node(add, ctx, field_name)
            return f"dict[str, {val}]"
        props = node.get("properties")
        if not props:
            return "dict[str, Any]"
        # Inline object with declared properties but no name — fall back to a
        # permissive dict (none of the current bundles hit this for top-level
        # defs; nested ones are rare and stay permissive).
        return "dict[str, Any]"

    # No type, no $ref, no union -> schemaless. Permissive.
    return "Any"


def _numeric_constraints(node: object) -> list[str]:
    """Return pydantic Field numeric-bound kwargs (`ge=`, `le=`) for an
    integer/number node, mirroring the TS emitter's `applyNumericBounds`.

    Unsigned integer formats (`uint`, `uint8`, …) imply `ge=0` when no explicit
    minimum is present.
    """
    if not isinstance(node, dict):
        return []
    # Look through a nullable type-list wrapper (`type: ["integer", "null"]`).
    type_ = node.get("type")
    if isinstance(type_, list):
        non_null = [t for t in type_ if t != "null"]
        type_ = non_null[0] if len(non_null) == 1 else None
    if type_ not in ("integer", "number"):
        return []
    out: list[str] = []
    minimum = node.get("minimum")
    fmt = node.get("format")
    is_unsigned = isinstance(fmt, str) and fmt.startswith("uint")
    if isinstance(minimum, int | float) and not isinstance(minimum, bool):
        out.append(f"ge={minimum}")
    elif is_unsigned:
        out.append("ge=0")
    maximum = node.get("maximum")
    if isinstance(maximum, int | float) and not isinstance(maximum, bool):
        out.append(f"le={maximum}")
    return out


def _field_expr(
    *, alias: str | None, required: bool, annotation: str, constraints: list[str]
) -> str:
    """Build the trailing ` = <default>`/` = Field(...)` for a field, folding in
    any alias, default, and numeric constraints."""
    kwargs: list[str] = []
    if alias is not None:
        kwargs.append(f"alias={json.dumps(alias)}")
    kwargs.extend(constraints)
    if required:
        # Required field: only emit Field(...) if there are kwargs to carry.
        if not kwargs:
            return ""
        return " = Field(" + ", ".join(kwargs) + ")"
    # Optional fields: arrays default to [], maps to {}, else None.
    if annotation.startswith("list["):
        return " = Field(default_factory=list" + ("".join(", " + k for k in kwargs)) + ")"
    if annotation.startswith("dict["):
        return " = Field(default_factory=dict" + ("".join(", " + k for k in kwargs)) + ")"
    kwargs.insert(0, "default=None")
    return " = Field(" + ", ".join(kwargs) + ")"


# pydantic v2 BaseModel attributes a wire field must not shadow. Fields with
# these names (or the protected `model_` prefix) are renamed to `<name>_` and
# carry an `alias` so the wire name round-trips unchanged.
_PYDANTIC_RESERVED = {
    "schema",
    "copy",
    "dict",
    "json",
    "construct",
    "validate",
    "fields",
    "parse_obj",
    "parse_raw",
    "parse_file",
}


def _sanitize_field(name: str) -> tuple[str, str | None]:
    """Return (python_name, alias_or_None). All current field names are valid
    Python identifiers, but guard against keywords, leading digits, and names
    that shadow pydantic ``BaseModel`` attributes (e.g. ``schema``) or the
    protected ``model_`` prefix."""
    import keyword

    if (
        keyword.iskeyword(name)
        or (name and name[0].isdigit())
        or name in _PYDANTIC_RESERVED
        or name.startswith("model_")
    ):
        return f"{name}_", name
    return name, None


def render_object(name: str, node: dict, ctx: Context) -> str:
    props: dict = node.get("properties", {})
    required = set(node.get("required", []))
    lines: list[str] = [f"class {name}(GeneratedModel):"]
    doc = node.get("description")
    if isinstance(doc, str) and doc:
        first = doc.strip().splitlines()[0]
        lines.append(f"    {json.dumps(first)}")
    if not props:
        lines.append("    pass")
        return "\n".join(lines)
    for key, prop in props.items():
        is_required = key in required
        if (
            key in SCHEMALESS_HINT
            and isinstance(prop, dict)
            and "$ref" not in prop
            and "type" not in prop
        ):
            annotation = "Any"
        else:
            annotation = render_node(prop, ctx, key)
        # Optional fields that aren't already Optional-wrapped get widened.
        if (
            not is_required
            and not annotation.startswith("Optional[")
            and not annotation.startswith("list[")
            and not annotation.startswith("dict[")
            and annotation != "Any"
        ):
            annotation = f"Optional[{annotation}]"
        py_name, alias = _sanitize_field(key)
        constraints = _numeric_constraints(prop)
        default = _field_expr(
            alias=alias, required=is_required, annotation=annotation, constraints=constraints
        )
        lines.append(f"    {py_name}: {annotation}{default}")
    return "\n".join(lines)


def render_oneof_object_union(name: str, variants: list, ctx: Context) -> str:
    """Emit a union of named variant classes for an internally-tagged enum
    (oneOf of object variants), e.g. AgentNotification."""
    variant_classes: list[str] = []
    variant_names: list[str] = []
    for i, variant in enumerate(variants):
        vname = f"{name}Variant{i}"
        variant_names.append(vname)
        variant_classes.append(render_object(vname, variant, ctx))
    union = "Union[" + ", ".join(variant_names) + "]"
    chunk = "\n\n".join(variant_classes)
    chunk += f"\n\n{name} = {union}"
    return chunk


def collect_refs(node: object, acc: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            acc.add(ref.replace("#/$defs/", ""))
        for k, v in node.items():
            if k == "$ref":
                continue
            collect_refs(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_refs(v, acc)


def topo_order(names: list[str], defs: dict) -> list[str]:
    deps: dict[str, list[str]] = {}
    name_set = set(names)
    for name in names:
        acc: set[str] = set()
        collect_refs(defs[name], acc)
        acc.discard(name)
        deps[name] = sorted(d for d in acc if d in name_set)
    ordered: list[str] = []
    emitted: set[str] = set()
    visiting: set[str] = set()

    def visit(n: str) -> None:
        if n in emitted or n in visiting:
            return
        visiting.add(n)
        for d in deps[n]:
            visit(d)
        visiting.discard(n)
        if n not in emitted:
            emitted.add(n)
            ordered.append(n)

    for n in names:
        visit(n)
    return ordered


def is_object_def(node: object) -> bool:
    if not isinstance(node, dict):
        return False
    if (
        node.get("type") == "object"
        and isinstance(node.get("properties"), dict)
        and node["properties"]
    ):
        # A map type (additionalProperties schema) is NOT a class.
        if isinstance(node.get("additionalProperties"), dict):
            return False
        return True
    return False


def is_oneof_object_union(node: object) -> bool:
    if not isinstance(node, dict):
        return False
    variants = node.get("oneOf")
    if not isinstance(variants, list) or len(variants) < 2:
        return False
    return all(
        isinstance(v, dict) and v.get("type") == "object" and "properties" in v for v in variants
    )


def compile_bundle(crate: str) -> tuple[str, str, int]:
    bundle = json.loads((SCHEMAS_ROOT / crate / "_all.json").read_text())
    defs: dict = bundle.get("$defs", {})
    names = sorted(defs.keys())
    ordered = topo_order(names, defs)
    ctx = Context(set(names))

    chunks: list[str] = []
    rebuild_targets: list[str] = []
    for name in ordered:
        node = defs[name]
        if name in OPEN_ENUM_DOCS:
            known = ", ".join(OPEN_ENUM_DOCS[name])
            chunks.append(
                f"# Open-string enum (known values: {known}); unknown values round-trip as str.\n"
                f"{name} = str"
            )
            continue
        if is_oneof_object_union(node):
            chunks.append(render_oneof_object_union(name, node["oneOf"], ctx))
            continue
        if is_object_def(node):
            chunks.append(render_object(name, node, ctx))
            rebuild_targets.append(name)
            continue
        # Scalar / enum / map / union alias.
        expr = render_node(node, ctx, None)
        chunks.append(f"{name} = {expr}")

    module = module_name_for_crate(crate)
    banner = (
        f"# AUTO-GENERATED FROM schemas/{crate}/_all.json — DO NOT EDIT BY HAND.\n"
        f"# Regenerate via: python scripts/codegen.py\n"
        f"# ruff: noqa\n"
        f"from __future__ import annotations\n\n"
        f"from typing import Any, Literal, Optional, Union\n\n"
        f"from pydantic import BaseModel, ConfigDict, Field\n\n\n"
        f"class GeneratedModel(BaseModel):\n"
        f'    """Base for generated wire models: extra fields preserved (forward compat)."""\n\n'
        f"    model_config = ConfigDict(\n"
        f'        extra="allow", populate_by_name=True, protected_namespaces=()\n'
        f"    )\n\n\n"
    )
    body = "\n\n\n".join(chunks) + "\n"
    rebuild = ""
    if rebuild_targets:
        rebuild = "\n\n" + "\n".join(f"{t}.model_rebuild()" for t in rebuild_targets) + "\n"
    return module, banner + body + rebuild, len(names)


def discover_crates() -> list[str]:
    out = []
    for d in sorted(SCHEMAS_ROOT.iterdir()):
        if d.is_dir() and (d / "_all.json").is_file():
            out.append(d.name)
    return out


def main() -> None:
    out_dir = Path(os.environ.get("ANIMUS_CODEGEN_OUT_DIR") or DEFAULT_OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    quiet = bool(os.environ.get("ANIMUS_CODEGEN_OUT_DIR"))
    crates = discover_crates()
    modules: list[str] = []
    for crate in crates:
        module, content, count = compile_bundle(crate)
        (out_dir / f"{module}.py").write_text(content)
        modules.append(module)
        if not quiet:
            print(f"wrote {module}.py ({count} types)", file=sys.stderr)

    # Barrel: re-export every generated module as a submodule namespace.
    barrel = [
        "# AUTO-GENERATED — DO NOT EDIT BY HAND.",
        "# Regenerate via: python scripts/codegen.py",
        "# ruff: noqa",
        "",
    ]
    for m in modules:
        barrel.append(f"from . import {m} as {m}")
    barrel.append("")
    barrel.append("__all__ = [")
    for m in modules:
        barrel.append(f"    {json.dumps(m)},")
    barrel.append("]")
    barrel.append("")
    (out_dir / "__init__.py").write_text("\n".join(barrel))
    if not quiet:
        print(f"wrote __init__.py (barrel, {len(modules)} modules)", file=sys.stderr)


if __name__ == "__main__":
    main()
