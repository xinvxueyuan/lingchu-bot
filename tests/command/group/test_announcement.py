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


@pytest.mark.asyncio
async def test_send_group_announcement_maps_base64_uri(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    """
    验证当 image_uri 使用 base64:// 前缀时，将其映射为 `base64` 参数并调用 send_group_announcement。

    调用 milkybot_send_group_announcement 时传入 image_uri="base64://aGVsbG8="，断言 bot.send_group_announcement 以 group_id=mock_event.data.peer_id、content="公告" 和 base64="aGVsbG8=" 被调用一次。
    """
    mock_bot.send_group_announcement = AsyncMock()

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH):
        await milkybot_send_group_announcement(
            content="公告",
            image_uri="base64://aGVsbG8=",
            bot=mock_bot,
            event=mock_event,
        )

    mock_bot.send_group_announcement.assert_called_once_with(
        group_id=mock_event.data.peer_id, content="公告", base64="aGVsbG8="
    )


@pytest.mark.asyncio
async def test_send_group_announcement_maps_http_uri(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.send_group_announcement = AsyncMock()

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH):
        await milkybot_send_group_announcement(
            content="公告",
            image_uri="https://example.com/img.png",
            bot=mock_bot,
            event=mock_event,
        )

    mock_bot.send_group_announcement.assert_called_once_with(
        group_id=mock_event.data.peer_id,
        content="公告",
        url="https://example.com/img.png",
    )


@pytest.mark.asyncio
async def test_send_group_announcement_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import NetworkError

    mock_bot.send_group_announcement = AsyncMock(side_effect=NetworkError("timeout"))

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image_uri=None, bot=mock_bot, event=mock_event
        )

    assert "发送群公告失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_send_group_announcement_action_failed_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import ActionFailed

    mock_bot.send_group_announcement = AsyncMock(
        side_effect=ActionFailed(message="权限不足")
    )

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image_uri=None, bot=mock_bot, event=mock_event
        )

    assert "发送群公告失败，操作被拒绝" in finish_text(mock_finish)
