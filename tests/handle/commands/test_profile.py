"""测试群资料设置命令 - OneBot11 群 API 映射覆盖"""

import base64
import hashlib
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiofiles
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import http_security
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import profile
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.profile import (
    onebot11_set_group_avatar,
    onebot11_set_group_name,
    set_group_avatar_cmd,
    set_group_name_cmd,
)
from tests.handle.commands.conftest import finish_text


def create_mock_image(raw: bytes | None = None) -> MagicMock:
    """创建模拟的 UniImage 对象。"""
    image = MagicMock()
    image.raw = raw
    image.path = None
    image.url = None
    return image


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for profile handler Depends() injection."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.mark.asyncio
async def test_onebot11_set_group_name_calls_v11_api(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    mock_onebot11_bot.set_group_name = AsyncMock()

    with patch.object(set_group_name_cmd, "finish") as mock_finish:
        await onebot11_set_group_name(
            new_group_name="新群名",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    mock_onebot11_bot.set_group_name.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, group_name="新群名"
    )
    assert finish_text(mock_finish) == "群名称已设置为: 新群名"


@pytest.mark.asyncio
async def test_onebot11_set_group_avatar_calls_napcat_api(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
    tmp_path: Path,
) -> None:
    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": "NapCat.Onebot",
            "app_version": "4.18.6",
        }
    )
    mock_onebot11_bot.call_api = AsyncMock()
    image_path = tmp_path / "test.png"
    async with aiofiles.open(image_path, "wb") as f:
        await f.write(b"fake-image-bytes")
    resolve_path = (
        "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11"
        ".default.profile._resolve_image_path"
    )

    with (
        patch.object(set_group_avatar_cmd, "finish") as mock_finish,
        patch(resolve_path, new=AsyncMock(return_value=image_path)),
    ):
        await onebot11_set_group_avatar(
            image=create_mock_image(raw=b"fake"),
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    mock_onebot11_bot.call_api.assert_called_once_with(
        "set_group_portrait",
        group_id=mock_onebot11_event.group_id,
        file="base64://" + base64.b64encode(b"fake-image-bytes").decode(),
    )
    assert finish_text(mock_finish) == "群头像已更新"


@pytest.mark.asyncio
async def test_onebot11_set_group_avatar_rejects_unsupported_impl(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    mock_onebot11_bot.get_version_info = AsyncMock(
        return_value={
            "protocol_version": "v11",
            "app_name": "go-cqhttp",
            "app_version": "1.0.0",
        }
    )
    mock_onebot11_bot.call_api = AsyncMock()
    image_path = Path("/tmp/test.png")
    resolve_path = (
        "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11"
        ".default.profile._resolve_image_path"
    )

    with (
        patch.object(set_group_avatar_cmd, "finish") as mock_finish,
        patch(resolve_path, new=AsyncMock(return_value=image_path)),
    ):
        await onebot11_set_group_avatar(
            image=create_mock_image(raw=b"fake"),
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    mock_onebot11_bot.call_api.assert_not_called()
    assert "不支持设置群头像" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_resolve_image_path_returns_none_for_none_image() -> None:
    """Image 为 None 时返回 None。"""
    result = await profile._resolve_image_path(None)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_image_path_caches_raw_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_resolve_image_path 通过 aiofiles 异步写入缓存文件。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(profile, "plugin_config", fake_config)

    raw_bytes = b"fake-avatar-bytes"
    image = create_mock_image(raw=raw_bytes)

    result = await profile._resolve_image_path(image)

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_path = tmp_path / "announcement_images" / f"{expected_md5}.png"
    assert result == expected_path
    assert result is not None
    async with aiofiles.open(result, "rb") as f:
        assert await f.read() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_returns_path_for_path_attribute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_resolve_image_path 直接返回 path 属性对应的 Path 对象。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(profile, "plugin_config", fake_config)

    expected_path = tmp_path / "avatar.png"
    image = MagicMock()
    image.raw = None
    image.path = str(expected_path)
    image.url = None

    result = await profile._resolve_image_path(image)

    assert result == expected_path


@pytest.mark.asyncio
async def test_resolve_image_path_caches_raw_bytesio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_resolve_image_path 处理 BytesIO 类型的 raw 属性。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(profile, "plugin_config", fake_config)

    raw_bytes = b"bytesio-avatar-bytes"
    image = MagicMock()
    image.raw = BytesIO(raw_bytes)
    image.path = None
    image.url = None

    result = await profile._resolve_image_path(image)

    expected_md5 = hashlib.md5(raw_bytes).hexdigest()
    expected_path = tmp_path / "announcement_images" / f"{expected_md5}.png"
    assert result == expected_path
    assert result is not None
    async with aiofiles.open(result, "rb") as f:
        assert await f.read() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_downloads_and_caches_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_resolve_image_path 通过 driver session 下载 URL 图片并缓存。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(profile, "plugin_config", fake_config)

    downloaded_content = b"downloaded-image-bytes"
    request_call = AsyncMock(return_value=SimpleNamespace(content=downloaded_content))

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request_call)

        async def __aexit__(self, *args: object) -> None:
            return None

    fake_driver = SimpleNamespace(get_session=SessionContext)
    monkeypatch.setattr(http_security, "get_driver", lambda: fake_driver)
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("93.184.216.34",)),
    )

    image = MagicMock()
    image.raw = None
    image.path = None
    image.url = "http://example.com/avatar.png"

    result = await profile._resolve_image_path(image)

    expected_md5 = hashlib.md5(downloaded_content).hexdigest()
    expected_path = tmp_path / "announcement_images" / f"{expected_md5}.png"
    assert result == expected_path
    assert result is not None
    async with aiofiles.open(result, "rb") as f:
        assert await f.read() == downloaded_content
    request_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_image_path_returns_none_when_driver_has_no_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Driver 没有 get_session 方法时，URL 图片返回 None。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(profile, "plugin_config", fake_config)

    fake_driver = SimpleNamespace()
    monkeypatch.setattr(http_security, "get_driver", lambda: fake_driver)
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("93.184.216.34",)),
    )

    image = MagicMock()
    image.raw = None
    image.path = None
    image.url = "http://example.com/avatar.png"

    result = await profile._resolve_image_path(image)

    assert result is None


@pytest.mark.asyncio
async def test_resolve_image_path_returns_none_when_no_resolvable_attribute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """raw/path/url 均为 None 时返回 None。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    monkeypatch.setattr(profile, "plugin_config", fake_config)

    image = MagicMock()
    image.raw = None
    image.path = None
    image.url = None

    result = await profile._resolve_image_path(image)

    assert result is None
