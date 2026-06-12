from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.profile import set_group_name_cmd
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
