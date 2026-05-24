from typing import Any

from arclet.alconna import Alconna
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import on_alconna

from ....i18n import _async as _
from .common import run_group_action

quit_group_cmd: type[Matcher] = on_alconna(
    command=Alconna("退出群"),
    aliases={"退群", "退出当前群"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@quit_group_cmd.handle()
async def milkybot_quit_group(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    return await run_group_action(
        quit_group_cmd,
        await _("退出群"),
        lambda: bot.quit_group(group_id=event.data.peer_id),
        await _("已退出当前群"),
    )
