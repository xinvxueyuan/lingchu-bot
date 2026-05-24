"""
测试群生命周期命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.lifecycle import (
    milkybot_quit_group,
)
from tests.command.group.conftest import finish_text

QUIT_GROUP_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.lifecycle."
    "quit_group_cmd.finish"
)


@pytest.mark.asyncio
async def test_quit_group_calls_milky_api(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.quit_group = AsyncMock()

    with patch(QUIT_GROUP_FINISH) as mock_finish:
        await milkybot_quit_group(bot=mock_bot, event=mock_event)

    mock_bot.quit_group.assert_called_once_with(group_id=mock_event.data.peer_id)
    assert finish_text(mock_finish) == "已退出当前群"


@pytest.mark.asyncio
async def test_quit_group_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import NetworkError

    mock_bot.quit_group = AsyncMock(side_effect=NetworkError("connection refused"))

    with patch(QUIT_GROUP_FINISH) as mock_finish:
        await milkybot_quit_group(bot=mock_bot, event=mock_event)

    assert "退出群失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_quit_group_action_failed_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import ActionFailed

    mock_bot.quit_group = AsyncMock(side_effect=ActionFailed(message="操作失败"))

    with patch(QUIT_GROUP_FINISH) as mock_finish:
        await milkybot_quit_group(bot=mock_bot, event=mock_event)

    assert "退出群失败，操作被拒绝" in finish_text(mock_finish)
