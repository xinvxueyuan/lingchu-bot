from typing import Any

from nonebot import logger
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent

from ..common import selected_adapter_handle
from ..test import echo_cmd


@selected_adapter_handle(echo_cmd, "~milky")
async def milkybot_echo(
    event: MilkyGroupMessageEvent,
) -> Any:
    raw_message = str(event.get_message())
    logger.info(f"[echo] 收到原始消息: {raw_message}")
    return await echo_cmd.finish(message=raw_message)
