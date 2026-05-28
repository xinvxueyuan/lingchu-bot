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


def create_mock_image(raw: bytes | None = None) -> MagicMock:
    """创建模拟的 UniImage 对象。"""
    image = MagicMock()
    image.raw = raw
    image.path = None
    image.url = None
    return image


@pytest.mark.asyncio
async def test_send_group_announcement_without_image(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.send_group_announcement = AsyncMock()
    mock_bot.get_impl_info = AsyncMock(return_value=MagicMock(impl_name="LLBot"))

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=create_mock_image(), bot=mock_bot, event=mock_event
        )

    mock_bot.send_group_announcement.assert_called_once()
    call_kwargs = mock_bot.send_group_announcement.call_args.kwargs
    assert call_kwargs["group_id"] == mock_event.data.peer_id
    assert call_kwargs["content"] == "公告"
    assert finish_text(mock_finish) == "群公告已发送"


@pytest.mark.asyncio
async def test_send_group_announcement_unsupported_milky_impl(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.get_impl_info = AsyncMock(return_value=MagicMock(impl_name="UnknownBot"))

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=create_mock_image(), bot=mock_bot, event=mock_event
        )

    assert "不支持的 Milky 实现" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_send_group_announcement_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    from nonebot.adapters.milky.exception import NetworkError

    mock_bot.send_group_announcement = AsyncMock(side_effect=NetworkError("timeout"))
    mock_bot.get_impl_info = AsyncMock(return_value=MagicMock(impl_name="LLBot"))

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=create_mock_image(), bot=mock_bot, event=mock_event
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
    mock_bot.get_impl_info = AsyncMock(return_value=MagicMock(impl_name="LLBot"))

    with patch(SEND_GROUP_ANNOUNCEMENT_FINISH) as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=create_mock_image(), bot=mock_bot, event=mock_event
        )

    assert "发送群公告失败，操作被拒绝" in finish_text(mock_finish)
