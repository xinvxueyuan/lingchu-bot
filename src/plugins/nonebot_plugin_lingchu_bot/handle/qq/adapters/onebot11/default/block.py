from typing import Any

from nonebot import logger, on_message, on_request, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
    GroupRequestEvent as OneBot11GroupRequestEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

from ......core.runtime_config import get_handle_config_manager
from ......database.orm_crud import DatabaseError
from ......i18n import _async as _
from ......repositories.blocklist import (
    BlockScope,
    clear_blocklist,
    find_active_block,
    remove_block,
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
    ONEBOT_V11_ADAPTER_ID,
    QQ_PLATFORM_ID,
    CommandAudit,
    bot_id,
    check_bot_privilege,
    check_target_privilege,
    default_admin_reason,
    finish_action_error_onebot11,
    format_user_display_name,
    record_audit_fire_and_forget,
    resolve_user_onebot11,
    store_block_record,
)

blocklisted_message = on_message(priority=1, block=False)
blocklisted_group_request = on_request(priority=1, block=False)


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
        reject_add_request=False,
    )


async def _block_member(
    *,
    command: Any,
    scope: BlockScope,
    user: At | int,
    duration: int | None,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    # 检查功能是否启用
    config = await get_handle_config_manager().get_config("block_member")
    if not config.enabled:
        return await command.finish(await _("该功能已禁用"))

    # 读取配置参数
    default_block_duration = config.defaults.get("block_duration")
    default_reason_text = config.defaults.get("default_reason", "违反群规")

    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)

    # 目标用户权限预检
    if not await check_target_privilege(bot, event, target_user_id, command):
        return None

    # 机器人权限预检
    if not await check_bot_privilege(bot, event.group_id, command):
        return None

    # 使用配置中的默认值
    # 如果用户没有提供duration，使用配置中的block_duration
    # 如果用户没有提供reason，使用配置中的default_reason（需要国际化）
    actual_duration = duration if duration is not None else default_block_duration
    reason_text = reason if reason is not None else await _(default_reason_text)

    try:
        await store_block_record(
            scope=scope,
            group_id=event.group_id,
            user_id=target_user_id,
            operator_id=event.user_id,
            duration=actual_duration,
            reason=reason_text,
            bot=bot,
        )
        await _kick_blocked_user(bot, event.group_id, target_user_id)
    except DatabaseError as error:
        return await _finish_database_error(command, await _("拉黑"), error)
    except OneBot11ActionFailed as error:
        return await finish_action_error_onebot11(command, await _("拉黑"), error)

    # 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="block_member",
            target_user_id=target_user_id,
            duration=actual_duration,
            reason=reason_text,
        ),
    )

    scope_text = await _("全局") if scope == "global" else await _("本群")
    duration_text = (
        await _("永久") if actual_duration is None else f"{actual_duration} 秒"
    )
    name_display = format_user_display_name(target_user_id, target_name)
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


@selected_adapter_handle(block_member_cmd, "~onebot.v11", "block_member")
async def onebot11_block_member(
    user: At | int,
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


@selected_adapter_handle(
    global_block_member_cmd,
    "~onebot.v11",
    "global_block_member",
)
async def onebot11_global_block_member(
    user: At | int,
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


async def _unblock_member(
    *,
    command: Any,
    scope: BlockScope,
    user: At | int,
    reason: str | None,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = await resolve_user_onebot11(user, bot, event)
    reason_text = await default_admin_reason(reason)
    try:
        result = await remove_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            scope=scope,
            group_id=event.group_id,
            user_id=target_user_id,
        )
        deleted = result[0]
    except DatabaseError as error:
        return await _finish_database_error(command, await _("删黑"), error)

    # 记录审计
    await record_audit_fire_and_forget(
        bot,
        event,
        CommandAudit(
            action="unblock_member",
            target_user_id=target_user_id,
            reason=reason_text,
        ),
    )

    scope_text = await _("全局") if scope == "global" else await _("本群")
    name_display = format_user_display_name(target_user_id, target_name)
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


@selected_adapter_handle(unblock_member_cmd, "~onebot.v11", "unblock_member")
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


@selected_adapter_handle(
    global_unblock_member_cmd,
    "~onebot.v11",
    "global_unblock_member",
)
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
    reason_text = await default_admin_reason(reason)
    try:
        result = await clear_blocklist(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            scope=scope,
            group_id=event.group_id,
        )
        deleted = result[0]
    except DatabaseError as error:
        return await _finish_database_error(command, await _("清空黑名单"), error)

    # 记录审计
    await record_audit_fire_and_forget(
        bot, event, CommandAudit(action="clear_blocklist", reason=reason_text)
    )

    scope_text = await _("全局") if scope == "global" else await _("本群")
    message = (
        await _("已清空黑名单: \n范围: {scope}\n原因: {reason}\n删除记录: {deleted}")
    ).format(scope=scope_text, reason=reason_text, deleted=deleted)
    logger.info(message)
    return await command.finish(message=message)


@selected_adapter_handle(clear_blocklist_cmd, "~onebot.v11", "clear_blocklist")
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


@selected_adapter_handle(
    global_clear_blocklist_cmd,
    "~onebot.v11",
    "global_clear_blocklist",
)
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
            bot_id=bot_id(bot),
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

    # 读取配置中的default_reason
    config = await get_handle_config_manager().get_config("block_member")
    default_reason_text = config.defaults.get("default_reason", "违反群规")

    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            bot_id=bot_id(bot),
            group_id=event.group_id,
            user_id=event.user_id,
        )
        if entry is None:
            return
        # 使用配置中的默认reason或黑名单记录中的reason
        reason = entry.reason or await _(default_reason_text)
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
