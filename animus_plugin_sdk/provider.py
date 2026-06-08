"""Subpath module: ``animus_plugin_sdk.provider`` — role contract + generated pydantic types."""

from __future__ import annotations

from .roles.provider import *  # noqa: F403
from .roles.provider import __all__ as _roles_all
from .types.generated import provider as gen

__all__ = [*_roles_all, "gen"]
