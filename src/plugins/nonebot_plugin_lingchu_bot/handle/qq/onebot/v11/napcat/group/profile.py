from pathlib import Path

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)


async def set_group_portrait_napcat(
    *,
    image_path: Path,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    await bot.call_api(
        "set_group_portrait",
        group_id=event.group_id,
        file=str(image_path),
    )
