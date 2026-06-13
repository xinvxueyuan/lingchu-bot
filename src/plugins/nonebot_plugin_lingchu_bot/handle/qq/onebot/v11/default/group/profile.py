from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot_plugin_alconna.uniseg import Image as UniImage
from packaging.version import InvalidVersion, parse

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.profile import (
    _resolve_image_path,
    set_group_avatar_cmd,
    set_group_name_cmd,
)
from ...napcat.group.profile import set_group_portrait_napcat
from .common import run_group_action_onebot11


@selected_adapter_handle(set_group_name_cmd, "~onebot.v11")
async def onebot11_set_group_name(
    new_group_name: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    return await run_group_action_onebot11(
        set_group_name_cmd,
        await _("设置群名称"),
        lambda: bot.set_group_name(group_id=event.group_id, group_name=new_group_name),
        (await _("群名称已设置为: {new_group_name}")).format(
            new_group_name=new_group_name
        ),
    )


@selected_adapter_handle(set_group_avatar_cmd, "~onebot.v11")
async def onebot11_set_group_avatar(
    image: UniImage | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    image_path = await _resolve_image_path(image)
    if image_path is None:
        await set_group_avatar_cmd.finish(await _("请上传一张图片"))

    version_info = await bot.get_version_info()
    # OneBot V11 适配器解包响应，get_version_info() 直接返回 data 字段
    data = version_info.get("data", version_info)
    app_name = data.get("app_name")
    raw_version = data.get("app_version", "0")
    try:
        current_version = parse(raw_version)
    except InvalidVersion:
        current_version = parse("0")

    async def _set_portrait() -> None:
        await set_group_portrait_napcat(image_path=image_path, bot=bot, event=event)

    match app_name:
        case "NapCat.Onebot" if current_version >= parse("4.18.0"):
            action = _set_portrait
        case _:
            await set_group_avatar_cmd.finish(
                await _("当前 OneBot 实现不支持设置群头像")
            )
            return None

    return await run_group_action_onebot11(
        set_group_avatar_cmd,
        await _("设置群头像"),
        action,
        await _("群头像已更新"),
    )
