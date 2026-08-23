"""测试群公告命令 - OneBot11 群 API 映射覆盖"""

import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiofiles
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import announcement
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.announcement import (
    onebot_v11_send_group_announcement,
    send_group_announcement_cmd,
)
from tests.handle.commands.conftest import finish_text


def create_mock_image(raw: Any = None) -> MagicMock:
    """创建模拟的 UniImage 对象。"""
    image = MagicMock()
    image.raw = raw
    image.path = None
    image.url = None
    return image


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for announcement handler Depends() injection."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.mark.asyncio
async def test_onebot11_send_group_announcement_calls_extension_api_without_image(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
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
            session=mock_session,
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
    mock_session: Mock,
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
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    raw_bytes = b"fake-image-bytes"
    image = create_mock_image(raw=raw_bytes)

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await onebot_v11_send_group_announcement(
            content="公告",
            image=image,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_image = str(tmp_path / "announcement_images" / f"{expected_md5}.png")
    mock_onebot11_bot.call_api.assert_called_once_with(
        "_send_group_notice",
        group_id=mock_onebot11_event.group_id,
        content="公告",
        image=expected_image,
    )
    assert finish_text(mock_finish) == "群公告已发送"


@pytest.mark.asyncio
async def test_onebot11_send_group_announcement_rejects_unsupported_impl(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
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
            session=mock_session,
        )

    mock_onebot11_bot.call_api.assert_not_called()
    assert "不支持的 OneBot 版本" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_send_group_announcement_handles_action_failed(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    """``OneBot11ActionFailed`` 上抛时被 catch-all 分支捕获并提示用户。"""
    from nonebot.adapters.onebot.v11.exception import ActionFailed

    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": "NapCat.Onebot",
            "app_version": "4.20.0",
        }
    )
    mock_onebot11_bot.call_api = AsyncMock(
        side_effect=ActionFailed(
            status="failed",
            retcode=-1,
            data=None,
            message="unknown failure",
            wording="unknown failure",
            echo="1",
            stream="normal-action",
        )
    )
    mock_onebot11_bot.get_group_member_info = AsyncMock(return_value={"role": "admin"})

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await onebot_v11_send_group_announcement(
            content="公告",
            image=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert "发送群公告失败" in finish_text(mock_finish)


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
    assert result is not None
    assert result.local_path == expected_path
    async with aiofiles.open(result.local_path, "rb") as f:
        assert await f.read() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_returns_path_attribute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw 为空但 path 存在且位于插件目录内时，直接返回该路径。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    existing_path = tmp_path / "existing.png"
    image = MagicMock()
    image.raw = None
    image.path = str(existing_path)
    image.url = None

    result = await announcement._resolve_image_path(image)

    assert result is not None
    assert result.local_path == existing_path


@pytest.mark.asyncio
async def test_resolve_image_path_rejects_foreign_local_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path 属性指向插件目录外时拒绝（防任意文件读取外发）。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    foreign_path = tmp_path.parent / "secret.png"
    image = MagicMock()
    image.raw = None
    image.path = str(foreign_path)
    image.url = None

    result = await announcement._resolve_image_path(image)

    assert result is None


@pytest.mark.asyncio
async def test_resolve_image_path_accepts_memoryview_raw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raw 为 memoryview 时正确转换为 bytes（不因类型假设崩溃）。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    raw_bytes = b"fake-image-bytes"
    image = create_mock_image(raw=memoryview(raw_bytes))

    result = await announcement._resolve_image_path(image)

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_path = tmp_path / "announcement_images" / f"{expected_md5}.png"
    assert result is not None
    assert result.local_path == expected_path
    async with aiofiles.open(result.local_path, "rb") as f:
        assert await f.read() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_unknown_raw_falls_back_to_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw 为未知类型时跳过 raw 分支，回退到 URL 下载。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)
    download = AsyncMock(return_value=b"safe-image")
    monkeypatch.setattr(announcement, "download_public_http_bytes", download)

    image = create_mock_image(raw=object())
    image.url = "https://example.com/announcement.png"

    result = await announcement._resolve_image_path(image)

    assert result is not None
    download.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_image_path_returns_none_when_download_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """URL 下载返回 None（如 driver 无会话）时整体返回 None。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)
    monkeypatch.setattr(
        announcement,
        "download_public_http_bytes",
        AsyncMock(return_value=None),
    )

    image = create_mock_image()
    image.url = "https://example.com/announcement.png"

    result = await announcement._resolve_image_path(image)

    assert result is None


@pytest.mark.asyncio
async def test_resolve_image_path_uses_bounded_public_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(announcement, "plugin_config", fake_config)
    download = AsyncMock(return_value=b"safe-image")
    monkeypatch.setattr(announcement, "download_public_http_bytes", download)

    image = create_mock_image()
    image.url = "https://example.com/announcement.png"

    result = await announcement._resolve_image_path(image)

    assert result is not None
    download.assert_awaited_once_with(
        "https://example.com/announcement.png",
        max_bytes=10 * 1024 * 1024,
    )
