"""测试 platforms/qq/permissions.py 的运行时身份组解析与 API 回退。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.onebot.v11.exception import NetworkError
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import PermissionContext
from src.plugins.nonebot_plugin_lingchu_bot.platforms.qq.permissions import (
    PLATFORM_ID,
    resolve_runtime_identity_groups,
)


def _make_context(
    *,
    scope_type: str = "group",
    scope_id: str | None = "10001",
    account_id: str | None = "42",
) -> PermissionContext:
    return PermissionContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        account_id=account_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


def _make_event(role: str | None = "member") -> SimpleNamespace:
    return SimpleNamespace(sender=SimpleNamespace(role=role))


@pytest.mark.asyncio
async def test_admin_role_returns_admin_groups_without_api_call() -> None:
    """event.sender.role 为 admin 时直接返回 admin 身份组，不调用 API。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock()
    event = _make_event(role="admin")
    context = _make_context()

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.admin"})
    bot.get_group_member_info.assert_not_called()


@pytest.mark.asyncio
async def test_owner_role_returns_owner_groups_without_api_call() -> None:
    """event.sender.role 为 owner 时直接返回 owner 身份组，不调用 API。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock()
    event = _make_event(role="owner")
    context = _make_context()

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.owner"})
    bot.get_group_member_info.assert_not_called()


@pytest.mark.asyncio
async def test_missing_role_calls_api_and_returns_role() -> None:
    """event.sender.role 缺失时调用 get_group_member_info API 获取角色。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock(return_value={"role": "admin"})
    event = _make_event(role=None)
    context = _make_context()

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.admin"})
    bot.get_group_member_info.assert_awaited_once_with(
        group_id=10001,
        user_id=42,
    )


@pytest.mark.asyncio
async def test_api_returns_owner_role_returns_owner_groups() -> None:
    """API 返回 role=owner 时返回 owner 身份组。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock(return_value={"role": "owner"})
    event = _make_event(role=None)
    context = _make_context()

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.owner"})


@pytest.mark.asyncio
async def test_api_failure_falls_back_to_member_groups() -> None:
    """API 调用失败时降级为 member 身份组。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock(side_effect=NetworkError("API error"))
    event = _make_event(role=None)
    context = _make_context()

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.member"})


@pytest.mark.asyncio
async def test_global_scope_returns_empty_without_api_call() -> None:
    """scope_type=global 时返回空 frozenset，不调用 API。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock()
    event = _make_event(role=None)
    context = _make_context(scope_type="global")

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset()
    bot.get_group_member_info.assert_not_called()


@pytest.mark.asyncio
async def test_member_role_returns_member_groups_without_api_call() -> None:
    """event.sender.role 为 member 时直接返回 member 身份组，不调用 API。"""
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock()
    event = _make_event(role="member")
    context = _make_context()

    result = await resolve_runtime_identity_groups(bot, event, context)

    assert result == frozenset({"qq.group", "qq.group.member"})
    bot.get_group_member_info.assert_not_called()


def test_platform_id_constant() -> None:
    """PLATFORM_ID 为 qq。"""
    assert PLATFORM_ID == "qq"


@pytest.mark.asyncio
async def test_missing_account_falls_back_without_api_call() -> None:
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock()

    result = await resolve_runtime_identity_groups(
        bot, _make_event(role=None), _make_context(account_id=None)
    )

    assert result == frozenset({"qq.group", "qq.group.member"})
    bot.get_group_member_info.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_api_role_falls_back_to_member() -> None:
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock(return_value={"role": "guest"})

    result = await resolve_runtime_identity_groups(
        bot, _make_event(role=None), _make_context()
    )

    assert result == frozenset({"qq.group", "qq.group.member"})


@pytest.mark.asyncio
async def test_legacy_data_sender_role_is_still_understood() -> None:
    bot = MagicMock()
    bot.get_group_member_info = AsyncMock()
    event = SimpleNamespace(
        sender=None,
        data=SimpleNamespace(sender=SimpleNamespace(role="owner")),
    )

    result = await resolve_runtime_identity_groups(bot, event, _make_context())

    assert result == frozenset({"qq.group", "qq.group.owner"})
    bot.get_group_member_info.assert_not_awaited()
