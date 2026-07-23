from dataclasses import dataclass
import hashlib
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Any, Final

import aiofiles
import aiofiles.os
from arclet.alconna import Alconna, Args
from nonebot import require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ....core.config import plugin_config
from ....core.http_security import download_public_http_bytes
from .triggers import COMMAND_TRIGGERS

_SEND_ANNOUNCEMENT = COMMAND_TRIGGERS["send_announcement"]
_ANNOUNCEMENT_IMAGE_DOWNLOAD_MAX_BYTES: Final = 10 * 1024 * 1024


@dataclass(frozen=True)
class AnnouncementImagePath:
    """Resolved announcement image path."""

    local_path: Path


def _announcement_image_cache_dir() -> Path:
    return plugin_config.cache_dir / "announcement_images"


async def _cache_image_bytes(raw_bytes: bytes) -> AnnouncementImagePath:
    cache_dir = _announcement_image_cache_dir()
    await aiofiles.os.makedirs(cache_dir, exist_ok=True)
    md5 = hashlib.md5(raw_bytes).hexdigest()
    cache_path = cache_dir / f"{md5}.png"
    async with aiofiles.open(cache_path, "wb") as f:
        await f.write(raw_bytes)
    return AnnouncementImagePath(local_path=cache_path)


async def _resolve_image_path(image: UniImage) -> AnnouncementImagePath | None:
    raw = getattr(image, "raw", None)
    if raw is not None:
        raw_bytes = raw.getvalue() if isinstance(raw, BytesIO) else raw
        return await _cache_image_bytes(raw_bytes)

    path = getattr(image, "path", None)
    if path is not None:
        local_path = Path(path)
        return AnnouncementImagePath(local_path=local_path)

    url = getattr(image, "url", None)
    if url is not None:
        content = await download_public_http_bytes(
            str(url),
            max_bytes=_ANNOUNCEMENT_IMAGE_DOWNLOAD_MAX_BYTES,
        )
        if content is not None:
            return await _cache_image_bytes(content)

    return None


send_group_announcement_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _SEND_ANNOUNCEMENT.primary,
        Args["content", str]["image?", UniImage, None],
    ),
    aliases=_SEND_ANNOUNCEMENT.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot_v11_send_group_announcement": ("..adapters.onebot11.default.announcement"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
