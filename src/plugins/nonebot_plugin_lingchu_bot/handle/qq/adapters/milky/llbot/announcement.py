from pathlib import Path

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError


async def send_group_announcement_llbot(
    *,
    content: str,
    image_path: Path | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    """发送群公告（Milky/llbot 实现）"""
    try:
        await bot.send_group_announcement(
            group_id=event.data.peer_id,
            content=content,
            path=image_path,
        )
    except (ActionFailed, NetworkError) as e:
        logger.error(f"发送群公告失败: {e!r}")
        raise
