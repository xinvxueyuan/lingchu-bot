"""
测试群资料设置命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.profile import (
    milkybot_set_group_avatar,
    milkybot_set_group_name,
)
from tests.command.group.conftest import finish_text

SET_GROUP_NAME_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.profile."
    "set_group_name_cmd.finish"
)
SET_GROUP_AVATAR_FINISH = (
    "src.plugins.nonebot_plugin_lingchu_bot.handle.command.group.profile."
    "set_group_avatar_cmd.finish"
)


@pytest.mark.asyncio
async def test_set_group_name_calls_milky_api(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_name = AsyncMock()

    with patch(SET_GROUP_NAME_FINISH) as mock_finish:
        await milkybot_set_group_name(
            new_group_name="新群名", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_name.assert_called_once_with(
        group_id=mock_event.data.peer_id, new_group_name="新群名"
    )
    assert finish_text(mock_finish) == "群名称已设置为: 新群名"


@pytest.mark.asyncio
async def test_set_group_avatar_maps_base64_uri(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_avatar = AsyncMock()

    with patch(SET_GROUP_AVATAR_FINISH) as mock_finish:
        await milkybot_set_group_avatar(
            image_uri="base64://abcd", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_avatar.assert_called_once_with(
        group_id=mock_event.data.peer_id, base64="abcd"
    )
    assert finish_text(mock_finish) == "群头像已更新"


@pytest.mark.asyncio
async def test_group_action_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_name = AsyncMock(side_effect=NetworkError("连接失败"))

    with patch(SET_GROUP_NAME_FINISH) as mock_finish:
        await milkybot_set_group_name(
            new_group_name="新群名", bot=mock_bot, event=mock_event
        )

    assert "设置群名称失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_group_action_rejected_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_name = AsyncMock(side_effect=ActionFailed(message="权限不足"))

    with patch(SET_GROUP_NAME_FINISH) as mock_finish:
        await milkybot_set_group_name(
            new_group_name="新群名", bot=mock_bot, event=mock_event
        )

    assert "设置群名称失败，操作被拒绝" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_avatar_maps_file_uri(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_avatar = AsyncMock()

    with patch(SET_GROUP_AVATAR_FINISH) as mock_finish:
        await milkybot_set_group_avatar(
            image_uri="file:///tmp/avatar.png", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_avatar.assert_called_once_with(
        group_id=mock_event.data.peer_id, path="/tmp/avatar.png"
    )
    assert finish_text(mock_finish) == "群头像已更新"


@pytest.mark.asyncio
async def test_set_group_avatar_maps_http_url(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_avatar = AsyncMock()

    with patch(SET_GROUP_AVATAR_FINISH) as mock_finish:
        await milkybot_set_group_avatar(
            image_uri="https://example.com/avatar.jpg", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_avatar.assert_called_once_with(
        group_id=mock_event.data.peer_id, url="https://example.com/avatar.jpg"
    )
    assert finish_text(mock_finish) == "群头像已更新"


@pytest.mark.asyncio
async def test_set_group_avatar_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    """
    验证在设置群头像时网络错误会返回可读的失败提示。

    模拟 Milky API 在调用 set_group_avatar 时抛出 NetworkError，并断言最终的 finish 文本包含 "设置群头像失败，网络异常"。
    """
    mock_bot.set_group_avatar = AsyncMock(side_effect=NetworkError("timeout"))

    with patch(SET_GROUP_AVATAR_FINISH) as mock_finish:
        await milkybot_set_group_avatar(
            image_uri="https://example.com/avatar.jpg", bot=mock_bot, event=mock_event
        )

    assert "设置群头像失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_avatar_action_failed_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    """
    验证在设置群头像时，当 Milky API 抛出 ActionFailed（表示操作被拒绝）时，指令会返回可读的失败消息。

    断言被 patch 的 finish 处理器的输出包含文本 "设置群头像失败，操作被拒绝"。
    """
    mock_bot.set_group_avatar = AsyncMock(side_effect=ActionFailed(message="权限不足"))

    with patch(SET_GROUP_AVATAR_FINISH) as mock_finish:
        await milkybot_set_group_avatar(
            image_uri="https://example.com/avatar.jpg", bot=mock_bot, event=mock_event
        )

    assert "设置群头像失败，操作被拒绝" in finish_text(mock_finish)
