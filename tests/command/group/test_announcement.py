"""
测试群公告命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.announcement import (
    milkybot_send_group_announcement,
)
from tests.command.group.conftest import finish_text

SEND_GROUP_ANNOUNCEMENT_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.announcement."
    "send_group_announcement_cmd.finish"
)


@pytest.mark.asyncio
async def test_send_group_announcement_without_image(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.send_group_announcement = AsyncMock()

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image_uri=None, bot=mock_bot, event=mock_event
        )

    mock_bot.send_group_announcement.assert_called_once_with(
        group_id=mock_event.data.peer_id, content="公告"
    )
    assert finish_text(mock_finish) == "群公告已发送"


@pytest.mark.asyncio
async def test_send_group_announcement_maps_file_uri(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.send_group_announcement = AsyncMock()

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH):
        await milkybot_send_group_announcement(
            content="公告",
            image_uri="file://C:/tmp/a.png",
            bot=mock_bot,
            event=mock_event,
        )

    mock_bot.send_group_announcement.assert_called_once_with(
        group_id=mock_event.data.peer_id, content="公告", path="C:/tmp/a.png"
    )
