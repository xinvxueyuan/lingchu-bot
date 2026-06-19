import asyncio
import base64
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
    """设置群头像（NapCat 实现）

    NapCat 的 ``set_group_portrait`` API 要求 ``file`` 字段为 ``http(s)://``、
    ``base64://`` 或 ``file://`` 格式，裸本地路径会被拒绝（retcode=1200）。
    这里统一使用 ``base64://`` 编码，兼容 bot 与 NapCat 分属不同容器的部署。
    """
    raw_bytes = await asyncio.to_thread(image_path.read_bytes)
    file_field = "base64://" + base64.b64encode(raw_bytes).decode()
    try:
        await bot.call_api(
            "set_group_portrait",
            group_id=event.group_id,
            file=file_field,
        )
    except OneBot11ActionFailed as e:
        logger.error(f"设置群头像失败: {e!r}")
        raise
