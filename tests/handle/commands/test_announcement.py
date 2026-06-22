"""
测试群公告命令 - OneBot11 群 API 映射覆盖
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import announcement
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.announcement import (
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
async def test_onebot11_send_group_announcement_calls_extension_api_without_image(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
) -> None:
    """无图片时，_send_group_notice 不应传入 image 参数。"""
    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": "NapCat.Onebot",
            "app_version": "4.18.0",
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
    )
    assert "image" not in mock_onebot11_bot.call_api.call_args.kwargs
    assert finish_text(mock_finish) == "群公告已发送"


@pytest.mark.asyncio
async def test_onebot11_send_group_announcement_calls_extension_api_with_image(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """有图片时，_send_group_notice 应传入 image 参数（NapCat 转为 str）。"""
    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": "NapCat.Onebot",
            "app_version": "4.18.0",
        }
    )
    mock_onebot11_bot.call_api = AsyncMock()
    mock_onebot11_bot.get_group_member_info = AsyncMock(return_value={"role": "admin"})

    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    fake_config.announcement_image_cache_dir = None
    fake_config.announcement_image_protocol_dir = None
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    image = create_mock_image(raw=b"fake-image-bytes")

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await onebot_v11_send_group_announcement(
            content="公告",
            image=image,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    call_kwargs = mock_onebot11_bot.call_api.call_args.kwargs
    assert "image" in call_kwargs
    assert isinstance(call_kwargs["image"], str)
    mock_onebot11_bot.call_api.assert_called_once_with(
        "_send_group_notice",
        group_id=mock_onebot11_event.group_id,
        content="公告",
        image=call_kwargs["image"],
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
    fake_config.announcement_image_cache_dir = None
    fake_config.announcement_image_protocol_dir = None
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    raw_bytes = b"fake-image-bytes"
    image = create_mock_image(raw=raw_bytes)

    result = await announcement._resolve_image_path(image)

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_path = tmp_path / "announcement_images" / f"{expected_md5}.png"
    assert result is not None
    assert result.local_path == expected_path
    assert result.protocol_path is None
    assert result.local_path.read_bytes() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_uses_announcement_cache_bridge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """配置路径桥接时，缓存写入宿主路径并返回协议端路径。"""
    host_cache_dir = tmp_path / "napcat-announcement-images"
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path / "default-cache"
    fake_config.announcement_image_cache_dir = host_cache_dir
    fake_config.announcement_image_protocol_dir = "/lingchu/announcement-images"
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    raw_bytes = b"fake-image-bytes"
    image = create_mock_image(raw=raw_bytes)

    result = await announcement._resolve_image_path(image)

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    assert result is not None
    assert result.local_path == host_cache_dir / f"{expected_md5}.png"
    assert result.protocol_path == f"/lingchu/announcement-images/{expected_md5}.png"
    assert result.local_path.read_bytes() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_returns_path_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """raw 为空但 path 存在时，直接返回该路径。"""
    fake_config = MagicMock()
    fake_config.announcement_image_cache_dir = None
    fake_config.announcement_image_protocol_dir = None
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    image = MagicMock()
    image.raw = None
    image.path = "/tmp/existing.png"
    image.url = None

    result = await announcement._resolve_image_path(image)

    assert result is not None
    assert result.local_path == Path("/tmp/existing.png")
    assert result.protocol_path is None
