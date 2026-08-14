from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.platforms import (
    iter_default_identity_groups,
    resolve_runtime_identity_groups,
)
from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import PermissionContext


def test_qq_default_identity_groups_are_platform_defined() -> None:
    groups = {seed.group_id: seed for seed in iter_default_identity_groups()}

    assert groups["qq.group"].platform_id == "qq"
    assert groups["qq.group.owner"].parent_group_id == "qq.group"
    assert groups["qq.group.admin"].parent_group_id == "qq.group"
    assert groups["qq.group.member"].parent_group_id == "qq.group"


def test_iter_default_identity_groups_discovers_qq_dynamically() -> None:
    """动态模块发现仍能正确返回 QQ 身份组。"""
    groups = {seed.group_id: seed for seed in iter_default_identity_groups()}

    assert "qq.group" in groups
    assert "qq.group.owner" in groups
    assert "qq.group.admin" in groups
    assert "qq.group.member" in groups
    assert "qq.friend" in groups


def test_iter_default_identity_groups_only_imports_enabled_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """禁用平台的权限模块不应被导入，也不应种子其身份组。"""
    import importlib

    from src.plugins.nonebot_plugin_lingchu_bot.permissions import platforms as module
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import registry

    monkeypatch.setattr(
        registry, "resolve_enabled_adapters", lambda _configured: {"~telegram"}
    )
    real_import = importlib.import_module

    def guarded_import(name: str, package: str | None = None) -> Any:
        if name == "..platforms.qq.permissions":
            raise AssertionError("qq permission module imported while disabled")
        return real_import(name, package=package)

    monkeypatch.setattr(importlib, "import_module", guarded_import)

    groups = {seed.group_id for seed in module.iter_default_identity_groups()}

    assert "telegram.group" in groups
    assert "qq.group" not in groups


@pytest.mark.asyncio
async def test_resolve_runtime_identity_groups_qq_calls_qq_resolver() -> None:
    """context.platform_id=qq 时调用 QQ 平台的 resolver。"""
    bot = MagicMock()
    bot.call_api = AsyncMock()
    event = SimpleNamespace(sender=SimpleNamespace(role="admin"))
    context = PermissionContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        account_id="42",
        scope_type="group",
        scope_id="10001",
    )

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.admin"})


@pytest.mark.asyncio
async def test_resolve_runtime_identity_groups_unknown_platform_returns_empty() -> None:
    """context.platform_id=unknown 时返回空 frozenset。"""
    bot = MagicMock()
    bot.call_api = AsyncMock()
    event = SimpleNamespace(sender=SimpleNamespace(role="admin"))
    context = PermissionContext(
        platform_id="unknown",
        adapter_id=None,
        account_id="42",
        scope_type="group",
        scope_id="10001",
    )

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset()
    bot.call_api.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_runtime_identity_groups_skips_disabled_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未启用平台的 resolver 不被导入，返回空 frozenset 且不调用 API。"""
    import importlib

    from src.plugins.nonebot_plugin_lingchu_bot.permissions import platforms as module
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import registry

    monkeypatch.setattr(
        registry, "resolve_enabled_adapters", lambda _configured: {"~telegram"}
    )
    real_import = importlib.import_module

    def guarded_import(name: str, package: str | None = None) -> Any:
        if name == "..platforms.qq.permissions":
            raise AssertionError("qq permission module imported while disabled")
        return real_import(name, package=package)

    monkeypatch.setattr(importlib, "import_module", guarded_import)

    bot = MagicMock()
    bot.call_api = AsyncMock()
    event = SimpleNamespace(sender=SimpleNamespace(role="admin"))
    context = PermissionContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        account_id="42",
        scope_type="group",
        scope_id="10001",
    )

    result = await module.resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset()
    bot.call_api.assert_not_called()
