import hashlib
from dataclasses import dataclass
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from arclet.alconna import Alconna, Args
from nonebot import get_driver
from nonebot.drivers import Request
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ....core.config import plugin_config
from .triggers import COMMAND_TRIGGERS

_SEND_ANNOUNCEMENT = COMMAND_TRIGGERS["send_announcement"]


@dataclass(frozen=True)
class AnnouncementImagePath:
    """Resolved announcement image path for both bot and protocol filesystems."""

    local_path: Path
    protocol_path: str | None = None


def _announcement_image_cache_dir() -> Path:
    return plugin_config.announcement_image_cache_dir or (
        plugin_config.cache_dir / "announcement_images"
    )


def _join_protocol_path(base: str, relative_path: Path) -> str:
    separator = "\\" if "\\" in base and "/" not in base else "/"
    return base.rstrip("/\\") + separator + separator.join(relative_path.parts)


def _to_protocol_path(local_path: Path) -> str | None:
    cache_dir = plugin_config.announcement_image_cache_dir
    protocol_dir = plugin_config.announcement_image_protocol_dir
    if cache_dir is None or protocol_dir is None:
        return None

    try:
        relative_path = local_path.resolve().relative_to(cache_dir.resolve())
    except ValueError:
        return None
    return _join_protocol_path(protocol_dir, relative_path)


async def _cache_image_bytes(raw_bytes: bytes) -> AnnouncementImagePath:
    cache_dir = _announcement_image_cache_dir()
    await aiofiles.os.makedirs(cache_dir, exist_ok=True)
    md5 = hashlib.md5(raw_bytes).hexdigest()
    cache_path = cache_dir / f"{md5}.png"
    async with aiofiles.open(cache_path, "wb") as f:
        await f.write(raw_bytes)
    return AnnouncementImagePath(
        local_path=cache_path,
        protocol_path=_to_protocol_path(cache_path),
    )


async def _resolve_image_path(image: UniImage) -> AnnouncementImagePath | None:
    raw = getattr(image, "raw", None)
    if raw is not None:
        raw_bytes = raw.getvalue() if isinstance(raw, BytesIO) else raw
        return await _cache_image_bytes(raw_bytes)

    path = getattr(image, "path", None)
    if path is not None:
        local_path = Path(path)
        return AnnouncementImagePath(
            local_path=local_path,
            protocol_path=_to_protocol_path(local_path),
        )

    url = getattr(image, "url", None)
    if url is not None:
        driver = get_driver()
        get_session = getattr(driver, "get_session", None)
        if get_session is not None:
            async with get_session() as session:
                request = Request("GET", url)
                response = await session.request(request)
                content = response.content
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
