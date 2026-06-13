from typing import Any

from nonebot import logger, on_message, on_request
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.event import (
    GroupRequestEvent as OneBot11GroupRequestEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
from nonebot_plugin_alconna.uniseg import At

from .......database.orm_crud import DatabaseError
from .......i18n import _async as _
from .......repositories.blocklist import (
    BlockScope,
    clear_blocklist,
    expires_at_from_duration,
    find_active_block,
    remove_block,
    upsert_block,
)
from .....group.block import (
    block_member_cmd,
    clear_blocklist_cmd,
    global_block_member_cmd,
    global_clear_blocklist_cmd,
    global_unblock_member_cmd,
    unblock_member_cmd,
)
from .....group.common import selected_adapter_handle
from .common import (
    finish_action_error_onebot11,
    target_user_onebot11,
)

QQ_PLATFORM_ID = "qq"
ONEBOT_V11_ADAPTER_ID = "~onebot.v11"

blocklisted_message = on_message(priority=1, block=False)
blocklisted_group_request = on_request(priority=1, block=False)


def _bot_id(bot: OneBot11Bot) -> str:
    return str(getattr(bot, "self_id", ""))


async def _default_block_reason(reason: str | None) -> str:
    return await _("违反群规「默认」") if reason is None else reason


async def _default_admin_reason(reason: str | None) -> str:
    return await _("管理员操作「默认」") if reason is None else reason


async def _store_block(  # noqa: PLR0913
    *,
    scope: BlockScope,
    user_id: int,
    duration: int | None,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    await upsert_block(
        platform_id=QQ_PLATFORM_ID,
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        bot_id=_bot_id(bot),
        scope=scope,
        group_id=event.group_id,
        user_id=user_id,
        operator_id=event.user_id,
        reason=reason,
        expires_at=expires_at_from_duration(duration),
    )


async def _finish_database_error(
    command: Any, operation: str, error: DatabaseError
) -> Any:
    logger.error(f"{operation}失败，数据库异常: {error!r}")
    return await command.finish(
        message=(await _("{operation}失败，数据库异常: {error!r}")).format(
            operation=operation,
            error=error,
        )
    )


async def _kick_blocked_user(
    bot: OneBot11Bot,
    group_id: int,
    user_id: int,
) -> None:
    await bot.set_group_kick(
        group_id=group_id,
        user_id=user_id,
        reject_add_request=True,
    )


async def _block_member(  # noqa: PLR0913
    *,
    command: Any,
    scope: BlockScope,
    user: At,
    duration: int | None,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = await target_user_onebot11(user, bot, event)
    reason_text = await _default_block_reason(reason)
    try:
        await _store_block(
            scope=scope,
            user_id=target_user_id,
            duration=duration,
            reason=reason_text,
            bot=bot,
            event=event,
        )
        await _kick_blocked_user(bot, event.group_id, target_user_id)
    except DatabaseError as error:
        return await _finish_database_error(command, await _("拉黑"), error)
    except OneBot11ActionFailed as error:
        return await finish_action_error_onebot11(command, await _("拉黑"), error)

    scope_text = await _("全局") if scope == "global" else await _("本群")
    duration_text = await _("永久") if duration is None else f"{duration} 秒"
    name_display = f"@{target_name}" if target_name else str(target_user_id)
    message = (
        await _(
            "已拉黑并踢出: \n"
            "范围: {scope}\n"
            "名称: {name_display}\n"
            "时长: {duration}\n"
            "原因: {reason}\n"
            "标识: {target_user_id}"
        )
    ).format(
        scope=scope_text,
        name_display=name_display,
        duration=duration_text,
        reason=reason_text,
        target_user_id=target_user_id,
    )
    logger.info(message)
    return await command.finish(message=message)


@selected_adapter_handle(block_member_cmd, "~onebot.v11")
async def onebot11_block_member(
    user: At,
    duration: int | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _block_member(
        command=block_member_cmd,
        scope="group",
        user=user,
        duration=duration,
        reason=reason,
        bot=bot,
        event=event,
    )


@selected_adapter_handle(global_block_member_cmd, "~onebot.v11")
async def onebot11_global_block_member(
    user: At,
    duration: int | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _block_member(
        command=global_block_member_cmd,
        scope="global",
        user=user,
        duration=duration,
        reason=reason,
        bot=bot,
        event=event,
    )


async def _unblock_member(  # noqa: PLR0913
    *,
    command: Any,
    scope: BlockScope,
    user: At,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = await target_user_onebot11(user, bot, event)
    reason_text = await _default_admin_reason(reason)
    try:
        result = await remove_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=_bot_id(bot),
            scope=scope,
            group_id=event.group_id,
            user_id=target_user_id,
        )
        deleted = result[0]
    except DatabaseError as error:
        return await _finish_database_error(command, await _("删黑"), error)

    scope_text = await _("全局") if scope == "global" else await _("本群")
    name_display = f"@{target_name}" if target_name else str(target_user_id)
    message = (
        await _(
            "已删黑: \n"
            "范围: {scope}\n"
            "名称: {name_display}\n"
            "原因: {reason}\n"
            "标识: {target_user_id}\n"
            "删除记录: {deleted}"
        )
    ).format(
        scope=scope_text,
        name_display=name_display,
        reason=reason_text,
        target_user_id=target_user_id,
        deleted=deleted,
    )
    logger.info(message)
    return await command.finish(message=message)


@selected_adapter_handle(unblock_member_cmd, "~onebot.v11")
async def onebot11_unblock_member(
    user: At,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _unblock_member(
        command=unblock_member_cmd,
        scope="group",
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )


@selected_adapter_handle(global_unblock_member_cmd, "~onebot.v11")
async def onebot11_global_unblock_member(
    user: At,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _unblock_member(
        command=global_unblock_member_cmd,
        scope="global",
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )


async def _clear_blocklist(
    *,
    command: Any,
    scope: BlockScope,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    reason_text = await _default_admin_reason(reason)
    try:
        result = await clear_blocklist(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=_bot_id(bot),
            scope=scope,
            group_id=event.group_id,
        )
        deleted = result[0]
    except DatabaseError as error:
        return await _finish_database_error(command, await _("清空黑名单"), error)

    scope_text = await _("全局") if scope == "global" else await _("本群")
    message = (
        await _("已清空黑名单: \n范围: {scope}\n原因: {reason}\n删除记录: {deleted}")
    ).format(scope=scope_text, reason=reason_text, deleted=deleted)
    logger.info(message)
    return await command.finish(message=message)


@selected_adapter_handle(clear_blocklist_cmd, "~onebot.v11")
async def onebot11_clear_blocklist(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _clear_blocklist(
        command=clear_blocklist_cmd,
        scope="group",
        reason=reason,
        bot=bot,
        event=event,
    )


@selected_adapter_handle(global_clear_blocklist_cmd, "~onebot.v11")
async def onebot11_global_clear_blocklist(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _clear_blocklist(
        command=global_clear_blocklist_cmd,
        scope="global",
        reason=reason,
        bot=bot,
        event=event,
    )


@blocklisted_message.handle()
async def onebot11_kick_blocklisted_message(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> None:
    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=_bot_id(bot),
            group_id=event.group_id,
            user_id=event.user_id,
        )
        if entry is None:
            return
        await _kick_blocked_user(bot, event.group_id, event.user_id)
    except DatabaseError as error:
        logger.error(f"检查黑名单失败，数据库异常: {error!r}")
    except OneBot11ActionFailed as error:
        logger.error(f"黑名单成员踢出失败，操作被拒绝: {error!r}")


@blocklisted_group_request.handle()
async def onebot11_reject_blocklisted_group_request(
    bot: OneBot11Bot,
    event: OneBot11GroupRequestEvent,
) -> None:
    if event.sub_type != "add":
        return
    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=_bot_id(bot),
            group_id=event.group_id,
            user_id=event.user_id,
        )
        if entry is None:
            return
        reason = entry.reason or await _default_block_reason(None)
        await bot.set_group_add_request(
            flag=event.flag,
            sub_type=event.sub_type,
            approve=False,
            reason=reason,
        )
    except DatabaseError as error:
        logger.error(f"检查加群请求黑名单失败，数据库异常: {error!r}")
    except OneBot11ActionFailed as error:
        logger.error(f"拒绝黑名单成员加群失败，操作被拒绝: {error!r}")
