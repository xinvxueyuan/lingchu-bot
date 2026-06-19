from types import SimpleNamespace
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
