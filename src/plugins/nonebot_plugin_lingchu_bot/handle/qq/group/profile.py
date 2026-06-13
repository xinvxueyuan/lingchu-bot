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
from ....services.permissions import bind_command_key
from .command_triggers import COMMAND_TRIGGERS

_SET_GROUP_NAME = COMMAND_TRIGGERS["set_group_name"]
_SET_GROUP_AVATAR = COMMAND_TRIGGERS["set_group_avatar"]


async def _resolve_image_path(image: UniImage | None) -> Path | None:
    if image is None:
        return None
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


set_group_name_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_GROUP_NAME.primary, Args["new_group_name", str]),
    aliases=_SET_GROUP_NAME.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(set_group_name_cmd, "set_group_name")
set_group_avatar_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_GROUP_AVATAR.primary, Args["image", UniImage | None]),
    aliases=_SET_GROUP_AVATAR.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(set_group_avatar_cmd, "set_group_avatar")

_LAZY_EXPORTS = {
    "milkybot_set_group_name": "..milky.v1_2.default.group.profile",
    "milkybot_set_group_avatar": "..milky.v1_2.default.group.profile",
    "onebot11_set_group_name": "..onebot.v11.default.group.profile",
    "onebot11_set_group_avatar": "..onebot.v11.default.group.profile",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入profile处理器..."))
