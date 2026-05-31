import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import get_driver
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.drivers import Request
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ....core.config import plugin_config
from ....i18n import _async as _
from .common import run_group_action_milky


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
    command=Alconna("设置群名称", Args["new_group_name", str]),
    aliases={"改群名", "修改群名称", "设置群名"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_avatar_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群头像", Args["image", UniImage | None]),
    aliases={"改群头像", "修改群头像"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@set_group_name_cmd.handle()
async def milkybot_set_group_name(
    new_group_name: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    """
    设置群名称。

    Parameters:
        new_group_name (str): 要设置的新群名称。

    Returns:
        Any: 群名称设置流程返回的结果。
    """
    return await run_group_action_milky(
        set_group_name_cmd,
        await _("设置群名称"),
        lambda: bot.set_group_name(
            group_id=event.data.peer_id, new_group_name=new_group_name
        ),
        (await _("群名称已设置为: {new_group_name}")).format(
            new_group_name=new_group_name
        ),
    )


@set_group_avatar_cmd.handle()
async def milkybot_set_group_avatar(
    image: UniImage | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    image_path = await _resolve_image_path(image)
    if image_path is None:
        await set_group_avatar_cmd.finish(await _("请上传一张图片"))
    return await run_group_action_milky(
        set_group_avatar_cmd,
        await _("设置群头像"),
        lambda: bot.set_group_avatar(group_id=event.data.peer_id, path=image_path),
        await _("群头像已更新"),
    )
