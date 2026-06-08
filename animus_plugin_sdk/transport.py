"""Subpath module: ``animus_plugin_sdk.transport`` — role contract + generated pydantic types."""

from __future__ import annotations

from .roles.transport import *  # noqa: F403
from .roles.transport import __all__ as _roles_all
from .types.generated import transport as gen

__all__ = [*_roles_all, "gen"]
