"""
测试群成员设置与踢出命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.member import (
    milkybot_kick_group_member,
    milkybot_set_group_member_admin,
    milkybot_set_group_member_card,
)
from tests.command.group.conftest import finish_text

SET_GROUP_MEMBER_ADMIN_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.member."
    "set_group_member_admin_cmd.finish"
)
SET_GROUP_MEMBER_CARD_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.member."
    "set_group_member_card_cmd.finish"
)
KICK_GROUP_MEMBER_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.member."
    "kick_group_member_cmd.finish"
)


@pytest.mark.asyncio
async def test_set_group_member_admin_ignores_unmatched_mention_segment(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_admin = AsyncMock()
    mock_event.data.segments = [
        {"type": "mention", "data": {"user_id": 222222, "name": "第一用户"}}
    ]

    with patch(SET_GROUP_MEMBER_ADMIN_FINISH) as mock_finish:
        await milkybot_set_group_member_admin(
            user=mock_at, is_set=True, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_admin.assert_called_once_with(
        group_id=mock_event.data.peer_id, user_id=987654321, is_set=True
    )
    assert "设置群管理员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_member_admin_matches_requested_mention(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_admin = AsyncMock()
    mock_event.data.segments = [
        {"type": "mention", "data": {"user_id": 111111, "name": "错误用户"}},
        {"type": "mention", "data": {"user_id": 987654321, "name": "目标用户"}},
    ]

    with patch(SET_GROUP_MEMBER_ADMIN_FINISH) as mock_finish:
        await milkybot_set_group_member_admin(
            user=mock_at, is_set=True, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_admin.assert_called_once_with(
        group_id=mock_event.data.peer_id, user_id=987654321, is_set=True
    )
    assert "设置群管理员: 目标用户(987654321)" in finish_text(mock_finish)
    assert "错误用户" not in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_member_admin_invalid_target_raises_value_error(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_admin = AsyncMock()
    mock_at.target = "not-a-number"

    with patch(SET_GROUP_MEMBER_ADMIN_FINISH) as mock_finish, pytest.raises(ValueError):
        await milkybot_set_group_member_admin(
            user=mock_at, is_set=True, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_admin.assert_not_called()
    mock_finish.assert_not_called()


@pytest.mark.asyncio
async def test_set_group_member_card_uses_at_target(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_card = AsyncMock()

    with patch(SET_GROUP_MEMBER_CARD_FINISH) as mock_finish:
        await milkybot_set_group_member_card(
            user=mock_at, card="新名片", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_card.assert_called_once_with(
        group_id=mock_event.data.peer_id, user_id=987654321, card="新名片"
    )
    assert "已设置群名片: 测试用户(987654321) -> 新名片" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_kick_group_member_passes_reject_flag(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.kick_group_member = AsyncMock()

    with patch(KICK_GROUP_MEMBER_FINISH) as mock_finish:
        await milkybot_kick_group_member(
            user=mock_at,
            reject_add_request=True,
            bot=mock_bot,
            event=mock_event,
        )

    mock_bot.kick_group_member.assert_called_once_with(
        group_id=mock_event.data.peer_id,
        user_id=987654321,
        reject_add_request=True,
    )
    assert "已踢出群成员: 测试用户(987654321)" in finish_text(mock_finish)
