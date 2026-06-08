"""Subpath module: ``animus_plugin_sdk.subject`` — subject_backend role contract,
generated pydantic types, and the ``ensure_wire_subject`` helper."""

from __future__ import annotations

from .dispatch.subject import ensure_wire_subject
from .roles.subject import *  # noqa: F403
from .roles.subject import __all__ as _roles_all
from .types.generated import subject as gen

__all__ = [*_roles_all, "ensure_wire_subject", "gen"]
