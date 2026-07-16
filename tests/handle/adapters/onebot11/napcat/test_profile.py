"""测试 napcat/profile.py 中 set_group_portrait_napcat 头像设置实现。

覆盖范围：
- 正常路径：读取图片文件、base64 编码、调用 set_group_portrait API
- 异常路径（行 34-36）：ActionFailed 时记录日志并重新抛出
"""

from base64 import b64encode
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.napcat.profile import (
    set_group_portrait_napcat,
)

_GROUP_ID = 123456789
_IMAGE_BYTES = b"\x89PNG\r\n\x1a\nfake-png-body"


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.call_api = AsyncMock()
    return bot


@pytest.fixture
def mock_event() -> MagicMock:
    event = MagicMock()
    event.group_id = _GROUP_ID
    return event


@pytest.mark.asyncio
async def test_set_group_portrait_success(
    tmp_path: Path, mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    """正常路径：读取图片并以 base64:// 编码调用 set_group_portrait API。"""
    image_path = tmp_path / "avatar.png"
    image_path.write_bytes(_IMAGE_BYTES)

    await set_group_portrait_napcat(
        image_path=image_path, bot=mock_bot, event=mock_event
    )

    mock_bot.call_api.assert_awaited_once_with(
        "set_group_portrait",
        group_id=_GROUP_ID,
        file="base64://" + b64encode(_IMAGE_BYTES).decode(),
    )


@pytest.mark.asyncio
async def test_set_group_portrait_logs_and_reraises_on_action_failed(
    tmp_path: Path, mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    """ActionFailed 时记录错误日志并重新抛出原异常（覆盖行 34-36）。"""
    image_path = tmp_path / "avatar.png"
    image_path.write_bytes(_IMAGE_BYTES)

    failure = OneBot11ActionFailed(message="set_group_portrait failed", retcode=1200)
    mock_bot.call_api = AsyncMock(side_effect=failure)

    with pytest.raises(OneBot11ActionFailed):
        await set_group_portrait_napcat(
            image_path=image_path, bot=mock_bot, event=mock_event
        )

    mock_bot.call_api.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_group_portrait_base64_matches_file_content(
    tmp_path: Path, mock_bot: MagicMock, mock_event: MagicMock
) -> None:
    """base64 字段必须与磁盘文件内容严格对应，避免图片被 NapCat 拒收。"""
    image_path = tmp_path / "portrait.bin"
    payload = bytes(range(256))
    image_path.write_bytes(payload)

    await set_group_portrait_napcat(
        image_path=image_path, bot=mock_bot, event=mock_event
    )

    call_kwargs = mock_bot.call_api.await_args.kwargs
    assert call_kwargs["file"].startswith("base64://")
    encoded = call_kwargs["file"][len("base64://") :]
    assert encoded == b64encode(payload).decode()
    assert call_kwargs["group_id"] == _GROUP_ID
