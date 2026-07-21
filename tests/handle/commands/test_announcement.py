"""测试群公告命令 - OneBot11 群 API 映射覆盖"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiofiles
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
    # 模拟"未配置路径桥接"的默认场景：announcement_image_cache_dir 派生自
    # cache_dir（与新类型 `Path` 下的 localstore 默认行为一致），protocol_dir 留空
    fake_config.announcement_image_cache_dir = tmp_path / "announcement_images"
    fake_config.announcement_image_protocol_dir = None
    monkeypatch.setattr(announcement, "plugin_config", fake_config)

    image = create_mock_image(raw=b"fake-image-bytes")

    with patch.object(send_group_announcement_cmd, "finish") as mock_finish:
        await onebot_v11_send_group_announcement(
            content="公告",
            image=image,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
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
async def test_resolve_image_path_caches_raw_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_resolve_image_path 通过 aiofiles 异步写入缓存文件。"""
    fake_config = MagicMock()
    fake_config.cache_dir = tmp_path
    # 模拟"未配置路径桥接"的默认场景：announcement_image_cache_dir 派生自
    # cache_dir（与新类型 `Path` 下的 localstore 默认行为一致），protocol_dir 留空
    fake_config.announcement_image_cache_dir = tmp_path / "announcement_images"
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
    async with aiofiles.open(result.local_path, "rb") as f:
        assert await f.read() == raw_bytes


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
    async with aiofiles.open(result.local_path, "rb") as f:
        assert await f.read() == raw_bytes


