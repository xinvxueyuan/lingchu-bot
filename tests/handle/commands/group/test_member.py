"""
测试群成员设置与踢出命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from src.plugins.nonebot_plugin_lingchu_bot.handle.commands.group.member import (
    kick_group_member_cmd,
    milkybot_kick_group_member,
    milkybot_set_group_member_admin,
    milkybot_set_group_member_card,
    milkybot_set_group_member_special_title,
    milkybot_unset_group_member_admin,
    onebot11_kick_group_member,
    onebot11_set_group_member_admin,
    onebot11_set_group_member_card,
    onebot11_set_group_member_special_title,
    onebot11_unset_group_member_admin,
    set_group_member_admin_cmd,
    set_group_member_card_cmd,
    set_group_member_special_title_cmd,
)
from tests.handle.commands.group.conftest import finish_text


@pytest.mark.asyncio
async def test_set_group_member_admin_ignores_unmatched_mention_segment(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_admin = AsyncMock()
    mock_event.data.segments = [
        {"type": "mention", "data": {"user_id": 222222, "name": "第一用户"}}
    ]

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
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

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
        await milkybot_set_group_member_admin(
            user=mock_at, is_set=True, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_admin.assert_called_once_with(
        group_id=mock_event.data.peer_id, user_id=987654321, is_set=True
    )
    assert "设置群管理员: 测试用户(987654321)" in finish_text(mock_finish)
    assert "错误用户" not in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_member_admin_invalid_target_raises_value_error(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_admin = AsyncMock()
    mock_at.target = "not-a-number"

    with (
        patch.object(set_group_member_admin_cmd, "finish") as mock_finish,
        pytest.raises(ValueError),
    ):
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

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
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

    with patch.object(kick_group_member_cmd, "finish") as mock_finish:
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


@pytest.mark.asyncio
async def test_set_group_member_special_title_calls_milky_api(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_special_title = AsyncMock()

    with patch.object(set_group_member_special_title_cmd, "finish") as mock_finish:
        await milkybot_set_group_member_special_title(
            user=mock_at, special_title="精英", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_special_title.assert_called_once_with(
        group_id=mock_event.data.peer_id, user_id=987654321, special_title="精英"
    )
    assert "已设置群头衔: 测试用户(987654321) -> 精英" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_unset_group_member_admin_delegates_with_is_set_false(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_admin = AsyncMock()

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
        await milkybot_unset_group_member_admin(
            user=mock_at, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_member_admin.assert_called_once_with(
        group_id=mock_event.data.peer_id, user_id=987654321, is_set=False
    )
    assert "取消群管理员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_kick_group_member_default_reject_false(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.kick_group_member = AsyncMock()

    with patch.object(kick_group_member_cmd, "finish") as mock_finish:
        await milkybot_kick_group_member(
            user=mock_at,
            reject_add_request=False,
            bot=mock_bot,
            event=mock_event,
        )

    mock_bot.kick_group_member.assert_called_once_with(
        group_id=mock_event.data.peer_id,
        user_id=987654321,
        reject_add_request=False,
    )
    assert "已踢出群成员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_member_card_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_card = AsyncMock(side_effect=NetworkError("timeout"))

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await milkybot_set_group_member_card(
            user=mock_at, card="新名片", bot=mock_bot, event=mock_event
        )

    assert "设置群名片失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_member_card_action_failed_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_bot.set_group_member_card = AsyncMock(
        side_effect=ActionFailed(message="权限不足")
    )

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await milkybot_set_group_member_card(
            user=mock_at, card="新名片", bot=mock_bot, event=mock_event
        )

    assert "设置群名片失败，操作被拒绝" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_target_user_falls_back_to_at_display_when_no_segments(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    """When there are no matching mention segments, target_user returns At.display."""
    mock_bot.set_group_member_card = AsyncMock()
    mock_event.data.segments = []

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await milkybot_set_group_member_card(
            user=mock_at, card="名片", bot=mock_bot, event=mock_event
        )

    assert "测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_target_user_falls_back_to_at_display_when_mention_name_empty(
    mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
) -> None:
    """
    验证当匹配的 mention 的 name 为空时，目标用户展示使用 At.display 回退。

    该测试调用设置群名片的处理函数并断言 finish 输出包含 At 的显示信息
    （例如 "测试用户(987654321)"）。
    """
    mock_bot.set_group_member_card = AsyncMock()
    mock_event.data.segments = [
        {"type": "mention", "data": {"user_id": 987654321, "name": ""}}
    ]

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await milkybot_set_group_member_card(
            user=mock_at, card="名片", bot=mock_bot, event=mock_event
        )

    assert "测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_member_card_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_card = AsyncMock()

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_card(
            user=mock_at,
            card="新名片",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_card.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, card="新名片"
    )
    assert "已设置群名片: 测试用户(987654321) -> 新名片" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_member_special_title_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_special_title = AsyncMock()

    with patch.object(set_group_member_special_title_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_special_title(
            user=mock_at,
            special_title="精英",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_special_title.assert_called_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        special_title="精英",
        duration=-1,
    )
    assert "已设置群头衔: 测试用户(987654321) -> 精英" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_member_admin_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_admin = AsyncMock()

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_admin(
            user=mock_at,
            is_set=True,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_admin.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, enable=True
    )
    assert "设置群管理员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_unset_group_member_admin_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_admin = AsyncMock()

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
        await onebot11_unset_group_member_admin(
            user=mock_at, bot=mock_onebot11_bot, event=mock_onebot11_event
        )

    mock_onebot11_bot.set_group_admin.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, enable=False
    )
    assert "取消群管理员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_group_member_passes_reject_flag(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()

    with patch.object(kick_group_member_cmd, "finish") as mock_finish:
        await onebot11_kick_group_member(
            user=mock_at,
            reject_add_request=True,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_kick.assert_called_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=True,
    )
    assert "已踢出群成员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_target_user_reads_matching_at_segment(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_card = AsyncMock()
    mock_at.display = ""
    wrong_segment = MagicMock(type="at", data={"qq": "111111", "name": "错误用户"})
    target_segment = MagicMock(type="at", data={"qq": "987654321", "name": "目标用户"})
    mock_onebot11_event.message = [wrong_segment, target_segment]

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_card(
            user=mock_at,
            card="新名片",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_card.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, card="新名片"
    )
    assert "目标用户(987654321)" in finish_text(mock_finish)
    assert "错误用户" not in finish_text(mock_finish)
