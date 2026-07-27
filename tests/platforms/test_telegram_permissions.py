from types import SimpleNamespace
from unittest.mock import AsyncMock

from nonebot.adapters.telegram.exception import NetworkError
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import PermissionContext
from src.plugins.nonebot_plugin_lingchu_bot.platforms.telegram.permissions import (
    get_default_identity_groups,
    resolve_runtime_identity_groups,
)


def test_telegram_identity_groups_include_chat_roles() -> None:
    groups = {seed.group_id for seed in get_default_identity_groups()}

    assert {
        "telegram.group",
        "telegram.group.owner",
        "telegram.group.admin",
        "telegram.group.member",
    } <= groups


@pytest.mark.asyncio
async def test_telegram_creator_gets_owner_group() -> None:
    event = SimpleNamespace(sender=SimpleNamespace(status="creator"))
    context = PermissionContext("telegram", "~telegram", "1", "group", "-1")

    assert await resolve_runtime_identity_groups(None, event, context) == frozenset({
        "telegram.group",
        "telegram.group.owner",
    })


@pytest.mark.asyncio
async def test_telegram_role_falls_back_to_chat_member_api() -> None:
    bot = SimpleNamespace(
        get_chat_member=AsyncMock(return_value=SimpleNamespace(status="administrator"))
    )
    event = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        from_=SimpleNamespace(id=42),
    )
    context = PermissionContext("telegram", "~telegram", "42", "group", "-1001")

    groups = await resolve_runtime_identity_groups(bot, event, context)

    assert groups == frozenset({"telegram.group", "telegram.group.admin"})
    bot.get_chat_member.assert_awaited_once_with(chat_id=-1001, user_id=42)


@pytest.mark.asyncio
async def test_telegram_unknown_sender_fails_closed() -> None:
    context = PermissionContext("telegram", "~telegram", None, "group", "-1001")

    assert (
        await resolve_runtime_identity_groups(None, SimpleNamespace(), context)
        == frozenset()
    )


@pytest.mark.asyncio
async def test_telegram_member_lookup_failure_fails_closed() -> None:
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=NetworkError()))
    event = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        from_=SimpleNamespace(id=42),
    )
    context = PermissionContext("telegram", "~telegram", "42", "group", "-1001")

    assert await resolve_runtime_identity_groups(bot, event, context) == frozenset()
