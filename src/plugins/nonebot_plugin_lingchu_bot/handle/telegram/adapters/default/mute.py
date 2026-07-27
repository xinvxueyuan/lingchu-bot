"""Telegram moderation handlers.

Note: do NOT add `from __future__ import annotations` here. NoneBot resolves
handler signature forward refs via the wrapper's __globals__ (common.py), which
cannot see GroupMessageEvent. Use real type objects like the OneBot V11 siblings.
"""

import time
from typing import Any

from nonebot import logger, require
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import GroupMessageEvent
from nonebot.adapters.telegram.exception import ActionFailed
from nonebot.adapters.telegram.model import ChatPermissions

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....core.config import get_handle_config_manager
from .....i18n import _async as _
from ....qq.commands.common import selected_adapter_handle
from ....qq.commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)

MUTE_DURATION_MIN = 1
MUTE_DURATION_MAX = 30 * 24 * 60 * 60


def _target_id(user: At | int) -> int:
    value = user.target if isinstance(user, At) else user
    return int(value)


def _send_permissions(*, allowed: bool) -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=allowed,
        can_send_audios=allowed,
        can_send_documents=allowed,
        can_send_photos=allowed,
        can_send_videos=allowed,
        can_send_video_notes=allowed,
        can_send_voice_notes=allowed,
        can_send_polls=allowed,
        can_send_other_messages=allowed,
        can_add_web_page_previews=allowed,
    )


@selected_adapter_handle(member_mute_cmd, "~telegram", "member_mute")
async def telegram_mute(
    user: At | int,
    duration: int | None,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
    reason: str | None = None,
) -> Any:
    del session, reason
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await member_mute_cmd.finish(await _("该功能已禁用"))
    actual_duration = duration or int(config.defaults.get("mute_duration", 300))
    if not MUTE_DURATION_MIN <= actual_duration <= MUTE_DURATION_MAX:
        return await member_mute_cmd.finish(await _("禁言时长超出允许范围"))
    target = _target_id(user)
    if target in {event.from_.id, int(bot.self_id)}:
        return await member_mute_cmd.finish(await _("不能禁言自己或机器人"))
    try:
        await bot.restrict_chat_member(
            chat_id=event.chat.id,
            user_id=target,
            permissions=_send_permissions(allowed=False),
            until_date=int(time.time()) + actual_duration,
        )
    except ActionFailed as error:
        logger.error(f"Telegram mute rejected: {error!r}")
        return await member_mute_cmd.finish(await _("禁言失败，操作被拒绝"))
    return await member_mute_cmd.finish(await _("禁言成功"))


@selected_adapter_handle(member_unmute_cmd, "~telegram", "member_unmute")
async def telegram_unmute(
    user: At | int,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await member_unmute_cmd.finish(await _("该功能已禁用"))
    try:
        await bot.restrict_chat_member(
            chat_id=event.chat.id,
            user_id=_target_id(user),
            permissions=_send_permissions(allowed=True),
        )
    except ActionFailed as error:
        logger.error(f"Telegram unmute rejected: {error!r}")
        return await member_unmute_cmd.finish(await _("解禁失败，操作被拒绝"))
    return await member_unmute_cmd.finish(await _("解禁成功"))


async def _set_whole_mute(
    bot: Bot,
    event: GroupMessageEvent,
    *,
    muted: bool,
) -> None:
    await bot.set_chat_permissions(
        chat_id=event.chat.id,
        permissions=_send_permissions(allowed=not muted),
    )


@selected_adapter_handle(whole_mute_cmd, "~telegram", "whole_mute")
async def telegram_whole_mute(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await whole_mute_cmd.finish(await _("该功能已禁用"))
    try:
        await _set_whole_mute(bot, event, muted=True)
    except ActionFailed as error:
        logger.error(f"Telegram whole mute rejected: {error!r}")
        return await whole_mute_cmd.finish(await _("全体禁言失败，操作被拒绝"))
    return await whole_mute_cmd.finish(await _("全体禁言成功"))


@selected_adapter_handle(whole_unmute_cmd, "~telegram", "whole_unmute")
async def telegram_whole_unmute(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    config = await get_handle_config_manager().get_config("member_mute")
    if not config.enabled:
        return await whole_unmute_cmd.finish(await _("该功能已禁用"))
    try:
        await _set_whole_mute(bot, event, muted=False)
    except ActionFailed as error:
        logger.error(f"Telegram whole unmute rejected: {error!r}")
        return await whole_unmute_cmd.finish(await _("全体解禁失败，操作被拒绝"))
    return await whole_unmute_cmd.finish(await _("全体解禁成功"))
