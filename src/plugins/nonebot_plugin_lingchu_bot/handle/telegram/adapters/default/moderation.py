"""Telegram group management handlers.

Note: do NOT add `from __future__ import annotations` here. NoneBot resolves
handler signature forward refs via the wrapper's __globals__ (common.py), which
cannot see GroupMessageEvent. Use real type objects like the OneBot V11 siblings.
"""

import time
from typing import Any, Final

from nonebot import get_driver, logger, require
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import GroupMessageEvent
from nonebot.adapters.telegram.exception import ActionFailed, NetworkError

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....core.config import get_handle_config_manager
from .....database.orm_crud import DatabaseError
from .....i18n import _async as _
from .....repositories.blocklist import (
    BlocklistUpsert,
    expires_at_from_duration,
    find_active_block,
    remove_block,
    upsert_block,
)
from .....repositories.message_store import AuditEvent, record_api_call
from ....qq.adapters.onebot11.default.common import CommandAudit
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

TELEGRAM_PLATFORM_ID: Final = "telegram"
TELEGRAM_ADAPTER_ID: Final = "~telegram"


def _telegram_bot_id(bot: Bot) -> str:
    return str(getattr(bot, "self_id", ""))


def _telegram_member_field(member: Any, name: str) -> Any:
    """Read a member field from either a dict or an object response."""
    if isinstance(member, dict):
        return member.get(name)
    return getattr(member, name, None)


def _telegram_member_status(member: Any) -> str:
    value = _telegram_member_field(member, "status")
    return value if isinstance(value, str) else ""


def _telegram_is_superuser(user_id: int) -> bool:
    superusers = getattr(getattr(get_driver(), "config", None), "superusers", ())
    text_id = str(user_id)
    configured = {str(value) for value in superusers}
    # NoneBot 2.5 supports both plain IDs and adapter-prefixed entries such as
    # "telegram:123456789"; match both so prefixed superusers are honored.
    return text_id in configured or f"telegram:{text_id}" in configured


def _normalized_block_duration(duration: Any) -> int | None:
    """Normalize a configured block duration for Telegram.

    TOML values may be strings or invalid types; coerce them to seconds and
    return None (permanent) when the value is not a positive number. Telegram
    treats until_date values less than 30 seconds in the future as a permanent
    ban, so positive durations are raised to a 30-second minimum to keep the
    local expires_at consistent with the actual ban behavior.
    """
    if isinstance(duration, bool):
        return None
    if isinstance(duration, str):
        text = duration.strip()
        try:
            value = int(text)
        except ValueError:
            return None
    elif isinstance(duration, int):
        value = duration
    else:
        return None
    if value <= 0:
        return None
    return max(value, 30)


async def _finish_database_error(
    command: Any, operation: str, error: DatabaseError
) -> Any:
    logger.error("Telegram %s database operation failed: %r", operation, error)
    message = await _("{operation}失败，数据库异常")
    return await command.finish(message.format(operation=operation))


async def _rollback_session(session: async_scoped_session) -> None:
    await session.rollback()


async def _check_telegram_bot_privilege(
    bot: Bot,
    event: GroupMessageEvent,
    command: Any,
) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=event.chat.id,
            user_id=int(bot.self_id),
        )
    except (ActionFailed, NetworkError) as error:
        await _finish_rejected(command, "验证机器人权限", error)
        return False

    status = _telegram_member_status(member)
    if status == "creator":
        return True
    if status != "administrator" or not bool(
        _telegram_member_field(member, "can_restrict_members")
    ):
        await command.finish(await _("机器人缺少管理员权限"))
        return False
    return True


async def _check_telegram_admin_target_privilege(
    bot: Bot,
    event: GroupMessageEvent,
    operator_user_id: int,
    command: Any,
) -> bool:
    try:
        operator_member = await bot.get_chat_member(
            chat_id=event.chat.id,
            user_id=operator_user_id,
        )
    except (ActionFailed, NetworkError) as error:
        await _finish_rejected(command, "验证操作权限", error)
        return False

    if _telegram_member_status(operator_member) == "creator" or _telegram_is_superuser(
        operator_user_id
    ):
        return True
    await command.finish(await _("目标用户权限过高，无法执行"))
    return False


async def _check_telegram_target_privilege(
    bot: Bot,
    event: GroupMessageEvent,
    target_user_id: int,
    command: Any,
    action: str,
) -> bool:
    operator_user_id = int(event.from_.id)
    try:
        bot_user_id = int(bot.self_id)
    except (TypeError, ValueError):
        bot_user_id = None
    if target_user_id in (operator_user_id, bot_user_id):
        message_key = (
            "不能{action}自己"
            if target_user_id == operator_user_id
            else "不能{action}机器人"
        )
        message = await _(message_key)
        await command.finish(message.format(action=action))
        return False

    try:
        target_member = await bot.get_chat_member(
            chat_id=event.chat.id,
            user_id=target_user_id,
        )
    except (ActionFailed, NetworkError) as error:
        await _finish_rejected(command, "验证目标用户权限", error)
        return False

    target_status = _telegram_member_status(target_member)
    if target_status == "creator":
        await command.finish(await _("目标用户权限过高，无法执行"))
        return False
    if target_status == "administrator":
        return await _check_telegram_admin_target_privilege(
            bot,
            event,
            operator_user_id,
            command,
        )
    return True


