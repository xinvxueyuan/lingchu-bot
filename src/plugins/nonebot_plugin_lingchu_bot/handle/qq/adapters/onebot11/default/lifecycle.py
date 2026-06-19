from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.lifecycle import quit_group_cmd


@selected_adapter_handle(quit_group_cmd, "~onebot.v11", "leave_group")
async def onebot11_quit_group(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 1. 执行退出群操作
    try:
        await bot.set_group_leave(group_id=event.group_id, is_dismiss=False)
    except OneBot11ActionFailed as e:
        logger.error(f"退出群失败，操作被拒绝: {e!r}")
        return await quit_group_cmd.finish(await _("退出群失败，操作被拒绝"))

    # 2. 反馈结果
    return await quit_group_cmd.finish(await _("退出当前群"))
