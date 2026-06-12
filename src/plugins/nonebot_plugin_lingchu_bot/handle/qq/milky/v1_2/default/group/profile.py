from typing import Any

from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna.uniseg import Image as UniImage

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.profile import (
    _resolve_image_path,
    set_group_avatar_cmd,
    set_group_name_cmd,
)
from .common import run_group_action_milky


@selected_adapter_handle(set_group_name_cmd, "~milky")
async def milkybot_set_group_name(
    new_group_name: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
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


@selected_adapter_handle(set_group_avatar_cmd, "~milky")
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
