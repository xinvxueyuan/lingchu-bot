from pathlib import Path

from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent


async def send_group_announcement_llbot(
    *,
    content: str,
    image_path: Path | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    await bot.send_group_announcement(
        group_id=event.data.peer_id,
        content=content,
        path=image_path,
    )
