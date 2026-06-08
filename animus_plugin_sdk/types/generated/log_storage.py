# AUTO-GENERATED FROM schemas/animus-log-storage-protocol/_all.json — DO NOT EDIT BY HAND.
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


LogLevel = Literal["trace", "debug", "info", "warn", "error"]


LogSource = Literal["daemon", "plugin", "cli", "workflow"]


class LogEntry(GeneratedModel):
    "One structured log record persisted by a log storage backend."
    fields_: Any = Field(default=None, alias="fields")
    id: str
    level: "LogLevel"
    message: str
    source: "LogSource"
    source_name: Optional[str] = Field(default=None)
    target: str
    ts: str


class LogQuery(GeneratedModel):
    "Filter applied to [`LogStorageBackend::query`] and"
    cursor: Optional[str] = Field(default=None)
    follow: Optional[bool] = Field(default=None)
    limit: Optional[int] = Field(default=None, ge=0)
    min_level: Optional["LogLevel"] = Field(default=None)
    since: Optional[str] = Field(default=None)
    source: Optional["LogSource"] = Field(default=None)
    source_name: Optional[str] = Field(default=None)
    target_glob: Optional[str] = Field(default=None)
    until: Optional[str] = Field(default=None)


class LogQueryResult(GeneratedModel):
    "One page of [`LogEntry`] records returned by"
    entries: list["LogEntry"]
    next_cursor: Optional[str] = Field(default=None)


class SupportsFiltering(GeneratedModel):
    "Server-side filter support advertised by [`LogStorageSchema`]."
    by_glob: Optional[bool] = Field(default=None)
    by_level: Optional[bool] = Field(default=None)
    by_source: Optional[bool] = Field(default=None)
    by_target: Optional[bool] = Field(default=None)
    by_time_range: Optional[bool] = Field(default=None)


class LogStorageSchema(GeneratedModel):
    "Capability declaration returned by [`METHOD_LOG_STORAGE_SCHEMA`]."
    max_query_window: Optional[int] = Field(default=None)
    retention_hint: Optional[int] = Field(default=None)
    supports_dedup: bool
    supports_filtering: "SupportsFiltering"
    supports_query: bool
    supports_tail: bool


LogEntry.model_rebuild()
LogQuery.model_rebuild()
LogQueryResult.model_rebuild()
SupportsFiltering.model_rebuild()
LogStorageSchema.model_rebuild()