@pytest.mark.asyncio
async def test_resolve_image_path_returns_path_attribute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw 为空但 path 存在时，直接返回该路径。"""
    fake_config = MagicMock()
    # 模拟"未配置路径桥接"的默认场景：announcement_image_cache_dir 派生自
    # cache_dir（与新类型 `Path` 下的 localstore 默认行为一致），protocol_dir 留空
    fake_config.announcement_image_cache_dir = tmp_path / "announcement_images"
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


class TestDetectCachePathStyleMismatch:
    def test_linux_windows_style_drive_letter_in_cache_dir(
        self, tmp_path: Path
    ) -> None:
        cache = Path("C:/dev/lingchu-bot/.local/napcat-announcement-images")
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=cache,
            protocol_dir="/lingchu-bot/.local/napcat-announcement-images",
            system_type="Linux",
        )
        assert result is not None
        assert result.detected_style == "Windows"
        assert result.system_type == "Linux"
        assert result.cache_dir == str(cache)

    def test_linux_windows_style_drive_letter_in_protocol_dir(self) -> None:
        cache = Path("/home/xinvdev/lingchu-bot/.local/napcat-announcement-images")
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=cache,
            protocol_dir="C:/lingchu-bot/.local/napcat-announcement-images",
            system_type="Linux",
        )
        assert result is not None
        assert result.detected_style == "Windows"
        assert result.protocol_dir.startswith("C:")

    def test_linux_posix_paths_are_silent(self, tmp_path: Path) -> None:
        cache = tmp_path / "napcat-announcement-images"
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=cache,
            protocol_dir="/lingchu/announcement-images",
            system_type="Linux",
        )
        assert result is None

    def test_linux_unset_protocol_dir_is_silent(self, tmp_path: Path) -> None:
        cache = Path("C:/dev/lingchu-bot/.local/napcat-announcement-images")
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=cache,
            protocol_dir=None,
            system_type="Linux",
        )
        assert result is None

    def test_windows_posix_cache_dir_flags_mismatch(self) -> None:
        cache = Path("/home/xinvdev/lingchu-bot/.local/napcat-announcement-images")
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=cache,
            protocol_dir="C:/lingchu/announcement-images",
            system_type="Windows",
        )
        assert result is not None
        assert result.detected_style == "POSIX"

    def test_windows_unc_protocol_dir_is_silent(self) -> None:
        # UNC paths (`\\wsl$\...`) are intentionally not flagged on Windows
        # hosts even though they start with backslashes.
        cache = Path("C:/Users/xinvdev/lingchu-bot/.local/napcat-announcement-images")
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=cache,
            protocol_dir="\\\\wsl$\\Debian\\home\\xinvdev\\lingchu-bot\\.local\\napcat-announcement-images",
            system_type="Windows",
        )
        assert result is None

    def test_other_system_type_is_silent(self, tmp_path: Path) -> None:
        result = announcement._detect_cache_path_style_mismatch(
            cache_dir=tmp_path / "announcement-images",
            protocol_dir="/lingchu/announcement-images",
            system_type="Other",
        )
        assert result is None


class TestSendGroupNoticeNapcatImageError:
    """Tests for send_group_notice_napcat image format errors.

    Covers the actionable warning emitted when NapCat rejects the announcement
    image format (retcode=1200).
    """

    @pytest.mark.asyncio
    async def test_image_format_error_emits_warning_and_reraises(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        from nonebot.adapters.onebot.v11.exception import ActionFailed

        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat import (
            announcement as napcat_announcement_module,
        )
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat.announcement import (
            send_group_notice_napcat,
        )

        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=ActionFailed(
                status="failed",
                retcode=1200,
                data=None,
                message=(
                    "群公告/lingchu-bot/.local/napcat-announcement-images/"
                    "54367a9439f567b9c8cdc04230ce3de8.png设置失败,"
                    "image字段可能格式不正确"
                ),
                wording=(
                    "群公告/lingchu-bot/.local/napcat-announcement-images/"
                    "54367a9439f567b9c8cdc04230ce3de8.png设置失败,"
                    "image字段可能格式不正确"
                ),
                echo="3",
                stream="normal-action",
            )
        )
        image_path = announcement.AnnouncementImagePath(
            local_path=Path(
                "/home/xinvdev/lingchu-bot/.local/napcat-announcement-images/"
                "54367a9439f567b9c8cdc04230ce3de8.png"
            ),
            protocol_path="/lingchu-bot/.local/napcat-announcement-images/"
            "54367a9439f567b9c8cdc04230ce3de8.png",
        )

        with (
            patch.object(napcat_announcement_module.logger, "warning") as mock_warning,
            pytest.raises(ActionFailed),
        ):
            await send_group_notice_napcat(
                content="公告",
                group_id=mock_onebot11_event.group_id,
                image_path=image_path,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        # The actionable warning must mention both paths and the env
        # variable name so the user can fix the configuration quickly.
        mock_warning.assert_called_once()
        message = mock_warning.call_args.args[0]
        assert "/lingchu-bot/.local/napcat-announcement-images/" in message
        assert "/home/xinvdev/lingchu-bot/.local/napcat-announcement-images/" in message
        assert "LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR" in message

    @pytest.mark.asyncio
    async def test_non_image_error_does_not_emit_extra_warning(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        from nonebot.adapters.onebot.v11.exception import ActionFailed

        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat import (
            announcement as napcat_announcement_module,
        )
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat.announcement import (
            send_group_notice_napcat,
        )

        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=ActionFailed(
                status="failed",
                retcode=1400,
                data=None,
                message="权限不足",
                wording="权限不足",
                echo="1",
                stream="normal-action",
            )
        )
        image_path = announcement.AnnouncementImagePath(
            local_path=Path("/home/xinvdev/lingchu-bot/.local/x.png"),
            protocol_path="/lingchu/x.png",
        )

        with (
            patch.object(napcat_announcement_module.logger, "warning") as mock_warning,
            patch.object(napcat_announcement_module.logger, "error") as mock_error,
            pytest.raises(ActionFailed),
        ):
            await send_group_notice_napcat(
                content="公告",
                group_id=mock_onebot11_event.group_id,
                image_path=image_path,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        # No actionable image-format warning should be emitted for other
        # retcodes; the original `f"发送群公告失败: {e!r}"` error log is
        # the only record.
        mock_warning.assert_not_called()
        mock_error.assert_called_once()
        assert "发送群公告失败" in mock_error.call_args.args[0]

    @pytest.mark.asyncio
    async def test_image_error_without_image_path_skips_warning(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        from nonebot.adapters.onebot.v11.exception import ActionFailed

        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat import (
            announcement as napcat_announcement_module,
        )
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat.announcement import (
            send_group_notice_napcat,
        )

        # Even if NapCat happens to return retcode=1200, the actionable
        # warning is only useful when an image was attached.
        mock_onebot11_bot.call_api = AsyncMock(
            side_effect=ActionFailed(
                status="failed",
                retcode=1200,
                data=None,
                message="image 字段可能格式不正确",
                wording="image 字段可能格式不正确",
                echo="1",
                stream="normal-action",
            )
        )

        with (
            patch.object(napcat_announcement_module.logger, "warning") as mock_warning,
            pytest.raises(ActionFailed),
        ):
            await send_group_notice_napcat(
                content="公告",
                group_id=mock_onebot11_event.group_id,
                image_path=None,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        mock_warning.assert_not_called()
