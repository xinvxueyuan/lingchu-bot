from typing import Any

from nonebot import logger
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.test import echo_cmd


@selected_adapter_handle(echo_cmd, "~milky")
async def milkybot_echo(
    event: MilkyGroupMessageEvent,
) -> Any:
    # 1. 获取原始消息
    raw_message = str(event.get_message())

    # 2. 输入数据清洗：去除首尾空白字符
    raw_message = raw_message.strip()

    # 3. 参数合法性检查
    if not raw_message:
        logger.warning("[echo] 收到空消息，跳过回显")
        return await echo_cmd.finish(await _("消息内容为空，无法回显"))

    # 4. 记录日志并执行回显
    logger.info(f"[echo] 收到原始消息: {raw_message}")
    return await echo_cmd.finish(message=raw_message)
