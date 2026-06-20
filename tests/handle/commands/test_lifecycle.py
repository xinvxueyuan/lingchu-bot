"""
测试群生命周期命令 - OneBot11 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.lifecycle import (
    onebot11_quit_group,
    quit_group_cmd,
)
from tests.handle.commands.conftest import finish_text


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
