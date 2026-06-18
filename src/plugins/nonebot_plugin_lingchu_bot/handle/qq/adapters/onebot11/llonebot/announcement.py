from pathlib import Path

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed


async def send_group_notice_llonebot(
    *,
    content: str,
    image_path: Path | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    """发送群公告（LLOneBot 实现）"""
    try:
        await bot.call_api(
            "_send_group_notice",
            group_id=event.group_id,
            content=content,
            image=image_path,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"发送群公告失败: {e!r}")
        raise
