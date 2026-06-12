"""
测试群生命周期命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group.lifecycle import (
    milkybot_quit_group,
    onebot11_quit_group,
    quit_group_cmd,
)
from tests.handle.commands.group.conftest import finish_text


@pytest.mark.asyncio
async def test_quit_group_sends_message_and_calls_api(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.quit_group = AsyncMock()

    with patch.object(quit_group_cmd, "send") as mock_send:
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

    with patch.object(quit_group_cmd, "send"), pytest.raises(NetworkError):
        await milkybot_quit_group(bot=mock_bot, event=mock_event)


@pytest.mark.asyncio
async def test_quit_group_propagates_action_failed_error(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import ActionFailed

    mock_bot.quit_group = AsyncMock(side_effect=ActionFailed(message="操作失败"))

    with patch.object(quit_group_cmd, "send"), pytest.raises(ActionFailed):
        await milkybot_quit_group(bot=mock_bot, event=mock_event)


@pytest.mark.asyncio
async def test_onebot11_quit_group_calls_set_group_leave(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.set_group_leave = AsyncMock()

    with patch.object(quit_group_cmd, "finish") as mock_finish:
        await onebot11_quit_group(bot=mock_onebot11_bot, event=mock_onebot11_event)

    mock_onebot11_bot.set_group_leave.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, is_dismiss=False
    )
    assert finish_text(mock_finish) == "退出当前群"
