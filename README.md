# animus-plugin-sdk (Python)

Python SDK for authoring [Animus](https://github.com/launchapp-dev/animus-cli)
stdio plugins. Pydantic-typed, with the Rust protocol crates as the single
source of truth. Covers every plugin role: subject, provider, trigger,
transport, log-storage, queue, workflow-runner, durable-store, memory-store,
and notifier.

This is the Python parallel to the TypeScript SDK
(`launchapp-dev/animus-plugin-sdk-ts`). Both SDKs **generate** their wire types
from the same source-of-truth JSON Schemas published by the
[`launchapp-dev/animus-protocol`](https://github.com/launchapp-dev/animus-protocol)
repo (the TS SDK emits Zod schemas; this SDK emits pydantic v2 models).

## Install

```sh
pip install animus-plugin-sdk
```

## Hello world (subject backend)

```python
# my_plugin.py
from animus_plugin_sdk import (
    PluginKind,
    Subject,
    SubjectCallContext,
    SubjectListParams,
    SubjectListResult,
    define_plugin,
)


class HelloBackend:
    def list(self, params: SubjectListParams, ctx: SubjectCallContext) -> SubjectListResult:
        return SubjectListResult(
            subjects=[Subject(id="task:1", kind=ctx.kind, title="hello",
                              status="ready", created_at="", updated_at="")],
            fetched_at="",
        )

    def get(self, params, ctx):
        if params.get("id") == "task:1":
            return Subject(id="task:1", kind=ctx.kind, title="hello",
                           status="ready", created_at="", updated_at="")
        return None


if __name__ == "__main__":
    define_plugin(
        kind=PluginKind.SUBJECT_BACKEND,
        impl=HelloBackend(),
        name="hello-subjects",
        version="0.1.0",
        description="Hard-coded sample backend",
        subject_kinds=["task"],
        env_required=["MY_API_TOKEN"],
    ).run()
```

Run the plugin to drive the JSON-RPC loop on stdin/stdout (`python my_plugin.py`)
or print the discovery manifest (`python my_plugin.py --manifest`). The SDK
auto-fills the wire-mandatory `status` / `created_at` / `updated_at` fields when
a hello-world example omits them.

## Layered submodule structure

The top-level `animus_plugin_sdk` keeps the back-compat surface: `define_plugin`,
the base/runtime layer (wire, handshake, error codes, `PROTOCOL_VERSION`), and
every role contract. Each role is **also** importable as a submodule mirroring
the Rust crates, exposing that role's contract + generated pydantic types:

```python
from animus_plugin_sdk.subject import SubjectBackend, ensure_wire_subject
from animus_plugin_sdk.subject import gen as subject_types     # generated wire types
from animus_plugin_sdk.provider import Provider, AgentRunRequest, AgentStream
from animus_plugin_sdk.trigger import TriggerBackend, TriggerEvent
from animus_plugin_sdk.transport import TransportBackend, TransportConfig
from animus_plugin_sdk.log_storage import LogStorageBackend, LogEntry
from animus_plugin_sdk.queue import Queue, QueueEnqueueRequest
from animus_plugin_sdk.workflow_runner import WorkflowRunner
from animus_plugin_sdk.durable_store import DurableStore
from animus_plugin_sdk.memory_store import MemoryStore
from animus_plugin_sdk.notifier import Notifier
```

| Layer                              | What it holds                                                   |
| ---------------------------------- | --------------------------------------------------------------- |
| `animus_plugin_sdk`                | `define_plugin`, base/runtime, all role contracts (back-compat) |
| `animus_plugin_sdk.<role>`         | role contract (Protocol/ABC) + generated pydantic types (`gen`) |
| `animus_plugin_sdk.types`          | base layer: `PROTOCOL_VERSION`, `PluginKind`, `ErrorCode`, envelopes |
| `animus_plugin_sdk.types.generated`| one pydantic module per protocol crate (codegen output)         |

## Roles (full coverage)

Every role from the protocol spec §7 is wired. The dispatcher validates inbound
params against the generated pydantic models (returning `-32602` `invalid_params`
on failure) and advertises only the methods it can serve.

| Role                  | Methods wired                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------------- |
| `subject_backend`     | `subject/list`, `subject/get`, `subject/schema`; optional `create`/`update`/`status`/`next`/`delete`; legacy `<kind>/*` routes |
| `provider`            | `agent/run`, `agent/resume`, `agent/cancel` + streaming `agent/output\|thinking\|toolCall\|toolResult\|error` |
| `trigger_backend`     | `trigger/watch` (streams flat `trigger/event`), `trigger/schema`, optional `trigger/ack`                  |
| `transport_backend`   | `transport/start`, `transport/shutdown`, `transport/schema`                                               |
| `log_storage_backend` | `log_storage/store`, optional `log_storage/query`, streaming `log_storage/tail`, `log_storage/schema`     |
| `queue`               | `queue/enqueue\|list\|lease\|stats\|hold\|release\|drop\|mark_assigned\|completion\|reorder`, optional `release_pending` |
| `workflow_runner`     | `workflow/execute`, `workflow/run_phase`                                                                  |
| `durable_store`       | `durable/begin_workflow_run\|begin_step\|commit_step\|abandon_step\|recover_in_flight\|query_run`         |
| `memory_store`        | `memory/put\|get\|query\|list_scopes\|delete_scope`                                                       |
| `notifier`            | `notifier/notify`, optional `notifier/flush`, `notifier/schema`                                           |

Optional methods that an impl does not provide return `-32001`
(`method_not_supported`); unrecognized methods return `-32601`
(`method_not_found`). This matches the TypeScript SDK's role surface exactly.

### Streaming concurrency

The stdio wire read loop is synchronous and serial. Streaming roles
(`trigger/watch`, `log_storage/tail`) acknowledge immediately and then drain the
author's iterator on a **background daemon thread**, emitting notifications via
the wire. Every stdout frame is written + flushed under a lock, so a background
notification never interleaves bytes with the main loop's response — the
synchronous subject path and per-frame framing are untouched. Provider streaming
runs inline on the dispatch thread: the impl emits via `ctx.stream` before
returning the final `AgentRunResponse`.

## Generated wire types (Rust is the source of truth)

The wire payload types under `animus_plugin_sdk.types.generated/<crate>.py` are
**generated** by `scripts/codegen.py` from the vendored JSON Schema bundles in
`schemas/<crate>/_all.json` (copied from `animus-protocol`). They are pydantic v2
models with `extra="allow"` so unknown fields round-trip (the Python equivalent
of Rust's `Other(String)` fall-through). Open-string enums (`TriggerActionHint`,
`TriggerAckStatus`) stay `str`; JSON-RPC envelope fields
(`id`/`params`/`result`/`payload`/`data`) stay `Any`.

Regenerate after updating the vendored schemas:

```sh
python scripts/codegen.py        # regenerate the models
python scripts/codegen_check.py  # CI drift check (fails on uncommitted diff)
```

A field whose name shadows a pydantic `BaseModel` attribute (e.g. `schema`) is
emitted as `<name>_` with a pydantic `alias`, so the wire name round-trips.

## Protocol version

This SDK targets `PROTOCOL_VERSION = "1.1.0"`. The handshake validates the host's
advertised version with strict major-version match: a `1.x` plugin accepts any
`1.x` host but rejects `0.x` or `2.x`. The v1.1.0 changes are additive — the four
new plugin kinds (`workflow_runner`, `queue`, `durable_store`, `memory_store`,
plus `notifier`), the tolerated `init_extensions` on `initialize`, and the
`kind_capabilities` map emitted only for the new kinds (v1.0.0 kinds keep the
wire shape byte-identical). v1.0.0 hosts continue to work.

## Parity with the TypeScript SDK

| Concept             | TS                     | Python                          |
| ------------------- | ---------------------- | ------------------------------- |
| Entrypoint          | `definePlugin(spec)`   | `define_plugin(kind, impl, …)`  |
| Stdio loop          | `createWire()`         | `create_wire()`                 |
| Handshake helpers   | `buildManifest`        | `build_manifest`                |
| Role contracts      | `interface`            | `typing.Protocol`               |
| Wire payload models | generated Zod schemas  | generated pydantic models       |
| Param validation    | `schema.safeParse`     | `model.model_validate`          |
| Subpath exports     | `/subject`, `/provider`| `animus_plugin_sdk.subject`, …  |
| Streaming           | async iterators        | sync iterators + daemon thread  |

## Development

```sh
git clone https://github.com/launchapp-dev/animus-plugin-sdk-py.git
cd animus-plugin-sdk-py
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/codegen_check.py
ruff check
ruff format --check
mypy animus_plugin_sdk
pytest -v
```

## License

Elastic-2.0
