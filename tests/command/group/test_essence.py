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
