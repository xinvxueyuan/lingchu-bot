from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError

from ......i18n import _async as _
from ....commands.common import selected_adapter_handle
from ....commands.lifecycle import quit_group_cmd


@selected_adapter_handle(quit_group_cmd, "~milky")
async def milkybot_quit_group(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    # 1. 发送退出消息
    try:
        await quit_group_cmd.send(
            group_id=event.data.peer_id,
            message=await _("退出当前群"),
        )
    except (NetworkError, ActionFailed) as e:
        logger.warning(f"发送退出消息失败: {e!r}")
        # 继续执行退出操作，不中断

    # 2. 执行退出群操作
    try:
        await bot.quit_group(group_id=event.data.peer_id)
    except NetworkError as e:
        logger.error(f"退出群失败，网络异常: {e!r}")
        return await quit_group_cmd.finish(await _("退出群失败，网络异常"))
    except ActionFailed as e:
        logger.error(f"退出群失败，操作被拒绝: {e!r}")
        return await quit_group_cmd.finish(await _("退出群失败，操作被拒绝"))

    # 3. 反馈结果
    return await quit_group_cmd.finish(await _("退出当前群"))