async def _record_telegram_audit(
    session: async_scoped_session,
    bot: Bot,
    event: GroupMessageEvent,
    audit: CommandAudit,
) -> None:
    audit_group_id = audit.group_id if audit.group_id is not None else event.chat.id
    data_summary = (
        f"operator={event.from_.id}, target={audit.target_user_id}, "
        f"action={audit.action}, group={audit_group_id}"
    )
    if audit.duration is not None:
        data_summary += f", duration={audit.duration}"
    if audit.reason is not None:
        data_summary += f", reason={audit.reason}"

    try:
        await record_api_call(
            session,
            AuditEvent(
                platform_id=TELEGRAM_PLATFORM_ID,
                adapter_id=TELEGRAM_ADAPTER_ID,
                protocol_id=None,
                bot_id=_telegram_bot_id(bot),
                api_name=f"command:{audit.action}",
                data_summary=data_summary,
                result_summary="success",
                exception_summary=None,
                audit_type="command",
            ),
        )
    except DatabaseError:
        logger.exception("记录 Telegram 命令审计失败: action=%s", audit.action)


async def _finish_rejected(
    command: Any,
    operation: str,
    error: ActionFailed | NetworkError,
) -> Any:
    logger.error("Telegram %s rejected: %r", operation, error)
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
    target = _target_id(user)
    if not await _check_telegram_target_privilege(
        bot, event, target, kick_member_cmd, "踢出"
    ):
        return None
    try:
        entry = await find_active_block(
            session,
            platform_id=TELEGRAM_PLATFORM_ID,
            adapter_id=TELEGRAM_ADAPTER_ID,
            bot_id=_telegram_bot_id(bot),
            group_id=event.chat.id,
            user_id=target,
        )
    except DatabaseError as error:
        return await _finish_database_error(kick_member_cmd, "查询黑名单", error)
    if entry is None:
        message = await _("用户 {user} 不在黑名单中，无法执行踢出操作")
        return await kick_member_cmd.finish(message.format(user=target))
    if not await _check_telegram_bot_privilege(bot, event, kick_member_cmd):
        return None
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
    except (ActionFailed, NetworkError) as error:
        return await _finish_rejected(kick_member_cmd, "移出成员", error)
    await _record_telegram_audit(
        session,
        bot,
        event,
        CommandAudit(action="kick_member", target_user_id=target, reason=reason),
    )
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
    config = await get_handle_config_manager().get_config("block_member")
    if not config.enabled:
        return await block_member_cmd.finish(await _("该功能已禁用"))
    actual_duration = _normalized_block_duration(
        duration if duration is not None else config.defaults.get("block_duration")
    )
    default_reason = config.defaults.get("default_reason", "违反群规")
    reason_text = reason if reason is not None else await _(default_reason)
    target = _target_id(user)
    if not await _check_telegram_target_privilege(
        bot, event, target, block_member_cmd, "拉黑"
    ):
        return None
    if not await _check_telegram_bot_privilege(bot, event, block_member_cmd):
        return None
    try:
        await upsert_block(
            session,
            BlocklistUpsert(
                platform_id=TELEGRAM_PLATFORM_ID,
                adapter_id=TELEGRAM_ADAPTER_ID,
                bot_id=_telegram_bot_id(bot),
                scope="group",
                group_id=event.chat.id,
                user_id=target,
                operator_id=event.from_.id,
                reason=reason_text,
                expires_at=expires_at_from_duration(actual_duration),
            ),
        )
        await bot.ban_chat_member(
            chat_id=event.chat.id,
            user_id=target,
            until_date=(
                int(time.time()) + actual_duration if actual_duration else None
            ),
            revoke_messages=True,
        )
    except (ActionFailed, NetworkError) as error:
        await _rollback_session(session)
        return await _finish_rejected(block_member_cmd, "拉黑成员", error)
    except DatabaseError as error:
        await _rollback_session(session)
        return await _finish_database_error(block_member_cmd, "拉黑成员", error)
    await _record_telegram_audit(
        session,
        bot,
        event,
        CommandAudit(
            action="block_member",
            target_user_id=target,
            duration=actual_duration,
            reason=reason_text,
        ),
    )
    return await block_member_cmd.finish(await _("已拉黑群成员"))


@selected_adapter_handle(unblock_member_cmd, "~telegram", "unblock_member")
async def telegram_unblock_member(
    user: At | int,
    bot: Bot,
    event: GroupMessageEvent,
    session: async_scoped_session,
    reason: str | None = None,
) -> Any:
    reason_text = reason if reason is not None else await _("管理员操作「默认」")
    target = _target_id(user)
    if not await _check_telegram_bot_privilege(bot, event, unblock_member_cmd):
        return None
    try:
        await remove_block(
            session,
            platform_id=TELEGRAM_PLATFORM_ID,
            adapter_id=TELEGRAM_ADAPTER_ID,
            bot_id=_telegram_bot_id(bot),
            scope="group",
            group_id=event.chat.id,
            user_id=target,
        )
        await bot.unban_chat_member(
            chat_id=event.chat.id,
            user_id=target,
            only_if_banned=True,
        )
    except (ActionFailed, NetworkError) as error:
        await _rollback_session(session)
        return await _finish_rejected(unblock_member_cmd, "解除拉黑", error)
    except DatabaseError as error:
        await _rollback_session(session)
        return await _finish_database_error(unblock_member_cmd, "解除拉黑", error)
    await _record_telegram_audit(
        session,
        bot,
        event,
        CommandAudit(
            action="unblock_member",
            target_user_id=target,
            reason=reason_text,
        ),
    )
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
