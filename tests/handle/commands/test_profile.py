"""
测试群资料设置命令 - OneBot11 群 API 映射覆盖
"""

import base64
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


@pytest.mark.asyncio
async def test_onebot11_set_group_avatar_calls_napcat_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, tmp_path: Path
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
    image_path.write_bytes(b"fake-image-bytes")
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
        )

    mock_onebot11_bot.call_api.assert_called_once_with(
        "set_group_portrait",
        group_id=mock_onebot11_event.group_id,
        file="base64://" + base64.b64encode(b"fake-image-bytes").decode(),
    )
    assert finish_text(mock_finish) == "群头像已更新"


@pytest.mark.asyncio
async def test_onebot11_set_group_avatar_rejects_unsupported_impl(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
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
        )

    mock_onebot11_bot.call_api.assert_not_called()
    assert "不支持设置群头像" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_resolve_image_path_returns_none_for_none_image() -> None:
    """image 为 None 时返回 None。"""
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
    assert result.read_bytes() == raw_bytes
