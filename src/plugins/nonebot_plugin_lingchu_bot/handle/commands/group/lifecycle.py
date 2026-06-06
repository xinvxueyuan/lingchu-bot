from typing import Any

from arclet.alconna import Alconna
from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import on_alconna

from ....i18n import _async as _
from .common import run_group_action_onebot11

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
    """
    在当前群聊中使机器人退出该群组。

    Parameters:
        event (MilkyGroupMessageEvent): 包含目标群 ID 的群消息事件；
        使用 event.data.peer_id 作为要退出的群组 ID。

    Returns:
        Any: 操作执行结果，表示退出群组请求的处理结果（具体类型由运行时实现决定）。
    """
    await quit_group_cmd.send(
        group_id=event.data.peer_id,
        message=await _("退出当前群"),
    )
    await bot.quit_group(group_id=event.data.peer_id)


@quit_group_cmd.handle()
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


async def import_handle() -> Any:
    logger.debug(await _("导入lifecycle处理器..."))
