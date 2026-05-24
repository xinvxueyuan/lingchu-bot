"""
测试群精华消息命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.essence import (
    milkybot_set_group_essence_message,
)
from tests.command.group.conftest import finish_text

SET_GROUP_ESSENCE_MESSAGE_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.essence."
    "set_group_essence_message_cmd.finish"
)


@pytest.mark.asyncio
async def test_set_group_essence_message_calls_milky_api(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_essence_message = AsyncMock()

    with patch(SET_GROUP_ESSENCE_MESSAGE_FINISH) as mock_finish:
        await milkybot_set_group_essence_message(
            message_seq=100, is_set=True, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_essence_message.assert_called_once_with(
        group_id=mock_event.data.peer_id, message_seq=100, is_set=True
    )
    assert finish_text(mock_finish) == "设置群精华消息: 100"


@pytest.mark.asyncio
async def test_set_group_essence_message_is_set_false_uses_unset_text(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_essence_message = AsyncMock()

    with patch(SET_GROUP_ESSENCE_MESSAGE_FINISH) as mock_finish:
        await milkybot_set_group_essence_message(
            message_seq=200, is_set=False, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_essence_message.assert_called_once_with(
        group_id=mock_event.data.peer_id, message_seq=200, is_set=False
    )
    assert finish_text(mock_finish) == "取消群精华消息: 200"


@pytest.mark.asyncio
async def test_unset_group_essence_message_delegates_with_is_set_false(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.essence import (
        milkybot_unset_group_essence_message,
    )

    mock_bot.set_group_essence_message = AsyncMock()

    with patch(SET_GROUP_ESSENCE_MESSAGE_FINISH) as mock_finish:
        await milkybot_unset_group_essence_message(
            message_seq=300, bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_essence_message.assert_called_once_with(
        group_id=mock_event.data.peer_id, message_seq=300, is_set=False
    )
    assert finish_text(mock_finish) == "取消群精华消息: 300"


@pytest.mark.asyncio
async def test_set_group_essence_message_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import NetworkError

    mock_bot.set_group_essence_message = AsyncMock(side_effect=NetworkError("timeout"))

    with patch(SET_GROUP_ESSENCE_MESSAGE_FINISH) as mock_finish:
        await milkybot_set_group_essence_message(
            message_seq=100, is_set=True, bot=mock_bot, event=mock_event
        )

    assert "设置群精华消息失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_essence_message_action_failed_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import ActionFailed

    mock_bot.set_group_essence_message = AsyncMock(
        side_effect=ActionFailed(message="无权限")
    )

    with patch(SET_GROUP_ESSENCE_MESSAGE_FINISH) as mock_finish:
        await milkybot_set_group_essence_message(
            message_seq=100, is_set=True, bot=mock_bot, event=mock_event
        )

    assert "设置群精华消息失败，操作被拒绝" in finish_text(mock_finish)
