import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import get_driver, logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.onebot.v11 import Bot as OneBot11
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBBot11_GroupMessageEvent,
)
from nonebot.drivers import Request
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage
from packaging.version import InvalidVersion, parse

from ....core.config import plugin_config
from ....i18n import _async as _
from .common import run_group_action_milky, run_group_action_onebot11


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
    command=Alconna("发送群公告", Args["content", str]["image?", UniImage, None]),
    aliases={"发群公告", "群公告"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# test_onebot_v11_send_group_announcement_cmd: type[AlconnaMatcher] = on_alconna(
#     command=Alconna(
#         "测试onebotv11发送群公告", Args["content", str]["image?", UniImage, None]
#     ),
#     aliases={"测试onebotv11发送群公告", "测试onebotv11群公告"},
#     priority=5,
#     block=True,
#     use_cmd_sep=True,
#     use_cmd_start=True,
# )

# test_milkybot_send_group_announcement_cmd: type[AlconnaMatcher] = on_alconna(
#     command=Alconna(
#         "测试milkybot发送群公告", Args["content", str]["image?", UniImage, None]
#     ),
#     aliases={"测试milkybot发送群公告", "测试milkybot群公告"},
#     priority=5,
#     block=True,
#     use_cmd_sep=True,
#     use_cmd_start=True,
# )


@send_group_announcement_cmd.handle()
async def milkybot_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    image_path = await _resolve_image_path(image) if image is not None else None
    impl_info = await bot.get_impl_info()

    match impl_info.impl_name:
        case "LLBot":
            if image is not None:
                await send_group_announcement_cmd.finish(
                    await _("协议端功能异常，等待上游修复")
                )
                return
        case _:
            await send_group_announcement_cmd.finish(await _("不支持的 Milky 实现"))
            return

    await run_group_action_milky(
        send_group_announcement_cmd,
        await _("发送群公告"),
        lambda: bot.send_group_announcement(
            group_id=event.data.peer_id,
            content=content,
            path=image_path,
        ),
        await _("群公告已发送"),
    )


async def onebot_v11_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: OneBot11,
    event: OneBBot11_GroupMessageEvent,
) -> None:
    image_path = await _resolve_image_path(image) if image is not None else None
    version_info = await bot.get_version_info()

    if version_info.get("data", {}).get("protocol_version") != "v11":
        await send_group_announcement_cmd.finish(await _("不支持的 OneBot 协议版本"))
    if version_info.get("status") != "ok":
        await send_group_announcement_cmd.finish(await _("OneBot 状态异常"))
    if version_info.get("retcode", -1) != 0:
        await send_group_announcement_cmd.finish(await _("OneBot 调用失败"))

    raw_version = version_info.get("data", {}).get("version", "0")
    try:
        current_version = parse(raw_version)
    except InvalidVersion:
        current_version = parse("0")

    app_name = version_info.get("data", {}).get("app_name")

    match app_name:
        case "LLOneBot" if current_version >= parse("7.12.0"):
            pass
        case "NapCat.Onebot" if current_version >= parse("4.18.0"):
            pass
        case _:
            await send_group_announcement_cmd.finish(await _("不支持的 OneBot 版本"))
            return

    await run_group_action_onebot11(
        send_group_announcement_cmd,
        await _("发送群公告"),
        lambda: bot.call_api(
            "_send_group_notice",
            group_id=event.group_id,
            content=content,
            image=image_path,
        ),
        await _("群公告已发送"),
    )


async def import_handle() -> Any:
    logger.debug(await _("导入announcement处理器..."))
