"""
测试群资料设置命令 - Milky 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from src.plugins.nonebot_plugin_lingchu_bot.handle.commands.group.profile import (
    milkybot_set_group_avatar,
    milkybot_set_group_name,
    onebot11_set_group_name,
    set_group_avatar_cmd,
    set_group_name_cmd,
)
from tests.handle.commands.group.conftest import finish_text


def create_mock_image(raw: bytes | None = None) -> MagicMock:
    """创建模拟的 UniImage 对象。"""
    image = MagicMock()
    image.raw = raw
    image.path = None
    image.url = None
    return image


@pytest.mark.asyncio
async def test_set_group_name_calls_milky_api(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_name = AsyncMock()

    with patch.object(set_group_name_cmd, "finish") as mock_finish:
        await milkybot_set_group_name(
            new_group_name="新群名", bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_name.assert_called_once_with(
        group_id=mock_event.data.peer_id, new_group_name="新群名"
    )
    assert finish_text(mock_finish) == "群名称已设置为: 新群名"


@pytest.mark.asyncio
async def test_set_group_avatar_without_image(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_avatar = AsyncMock()

    with patch.object(set_group_avatar_cmd, "finish") as mock_finish:
        await milkybot_set_group_avatar(
            image=create_mock_image(), bot=mock_bot, event=mock_event
        )

    mock_bot.set_group_avatar.assert_called_once()
    call_kwargs = mock_bot.set_group_avatar.call_args.kwargs
    assert call_kwargs["group_id"] == mock_event.data.peer_id
    assert "path" in call_kwargs or call_kwargs.get("path") is None
    assert finish_text(mock_finish) == "群头像已更新"


@pytest.mark.asyncio
async def test_group_action_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_name = AsyncMock(side_effect=NetworkError("连接失败"))

    with patch.object(set_group_name_cmd, "finish") as mock_finish:
        await milkybot_set_group_name(
            new_group_name="新群名", bot=mock_bot, event=mock_event
        )

    assert "设置群名称失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_group_action_rejected_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_name = AsyncMock(side_effect=ActionFailed(message="权限不足"))

    with patch.object(set_group_name_cmd, "finish") as mock_finish:
        await milkybot_set_group_name(
            new_group_name="新群名", bot=mock_bot, event=mock_event
        )

    assert "设置群名称失败，操作被拒绝" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_avatar_network_error_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_avatar = AsyncMock(side_effect=NetworkError("timeout"))

    with patch.object(set_group_avatar_cmd, "finish") as mock_finish:
        await milkybot_set_group_avatar(
            image=create_mock_image(), bot=mock_bot, event=mock_event
        )

    assert "设置群头像失败，网络异常" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_set_group_avatar_action_failed_returns_readable_message(
    mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    mock_bot.set_group_avatar = AsyncMock(side_effect=ActionFailed(message="权限不足"))

    with patch.object(set_group_avatar_cmd, "finish") as mock_finish:
        await milkybot_set_group_avatar(
            image=create_mock_image(), bot=mock_bot, event=mock_event
        )

    assert "设置群头像失败，操作被拒绝" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_name_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.set_group_name = AsyncMock()

    with patch.object(set_group_name_cmd, "finish") as mock_finish:
        await onebot11_set_group_name(
            new_group_name="新群名",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_name.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, group_name="新群名"
    )
    assert finish_text(mock_finish) == "群名称已设置为: 新群名"
