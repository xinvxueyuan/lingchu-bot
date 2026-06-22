from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

from ....commands.announcement import AnnouncementImagePath


async def send_group_notice_napcat(
    *,
    content: str,
    group_id: int,
    image_path: AnnouncementImagePath | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,  # noqa: ARG001
) -> None:
    """发送群公告（NapCat 实现）"""
    try:
        if image_path is not None:
            await bot.call_api(
                "_send_group_notice",
                group_id=group_id,
                content=content,
                image=image_path.protocol_path or str(image_path.local_path),
            )
        else:
            await bot.call_api(
                "_send_group_notice",
                group_id=group_id,
                content=content,
            )
    except OneBot11ActionFailed as e:
        logger.error(f"发送群公告失败: {e!r}")
        raise
