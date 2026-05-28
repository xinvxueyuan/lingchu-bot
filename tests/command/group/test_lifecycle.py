"""
测试群生命周期命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.lifecycle import (
    milkybot_quit_group,
)

QUIT_GROUP_SEND = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.lifecycle."
    "quit_group_cmd.send"
)


@pytest.mark.asyncio
async def test_quit_group_sends_message_and_calls_api(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.quit_group = AsyncMock()

    with patch(QUIT_GROUP_SEND) as mock_send:
        await milkybot_quit_group(bot=mock_bot, event=mock_event)

    mock_send.assert_called_once_with(
        group_id=mock_event.data.peer_id, message="退出当前群"
    )
    mock_bot.quit_group.assert_called_once_with(group_id=mock_event.data.peer_id)


@pytest.mark.asyncio
async def test_quit_group_propagates_network_error(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import NetworkError

    mock_bot.quit_group = AsyncMock(side_effect=NetworkError("connection refused"))

    with patch(QUIT_GROUP_SEND), pytest.raises(NetworkError):
        await milkybot_quit_group(bot=mock_bot, event=mock_event)


@pytest.mark.asyncio
async def test_quit_group_propagates_action_failed_error(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import ActionFailed

    mock_bot.quit_group = AsyncMock(side_effect=ActionFailed(message="操作失败"))

    with patch(QUIT_GROUP_SEND), pytest.raises(ActionFailed):
        await milkybot_quit_group(bot=mock_bot, event=mock_event)
