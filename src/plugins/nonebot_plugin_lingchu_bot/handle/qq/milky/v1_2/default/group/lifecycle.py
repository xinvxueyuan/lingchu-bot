from typing import Any

from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.lifecycle import quit_group_cmd


@selected_adapter_handle(quit_group_cmd, "~milky")
async def milkybot_quit_group(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    await quit_group_cmd.send(
        group_id=event.data.peer_id,
        message=await _("退出当前群"),
    )
    await bot.quit_group(group_id=event.data.peer_id)
