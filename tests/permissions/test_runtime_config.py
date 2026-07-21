from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.service import (
    check_permission,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo


@pytest.fixture
def mock_session() -> Mock:
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.fixture
def bot() -> SimpleNamespace:
    return SimpleNamespace(
        adapter=SimpleNamespace(get_name=lambda: "OneBot V11"),
        call_api=AsyncMock(return_value={"role": "admin"}),
    )


def event() -> SimpleNamespace:
    return SimpleNamespace(
        user_id=42,
        group_id=10001,
        sender=SimpleNamespace(role="admin"),
    )


@pytest.mark.asyncio
async def test_platform_runtime_groups_can_be_disabled_by_config(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: SimpleNamespace,
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
                SimpleNamespace(group_id="qq.group.admin", parent_group_id="qq.group"),
            ]
        ),
    )
    monkeypatch.setattr(
        repo,
        "list_grants",
        AsyncMock(
            return_value=[SimpleNamespace(group_id="qq.group.admin", effect="allow")]
        ),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.permissions.service.platform_runtime_passthrough_enabled",
        lambda _context: False,
    )

    decision = await check_permission(mock_session, "member_mute", bot, event())

    assert decision.allowed is False
    assert decision.reason == "missing_grant"
