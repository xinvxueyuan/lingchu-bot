from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from .....group.common import selected_adapter_handle
from .....group.test import echo_cmd


@selected_adapter_handle(echo_cmd, "~onebot.v11")
async def onebot11_echo(
    event: OneBot11GroupMessageEvent,
) -> Any:
    raw_message = str(event.get_message())
    logger.info(f"[echo] 收到原始消息: {raw_message}")
    return await echo_cmd.finish(message=raw_message)
