import hashlib
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from arclet.alconna import Alconna, Args
from nonebot import logger, require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ....core.config import plugin_config
from ....core.http_security import download_public_http_bytes
from .triggers import COMMAND_TRIGGERS

_SET_GROUP_NAME = COMMAND_TRIGGERS["set_group_name"]
_SET_GROUP_AVATAR = COMMAND_TRIGGERS["set_group_avatar"]
_AVATAR_IMAGE_DOWNLOAD_MAX_BYTES = 10 * 1024 * 1024


async def _cache_image_bytes(raw_bytes: bytes) -> Path:
    cache_dir = plugin_config.cache_dir / "announcement_images"
    await aiofiles.os.makedirs(cache_dir, exist_ok=True)
    md5 = hashlib.md5(raw_bytes).hexdigest()
    cache_path = cache_dir / f"{md5}.png"
    async with aiofiles.open(cache_path, "wb") as f:
        await f.write(raw_bytes)
    return cache_path


def _coerce_raw_image_bytes(raw: Any) -> bytes | None:
    """Coerce a uniseg Image raw payload into bytes without assuming one type."""
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, BytesIO):
        return raw.getvalue()
    if isinstance(raw, memoryview):
        return raw.tobytes()
    return None


def _is_plugin_owned_path(path: Path) -> bool:
    """Defence-in-depth: only localstore-owned dirs may be sent as images."""
    resolved = path.resolve()
    bases = [
        base.resolve()
        for base in (plugin_config.data_dir, plugin_config.cache_dir)
        if isinstance(base, Path)
    ]
    return any(resolved.is_relative_to(base) for base in bases)


async def _resolve_image_path(image: UniImage | None) -> Path | None:
    if image is None:
        return None
    raw = getattr(image, "raw", None)
    if raw is not None:
        raw_bytes = _coerce_raw_image_bytes(raw)
        if raw_bytes is not None:
            return await _cache_image_bytes(raw_bytes)

    path = getattr(image, "path", None)
    if path is not None:
        local_path = Path(path)
        # uniseg OneBot V11 builders never fill path today; if a future adapter
        # does, refuse paths outside plugin localstore dirs (arbitrary file read).
        if not _is_plugin_owned_path(local_path):
            logger.warning(f"拒绝非插件目录内的图片路径: {local_path}")
        else:
            return local_path

    url = getattr(image, "url", None)
    if url is not None:
        content = await download_public_http_bytes(
            str(url),
            max_bytes=_AVATAR_IMAGE_DOWNLOAD_MAX_BYTES,
        )
        if content is not None:
            return await _cache_image_bytes(content)

    return None


set_group_name_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_GROUP_NAME.primary, Args["new_group_name", str]),
    aliases=_SET_GROUP_NAME.aliases,
    priority=805,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_avatar_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_GROUP_AVATAR.primary, Args["image", UniImage | None]),
    aliases=_SET_GROUP_AVATAR.aliases,
    priority=805,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_set_group_name": "..adapters.onebot11.default.profile",
    "onebot11_set_group_avatar": "..adapters.onebot11.default.profile",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
