"""Subpath module: ``animus_plugin_sdk.notifier`` — role contract + generated pydantic types."""

from __future__ import annotations

from .roles.notifier import *  # noqa: F403
from .roles.notifier import __all__ as _roles_all
from .types.generated import notifier as gen

__all__ = [*_roles_all, "gen"]
