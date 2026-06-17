from pathlib import Path

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed


async def set_group_portrait_napcat(
    *,
    image_path: Path,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    """设置群头像（NapCat 实现）"""
    try:
        await bot.call_api(
            "set_group_portrait",
            group_id=event.group_id,
            file=str(image_path),
        )
    except OneBot11ActionFailed as e:
        logger.error(f"设置群头像失败: {e!r}")
        raise
