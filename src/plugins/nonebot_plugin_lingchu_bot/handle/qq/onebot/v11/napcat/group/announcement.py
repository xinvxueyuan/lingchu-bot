from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)


async def send_group_notice_napcat(
    *,
    content: str,
    image_path: Path | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    await bot.call_api(
        "_send_group_notice",
        group_id=event.group_id,
        content=content,
        image=image_path,
    )
