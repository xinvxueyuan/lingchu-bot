from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

from ......i18n import _async as _
from ....commands.announcement import AnnouncementImagePath

# NapCat reports `retcode=1200` when the announcement `image` field is
# unreadable (file missing, bind mount misconfigured, path style mismatch).
# We treat the wording/message text as well so older NapCat builds that
# keep a similar human-readable hint still match.
_NAPCAT_IMAGE_RETCODE = 1200
_NAPCAT_IMAGE_HINTS = ("image", "image字段", "图片")


def _is_napcat_image_format_error(exc: OneBot11ActionFailed) -> bool:
    info: dict[str, Any] = getattr(exc, "info", {}) or {}
    if info.get("retcode") == _NAPCAT_IMAGE_RETCODE:
        return True
    haystack_parts = [
        str(info.get("message") or ""),
        str(info.get("wording") or ""),
        str(info.get("data") or ""),
    ]
    haystack = " ".join(haystack_parts).lower()
    return any(hint.lower() in haystack for hint in _NAPCAT_IMAGE_HINTS)


async def send_group_notice_napcat(
    *,
    content: str,
    group_id: int,
    image_path: AnnouncementImagePath | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    """发送群公告（NapCat 实现）"""
    try:
        if image_path is not None:
            await bot.call_api(
                "_send_group_notice",
                group_id=group_id,
                content=content,
                image=str(image_path.local_path),
            )
        else:
            await bot.call_api(
                "_send_group_notice",
                group_id=group_id,
                content=content,
            )
    except OneBot11ActionFailed as e:
        if image_path is not None and _is_napcat_image_format_error(e):
            template = await _(
                "NapCat 拒绝公告图片：已发送的 image 字段为 {local_path}。"
            )
            logger.warning(
                template.format(
                    local_path=str(image_path.local_path),
                )
            )
        logger.error(f"发送群公告失败: {e!r}")
        raise
