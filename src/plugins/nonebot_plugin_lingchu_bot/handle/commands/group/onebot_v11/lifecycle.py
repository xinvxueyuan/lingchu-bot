from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from .....i18n import _async as _
from ..common import selected_adapter_handle
from ..lifecycle import quit_group_cmd
from .common import run_group_action_onebot11


@selected_adapter_handle(quit_group_cmd, "~onebot.v11")
async def onebot11_quit_group(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    return await run_group_action_onebot11(
        quit_group_cmd,
        await _("退出当前群"),
        lambda: bot.set_group_leave(group_id=event.group_id, is_dismiss=False),
        await _("退出当前群"),
    )
