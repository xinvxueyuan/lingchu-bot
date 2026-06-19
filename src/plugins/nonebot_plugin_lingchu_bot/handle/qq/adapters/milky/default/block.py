from typing import Any

from nonebot import logger, on_message, on_request
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import (
    GroupJoinRequestEvent as MilkyGroupJoinRequestEvent,
)
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed as MilkyActionFailed
from nonebot.adapters.milky.exception import NetworkError as MilkyNetworkError
from nonebot_plugin_alconna.uniseg import At

from ......database.orm_crud import DatabaseError
from ......i18n import _async as _
from ......repositories.blocklist import (
    BlockScope,
    clear_blocklist,
    expires_at_from_duration,
    find_active_block,
    remove_block,
    upsert_block,
)
from ....commands.block import (
    block_member_cmd,
    clear_blocklist_cmd,
    global_block_member_cmd,
    global_clear_blocklist_cmd,
    global_unblock_member_cmd,
    unblock_member_cmd,
)
from ....commands.common import selected_adapter_handle
from .common import (
    finish_action_error_milky,
    resolve_user_milky,
)

QQ_PLATFORM_ID = "qq"
MILKY_ADAPTER_ID = "~milky"

blocklisted_message = on_message(priority=1, block=False)
blocklisted_group_request = on_request(priority=1, block=False)


def _bot_id(bot: MilkyBot) -> str:
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
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    await upsert_block(
        platform_id=QQ_PLATFORM_ID,
        adapter_id=MILKY_ADAPTER_ID,
        bot_id=_bot_id(bot),
        scope=scope,
        group_id=event.data.peer_id,
        user_id=user_id,
        operator_id=event.data.sender.user_id,
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
    bot: MilkyBot,
    group_id: int,
    user_id: int,
) -> None:
    await bot.kick_group_member(
        group_id=group_id,
        user_id=user_id,
        reject_add_request=False,
    )


async def _block_member(  # noqa: PLR0913
    *,
    command: Any,
    scope: BlockScope,
    user: At | int,
    duration: int | None,
    reason: str | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = await resolve_user_milky(user, bot, event)
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
        await _kick_blocked_user(bot, event.data.peer_id, target_user_id)
    except DatabaseError as error:
        return await _finish_database_error(command, await _("拉黑"), error)
    except (MilkyActionFailed, MilkyNetworkError) as error:
        return await finish_action_error_milky(command, await _("拉黑"), error)

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


@selected_adapter_handle(block_member_cmd, "~milky", "block_member")
async def milkybot_block_member(
    user: At | int,
    duration: int | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
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


@selected_adapter_handle(global_block_member_cmd, "~milky", "global_block_member")
async def milkybot_global_block_member(
    user: At | int,
    duration: int | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
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
    user: At | int,
    reason: str | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = await resolve_user_milky(user, bot, event)
    reason_text = await _default_admin_reason(reason)
    try:
        result = await remove_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=MILKY_ADAPTER_ID,
            bot_id=_bot_id(bot),
            scope=scope,
            group_id=event.data.peer_id,
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


@selected_adapter_handle(unblock_member_cmd, "~milky", "unblock_member")
async def milkybot_unblock_member(
    user: At | int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
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


@selected_adapter_handle(global_unblock_member_cmd, "~milky", "global_unblock_member")
async def milkybot_global_unblock_member(
    user: At | int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
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
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    reason_text = await _default_admin_reason(reason)
    try:
        result = await clear_blocklist(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=MILKY_ADAPTER_ID,
            bot_id=_bot_id(bot),
            scope=scope,
            group_id=event.data.peer_id,
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


@selected_adapter_handle(clear_blocklist_cmd, "~milky", "clear_blocklist")
async def milkybot_clear_blocklist(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    return await _clear_blocklist(
        command=clear_blocklist_cmd,
        scope="group",
        reason=reason,
        bot=bot,
        event=event,
    )


@selected_adapter_handle(
    global_clear_blocklist_cmd,
    "~milky",
    "global_clear_blocklist",
)
async def milkybot_global_clear_blocklist(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
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
async def milkybot_kick_blocklisted_message(
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> None:
    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=MILKY_ADAPTER_ID,
            bot_id=_bot_id(bot),
            group_id=event.data.peer_id,
            user_id=event.data.sender.user_id,
        )
        if entry is None:
            return
        await _kick_blocked_user(bot, event.data.peer_id, event.data.sender.user_id)
    except DatabaseError as error:
        logger.error(f"检查黑名单失败，数据库异常: {error!r}")
    except (MilkyActionFailed, MilkyNetworkError) as error:
        logger.error(f"黑名单成员踢出失败，操作被拒绝: {error!r}")


@blocklisted_group_request.handle()
async def milkybot_reject_blocklisted_group_request(
    bot: MilkyBot,
    event: MilkyGroupJoinRequestEvent,
) -> None:
    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=MILKY_ADAPTER_ID,
            bot_id=_bot_id(bot),
            group_id=event.data.group_id,
            user_id=event.data.initiator_id,
        )
        if entry is None:
            return
        reason = entry.reason or await _default_block_reason(None)
        await bot.reject_group_request(
            notification_seq=event.data.notification_seq,
            notification_type="join_request",
            group_id=event.data.group_id,
            is_filtered=event.data.is_filtered,
            reason=reason,
        )
    except DatabaseError as error:
        logger.error(f"检查加群请求黑名单失败，数据库异常: {error!r}")
    except (MilkyActionFailed, MilkyNetworkError) as error:
        logger.error(f"拒绝黑名单成员加群失败，操作被拒绝: {error!r}")
