"""Hook handler registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .interfaces import HookContext, HookHandler, HookType

if TYPE_CHECKING:
    from collections.abc import Iterator

_handlers: dict[HookType, list[tuple[HookHandler[Any], bool]]] = {
    hook_type: [] for hook_type in HookType
}


def register_handler[T: HookContext](
    hook_type: HookType,
    handler: HookHandler[T],
    *,
    enabled: bool = True,
) -> HookHandler[T]:
    """Register a hook handler for a capability category.

    Handlers may be registered as disabled; ``iter_handlers`` and
    ``get_handlers_by_type`` only yield enabled entries.
    """
    _handlers[hook_type].append((handler, enabled))
    return handler


def iter_handlers(hook_type: HookType | None = None) -> Iterator[HookHandler[Any]]:
    """Yield enabled handlers, optionally filtered by hook type."""
    entries: list[tuple[HookHandler[Any], bool]]
    if hook_type is None:
        entries = [entry for handlers in _handlers.values() for entry in handlers]
    else:
        entries = _handlers.get(hook_type, [])
    for handler, enabled in entries:
        if enabled:
            yield handler


def get_handlers_by_type(hook_type: HookType) -> tuple[HookHandler[Any], ...]:
    """Return enabled handlers for a specific hook type."""
    return tuple(
        handler for handler, enabled in _handlers.get(hook_type, []) if enabled
    )


__all__ = [
    "get_handlers_by_type",
    "iter_handlers",
    "register_handler",
]
