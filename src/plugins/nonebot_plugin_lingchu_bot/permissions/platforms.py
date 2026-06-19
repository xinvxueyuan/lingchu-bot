"""Permission integration points exported by platform modules."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .types import PermissionContext, PlatformIdentityGroupSeed

type RuntimeGroupResolver = Callable[
    [Any, Any, PermissionContext],
    Awaitable[frozenset[str]],
]

_PLATFORM_PERMISSION_MODULES = ("..platforms.qq.permissions",)


def iter_default_identity_groups() -> tuple[PlatformIdentityGroupSeed, ...]:
    seeds: list[PlatformIdentityGroupSeed] = []
    for module in _iter_permission_modules():
        seeds.extend(module.get_default_identity_groups())
    return tuple(seeds)


async def resolve_runtime_identity_groups(
    bot: Any,
    event: Any,
    context: PermissionContext,
) -> frozenset[str]:
    for module in _iter_permission_modules():
        if getattr(module, "QQ_PLATFORM_ID", None) != context.platform_id:
            continue
        resolver = getattr(module, "resolve_runtime_identity_groups", None)
        if resolver is None:
            return frozenset()
        return await resolver(bot, event, context)
    return frozenset()


def _iter_permission_modules() -> tuple[Any, ...]:
    from importlib import import_module

    return tuple(
        import_module(module_name, package=__package__)
        for module_name in _PLATFORM_PERMISSION_MODULES
    )
