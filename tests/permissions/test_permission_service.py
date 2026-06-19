from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.service import (
    allowed_command_keys,
    check_permission,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo


@pytest.fixture
def bot() -> MagicMock:
    bot = MagicMock()
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = "OneBot V11"
    return bot


def event(user_id: int = 42) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        group_id=10001,
        sender=SimpleNamespace(role="member"),
    )


@pytest.mark.asyncio
async def test_superuser_permission_allows_command(
    monkeypatch: pytest.MonkeyPatch,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))

    decision = await check_permission("member_mute", bot, event())

    assert decision.allowed is True
    assert decision.reason == "superuser"
    assert decision.uid == "userA"


@pytest.mark.asyncio
async def test_anonymous_permission_denies_command(
    monkeypatch: pytest.MonkeyPatch,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo, "get_user_by_platform_account", AsyncMock(return_value=None)
    )

    decision = await check_permission("member_mute", bot, event())

    assert decision.allowed is False
    assert decision.reason == "anonymous"


@pytest.mark.asyncio
async def test_group_grant_permission_allows_child_runtime_group(
    monkeypatch: pytest.MonkeyPatch,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(group_id="qq.group", parent_group_id=None),
                SimpleNamespace(group_id="qq.group.member", parent_group_id="qq.group"),
            ]
        ),
    )
    monkeypatch.setattr(
        repo,
        "list_grants",
        AsyncMock(return_value=[SimpleNamespace(group_id="qq.group", effect="allow")]),
    )

    decision = await check_permission("member_mute", bot, event())

    assert decision.allowed is True
    assert decision.reason == "granted"
    assert decision.matched_groups == frozenset({"qq.group"})


@pytest.mark.asyncio
async def test_allowed_command_keys_returns_all_for_superuser(
    monkeypatch: pytest.MonkeyPatch,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))

    keys = await allowed_command_keys(
        bot, event(), frozenset({"member_mute", "kick_member"})
    )

    assert keys == frozenset({"member_mute", "kick_member"})
