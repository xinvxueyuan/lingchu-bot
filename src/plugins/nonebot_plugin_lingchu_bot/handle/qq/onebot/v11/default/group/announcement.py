from nonebot.adapters.onebot.v11 import Bot as OneBot11
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBBot11_GroupMessageEvent,
)
from nonebot_plugin_alconna.uniseg import Image as UniImage
from packaging.version import InvalidVersion, parse

from .......i18n import _async as _
from .....group.announcement import _resolve_image_path, send_group_announcement_cmd
from .....group.common import selected_adapter_handle
from ...llonebot.group.announcement import send_group_notice_llonebot
from ...napcat.group.announcement import send_group_notice_napcat
from .common import run_group_action_onebot11


@selected_adapter_handle(send_group_announcement_cmd, "~onebot.v11")
async def onebot_v11_send_group_announcement(
    content: str,
    image: UniImage | None,
    bot: OneBot11,
    event: OneBBot11_GroupMessageEvent,
) -> None:
    image_path = await _resolve_image_path(image) if image is not None else None
    version_info = await bot.get_version_info()
    # OneBot V11 适配器解包响应，get_version_info() 直接返回 data 字段
    data = version_info.get("data", version_info)

    if data.get("protocol_version") != "v11":
        await send_group_announcement_cmd.finish(await _("不支持的 OneBot 协议版本"))

    raw_version = data.get("app_version", "0")
    try:
        current_version = parse(raw_version)
    except InvalidVersion:
        current_version = parse("0")

    app_name = data.get("app_name")

    match app_name:
        case "LLOneBot" if current_version >= parse("7.12.0"):
            action = send_group_notice_llonebot
        case "NapCat.Onebot" if current_version >= parse("4.18.0"):
            action = send_group_notice_napcat
        case _:
            await send_group_announcement_cmd.finish(await _("不支持的 OneBot 版本"))
            return

    await run_group_action_onebot11(
        send_group_announcement_cmd,
        await _("发送群公告"),
        lambda: action(
            content=content,
            image_path=image_path,
            bot=bot,
            event=event,
        ),
        await _("群公告已发送"),
    )
