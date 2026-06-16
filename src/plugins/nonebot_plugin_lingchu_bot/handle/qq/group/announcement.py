import hashlib
from importlib import import_module
from io import BytesIO
from pathlib import Path
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import get_driver, logger
from nonebot.drivers import Request
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ....core.config import plugin_config
from ....i18n import _async as _
from .command_triggers import COMMAND_TRIGGERS

_SEND_ANNOUNCEMENT = COMMAND_TRIGGERS["send_announcement"]


async def _resolve_image_path(image: UniImage) -> Path | None:
    raw = getattr(image, "raw", None)
    if raw is not None:
        raw_bytes = raw.getvalue() if isinstance(raw, BytesIO) else raw
        cache_dir = plugin_config.cache_dir / "announcement_images"
        cache_dir.mkdir(parents=True, exist_ok=True)
        md5 = hashlib.md5(raw_bytes).hexdigest()
        cache_path = cache_dir / f"{md5}.png"
        cache_path.write_bytes(raw_bytes)
        return cache_path

    path = getattr(image, "path", None)
    if path is not None:
        return Path(path)

    url = getattr(image, "url", None)
    if url is not None:
        driver = get_driver()
        get_session = getattr(driver, "get_session", None)
        if get_session is not None:
            async with get_session() as session:
                request = Request("GET", url)
                response = await session.request(request)
                content = response.content
                cache_dir = plugin_config.cache_dir / "announcement_images"
                cache_dir.mkdir(parents=True, exist_ok=True)
                md5 = hashlib.md5(content).hexdigest()
                cache_path = cache_dir / f"{md5}.png"
                cache_path.write_bytes(content)
                return cache_path

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
    "milkybot_send_group_announcement": "..milky.v1_2.default.group.announcement",
    "onebot_v11_send_group_announcement": ("..onebot.v11.default.group.announcement"),
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入announcement处理器..."))
