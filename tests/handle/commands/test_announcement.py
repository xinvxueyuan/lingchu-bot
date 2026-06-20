"""
测试群公告命令 - Milky 群 API 映射覆盖
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import announcement
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.announcement import (
    milkybot_send_group_announcement,
    onebot_v11_send_group_announcement,
    send_group_announcement_cmd,
)
from tests.handle.commands.conftest import finish_text


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

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=None, bot=mock_bot, event=mock_event
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

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
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

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=None, bot=mock_bot, event=mock_event
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

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await milkybot_send_group_announcement(
            content="公告", image=None, bot=mock_bot, event=mock_event
        )

    assert "发送群公告失败，操作被拒绝" in finish_text(mock_finish)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("app_name", "version"),
    [("LLOneBot", "7.12.0"), ("NapCat.Onebot", "4.18.0")],
)
async def test_onebot11_send_group_announcement_calls_extension_api(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    app_name: str,
    version: str,
) -> None:
    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": app_name,
            "app_version": version,
        }
    )
    mock_onebot11_bot.call_api = AsyncMock()
    mock_onebot11_bot.get_group_member_info = AsyncMock(return_value={"role": "admin"})

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await onebot_v11_send_group_announcement(
            content="公告",
            image=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.call_api.assert_called_once_with(
        "_send_group_notice",
        group_id=mock_onebot11_event.group_id,
        content="公告",
        image=None,
    )
    assert finish_text(mock_finish) == "群公告已发送"


@pytest.mark.asyncio
async def test_onebot11_send_group_announcement_rejects_unsupported_impl(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": "UnknownBot",
            "app_version": "1.0.0",
        }
    )
    mock_onebot11_bot.call_api = AsyncMock()
    mock_onebot11_bot.get_group_member_info = AsyncMock(return_value={"role": "admin"})

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await onebot_v11_send_group_announcement(
            content="公告",
            image=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.call_api.assert_not_called()
    assert "不支持的 OneBot 版本" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_resolve_image_path_caches_raw_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_resolve_image_path 通过 aiofiles 异步写入缓存文件。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    raw_bytes = b"fake-image-bytes"
    image = create_mock_image(raw=raw_bytes)

    result = await announcement._resolve_image_path(image)

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_path = tmp_path / "announcement_images" / f"{expected_md5}.png"
    assert result == expected_path
    assert result is not None
    assert result.read_bytes() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_returns_path_attribute() -> None:
    """raw 为空但 path 存在时，直接返回该路径。"""
    image = MagicMock()
    image.raw = None
    image.path = "/tmp/existing.png"
    image.url = None

    result = await announcement._resolve_image_path(image)

    assert result == Path("/tmp/existing.png")
