"""Telegram group management handlers.

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

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....i18n import _async as _
from ....qq.commands.block import block_member_cmd, unblock_member_cmd
from ....qq.commands.common import selected_adapter_handle
from ....qq.commands.kick import kick_member_cmd
from ....qq.commands.lifecycle import quit_group_cmd
from ....qq.commands.member import (
    set_group_member_admin_cmd,
    unset_group_member_admin_cmd,
)
from ....qq.commands.profile import set_group_name_cmd
from .mute import _target_id


async def _finish_rejected(command: Any, operation: str, error: ActionFailed) -> Any:
    logger.error(f"Telegram {operation} rejected: {error!r}")
    message = await _("{operation}失败，操作被拒绝")
    return await command.finish(message.format(operation=operation))


@selected_adapter_handle(kick_member_cmd, "~telegram", "kick_member")
async def telegram_kick_member(
    user: At | int,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
    reason: str | None = None,
) -> Any:
    del session, reason
    target = _target_id(user)
    try:
        await bot.ban_chat_member(
            chat_id=event.chat.id,
            user_id=target,
            revoke_messages=False,
        )
        await bot.unban_chat_member(
            chat_id=event.chat.id,
            user_id=target,
            only_if_banned=True,
        )
    except ActionFailed as error:
        return await _finish_rejected(kick_member_cmd, "移出成员", error)
    return await kick_member_cmd.finish(await _("已移出群成员"))


@selected_adapter_handle(block_member_cmd, "~telegram", "block_member")
async def telegram_block_member(
    user: At | int,
    duration: int | None,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
    reason: str | None = None,
) -> Any:
    del session, reason
    until_date = int(time.time()) + duration if duration else None
    try:
        await bot.ban_chat_member(
            chat_id=event.chat.id,
            user_id=_target_id(user),
            until_date=until_date,
            revoke_messages=True,
        )
    except ActionFailed as error:
        return await _finish_rejected(block_member_cmd, "拉黑成员", error)
    return await block_member_cmd.finish(await _("已拉黑群成员"))


@selected_adapter_handle(unblock_member_cmd, "~telegram", "unblock_member")
async def telegram_unblock_member(
    user: At | int,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
    reason: str | None = None,
) -> Any:
    del session, reason
    try:
        await bot.unban_chat_member(
            chat_id=event.chat.id,
            user_id=_target_id(user),
            only_if_banned=True,
        )
    except ActionFailed as error:
        return await _finish_rejected(unblock_member_cmd, "解除拉黑", error)
    return await unblock_member_cmd.finish(await _("已解除群成员拉黑"))


async def _set_admin(
    bot: Bot,
    event: GroupMessageEvent,
    user: At | int,
    *,
    value: bool,
) -> None:
    await bot.promote_chat_member(
        chat_id=event.chat.id,
        user_id=_target_id(user),
        can_manage_chat=value,
        can_delete_messages=value,
        can_restrict_members=value,
        can_invite_users=value,
        can_pin_messages=value,
        can_manage_topics=value,
    )


@selected_adapter_handle(set_group_member_admin_cmd, "~telegram", "set_member_admin")
async def telegram_set_member_admin(
    user: At | int,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    try:
        await _set_admin(bot, event, user, value=True)
    except ActionFailed as error:
        return await _finish_rejected(set_group_member_admin_cmd, "设置管理员", error)
    return await set_group_member_admin_cmd.finish(await _("设置管理员成功"))


@selected_adapter_handle(
    unset_group_member_admin_cmd,
    "~telegram",
    "unset_member_admin",
)
async def telegram_unset_member_admin(
    user: At | int,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    try:
        await _set_admin(bot, event, user, value=False)
    except ActionFailed as error:
        return await _finish_rejected(unset_group_member_admin_cmd, "取消管理员", error)
    return await unset_group_member_admin_cmd.finish(await _("取消管理员成功"))


@selected_adapter_handle(set_group_name_cmd, "~telegram", "set_group_name")
async def telegram_set_group_name(
    new_group_name: str,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    try:
        await bot.set_chat_title(chat_id=event.chat.id, title=new_group_name)
    except ActionFailed as error:
        return await _finish_rejected(set_group_name_cmd, "设置群名称", error)
    return await set_group_name_cmd.finish(await _("设置群名称成功"))


@selected_adapter_handle(quit_group_cmd, "~telegram", "leave_group")
async def telegram_leave_group(
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    try:
        await bot.leave_chat(chat_id=event.chat.id)
    except ActionFailed as error:
        return await _finish_rejected(quit_group_cmd, "退出群组", error)
    return await quit_group_cmd.finish(await _("退出当前群"))
